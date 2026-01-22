"""RFSN Dashboard Backend.

Serves the UI, manages API keys, and broadcasts controller events via WebSockets.
Enhanced with run management, health monitoring, and controller interaction APIs.
"""

import os
import asyncio
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv, set_key

# Load existing environment
load_dotenv()

app = FastAPI(title="RFSN Dashboard", version="2.0.0")

# Allow CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Startup Time ---
_startup_time = time.time()

# --- State Management ---


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        # Clean up dead connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()

# --- Run Management ---
# In-memory storage of active and recent runs
_active_runs: Dict[str, Dict[str, Any]] = {}
_run_history: List[Dict[str, Any]] = []
_max_history = 50


# --- Models ---


class ConfigUpdate(BaseModel):
    """Configuration update request."""

    DEEPSEEK_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None


class RunConfig(BaseModel):
    """Configuration for launching a controller run."""

    repo_url: str = Field(..., description="GitHub repository URL")
    test_cmd: Optional[str] = Field(
        None, description="Test command (auto-detect if not set)"
    )
    max_steps: int = Field(12, ge=1, le=100, description="Maximum steps")
    planner_mode: str = Field("off", description="Planner mode: off, dag")
    policy_mode: str = Field("off", description="Policy mode: off, bandit")
    feature_mode: bool = Field(False, description="Enable feature generation mode")
    feature_description: Optional[str] = Field(None, description="Feature description")
    parallel_patches: bool = Field(False, description="Generate patches in parallel")
    incremental_tests: bool = Field(False, description="Use incremental testing")
    enable_llm_cache: bool = Field(False, description="Enable LLM response caching")


class ControllerEvent(BaseModel):
    """Event received from the controller."""

    type: str  # e.g., "log", "step", "patch", "error"
    data: Dict
    run_id: Optional[str] = None


class RunSummary(BaseModel):
    """Summary of a controller run."""

    run_id: str
    repo_url: str
    status: str  # pending, running, success, failed, stopped
    started_at: str
    ended_at: Optional[str] = None
    steps_completed: int = 0
    patches_tried: int = 0


# --- Routes ---


@app.get("/api/health")
async def health_check():
    """Dashboard health check endpoint."""
    uptime_seconds = time.time() - _startup_time
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime_seconds, 2),
        "active_connections": len(manager.active_connections),
        "active_runs": len(_active_runs),
        "version": "2.0.0",
    }


@app.get("/api/config")
async def get_config():
    """Get current configuration (masked keys)."""
    # Reload env to get latest values
    load_dotenv(override=True)

    def mask(key: str) -> Optional[str]:
        val = os.getenv(key)
        if not val:
            return None
        if len(val) < 8:
            return "*" * len(val)
        return val[:4] + "*" * (len(val) - 8) + val[-4:]

    return {
        "DEEPSEEK_API_KEY": mask("DEEPSEEK_API_KEY"),
        "GEMINI_API_KEY": mask("GEMINI_API_KEY"),
        "OPENAI_API_KEY": mask("OPENAI_API_KEY"),
        "GITHUB_TOKEN": mask("GITHUB_TOKEN"),
    }


@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    """Update API keys in .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        env_file.touch()

    updates = config.dict(exclude_unset=True)
    updated_count = 0

    for key, value in updates.items():
        if value:
            # Write to .env file
            set_key(env_file, key, value)
            # Update current process env
            os.environ[key] = value
            updated_count += 1

    return {"status": "ok", "updated": updated_count}


@app.get("/api/runs")
async def list_runs():
    """List all runs (active and recent history)."""
    active = [
        RunSummary(
            run_id=run_id,
            repo_url=data.get("repo_url", ""),
            status=data.get("status", "running"),
            started_at=data.get("started_at", ""),
            steps_completed=data.get("steps_completed", 0),
            patches_tried=data.get("patches_tried", 0),
        ).dict()
        for run_id, data in _active_runs.items()
    ]
    return {
        "active": active,
        "history": _run_history[-20:],  # Last 20 from history
    }


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """Get details for a specific run."""
    if run_id in _active_runs:
        return {"found": True, "active": True, **_active_runs[run_id]}

    for run in _run_history:
        if run.get("run_id") == run_id:
            return {"found": True, "active": False, **run}

    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/run")
async def start_run(config: RunConfig):
    """Launch a new controller run."""
    run_id = str(uuid4())[:8]
    started_at = datetime.now().isoformat()

    # Build command
    cmd = ["uv", "run", "rfsn", "--repo", config.repo_url]
    if config.test_cmd:
        cmd.extend(["--test", config.test_cmd])
    cmd.extend(["--steps", str(config.max_steps)])

    if config.planner_mode != "off":
        cmd.extend(["--planner-mode", config.planner_mode])
    if config.policy_mode != "off":
        cmd.extend(["--policy-mode", config.policy_mode])
    if config.feature_mode:
        cmd.append("--feature-mode")
        if config.feature_description:
            cmd.extend(["--feature-description", config.feature_description])
    if config.parallel_patches:
        cmd.append("--parallel-patches")
    if config.incremental_tests:
        cmd.append("--incremental-tests")
    if config.enable_llm_cache:
        cmd.append("--enable-llm-cache")

    # Store run info
    run_data = {
        "run_id": run_id,
        "repo_url": config.repo_url,
        "config": config.dict(),
        "command": cmd,
        "status": "pending",
        "started_at": started_at,
        "steps_completed": 0,
        "patches_tried": 0,
        "process": None,
    }
    _active_runs[run_id] = run_data

    # Broadcast run started event
    await manager.broadcast(
        json.dumps(
            {
                "type": "run_started",
                "run_id": run_id,
                "data": {"repo_url": config.repo_url, "started_at": started_at},
            }
        )
    )

    # Note: In production, you'd spawn the subprocess here
    # For now, we just track the configuration
    run_data["status"] = "running"

    return {"status": "ok", "run_id": run_id, "command": " ".join(cmd)}


@app.post("/api/stop/{run_id}")
async def stop_run(run_id: str):
    """Stop a running controller."""
    if run_id not in _active_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run_data = _active_runs[run_id]

    # Terminate process if running
    proc = run_data.get("process")
    if proc and proc.poll() is None:
        proc.terminate()

    run_data["status"] = "stopped"
    run_data["ended_at"] = datetime.now().isoformat()

    # Move to history
    _run_history.append(run_data.copy())
    if len(_run_history) > _max_history:
        _run_history.pop(0)
    del _active_runs[run_id]

    # Broadcast stop event
    await manager.broadcast(
        json.dumps({"type": "run_stopped", "run_id": run_id, "data": {}})
    )

    return {"status": "ok", "run_id": run_id}


@app.post("/api/events")
async def receive_event(event: ControllerEvent = Body(...)):
    """Receive an event from the controller and broadcast it."""
    # Update run stats if applicable
    if event.run_id and event.run_id in _active_runs:
        run = _active_runs[event.run_id]
        if event.type == "status" and "step" in event.data:
            run["steps_completed"] = event.data.get("step", 0)
        if event.type == "metric" and "patches_tried" in event.data:
            run["patches_tried"] = event.data.get("patches_tried", 0)
        if event.type == "complete":
            run["status"] = "success" if event.data.get("success") else "failed"
            run["ended_at"] = datetime.now().isoformat()
            # Move to history
            _run_history.append(run.copy())
            if len(_run_history) > _max_history:
                _run_history.pop(0)
            del _active_runs[event.run_id]

    msg = json.dumps({"type": event.type, "data": event.data, "run_id": event.run_id})
    await manager.broadcast(msg)
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the frontend."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive commands from UI
            data = await websocket.receive_text()
            # Future: Handle commands from UI
            try:
                cmd = json.loads(data)
                if cmd.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "data": {}}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Serve static files (UI)
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    # Run on localhost:8000
    print("Starting RFSN Dashboard on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
