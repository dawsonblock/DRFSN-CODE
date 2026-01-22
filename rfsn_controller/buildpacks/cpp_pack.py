"""C/C++ buildpack implementation.

Supports CMake and Make based projects, including single file compilation.
"""

import os
from typing import List, Optional

from .base import (
    Buildpack,
    BuildpackContext,
    BuildpackType,
    DetectResult,
    FailureInfo,
    Step,
    TestPlan,
)


class CppBuildpack(Buildpack):
    """Buildpack for C/C++ projects."""

    def __init__(self):
        super().__init__()
        # Note: We need to register CPP/C in BuildpackType enum first
        # For now, we reuse UNKNOWN or rely on dynamic typing until base.py is updated
        self._buildpack_type = BuildpackType.CPP

    def detect(self, ctx: BuildpackContext) -> Optional[DetectResult]:
        """Detect C/C++ project."""
        confidence = 0.0
        
        # Check for build systems
        if "CMakeLists.txt" in ctx.files:
            confidence = 1.0
        elif "Makefile" in ctx.files or "makefile" in ctx.files:
            confidence = 0.9
        
        # Check for source files
        if confidence == 0.0:
            c_files = [f for f in ctx.files if f.endswith(".c")]
            cpp_files = [f for f in ctx.files if f.endswith(".cpp") or f.endswith(".cc")]
            # h_files check removed as it was unused
            
            if c_files or cpp_files:
                confidence = 0.8  # Strong signal if source files exist
        
        if confidence > 0.0:
            return DetectResult(
                buildpack_type=self._buildpack_type,
                confidence=confidence,
            )
        
        return None

    def image(self) -> str:
        """Return C++ build image."""
        # Using a standard image with gcc/clang
        return "gcc:latest"

    def sysdeps_whitelist(self) -> List[str]:
        """Return allowed system packages."""
        return super().sysdeps_whitelist() + [
            "cmake",
            "gdb",
            "valgrind",
            "clang",
            "llvm",
        ]

    def install_plan(self, ctx: BuildpackContext) -> List[Step]:
        """Generate install steps."""
        steps = []
        
        # Check for custom setup first (using the pattern we established)
        if "setup.sh" in ctx.files:
            steps.append(Step(
                argv=["bash", "setup.sh"],
                description="Run custom setup script",
                timeout_sec=600,
                network_required=True,
            ))
            return steps

        # CMake workflow
        if "CMakeLists.txt" in ctx.files:
            steps.append(Step(
                argv=["mkdir", "-p", "build"],
                description="Create build directory",
            ))
            steps.append(Step(
                argv=["cmake", "-S", ".", "-B", "build"],
                description="Configure CMake",
                timeout_sec=300,
            ))
            steps.append(Step(
                argv=["cmake", "--build", "build"],
                description="Build with CMake",
                timeout_sec=600,
            ))
            return steps
            
        # Makefile workflow
        if "Makefile" in ctx.files or "makefile" in ctx.files:
            steps.append(Step(
                argv=["make"],
                description="Build with Make",
                timeout_sec=600,
            ))
            return steps
            
        # Single file heuristics (fallback)
        # We don't compile here for single files, we let test_plan handle it
        # or we compile all .c files found
        return []

    def test_plan(self, ctx: BuildpackContext, focus_file: Optional[str] = None) -> TestPlan:
        """Generate test plan."""
        # Check for CTest
        if "CMakeLists.txt" in ctx.files:
            return TestPlan(
                argv=["ctest", "--test-dir", "build", "--output-on-failure"],
                description="Run CTest",
            )
            
        # Check for custom python harness (like D-Bug)
        # This is a bit specific but covers our use case
        if os.path.exists(os.path.join(ctx.repo_dir, "tests")):
            # Simple heuristic: look for python scripts in tests/
            try:
                test_files = [f for f in os.listdir(os.path.join(ctx.repo_dir, "tests")) if f.endswith(".py")]
                if test_files:
                     return TestPlan(
                        argv=["python", f"tests/{test_files[0]}"],
                        description="Run Python test harness",
                    )
            except OSError:
                pass

        # Fallback: compile and run if single C file
        c_files = [f for f in ctx.files if f.endswith(".c") and "test" not in f]
        if len(c_files) == 1:
            src = c_files[0]
            exe = src.replace(".c", "")
            return TestPlan(
                argv=["sh", "-c", f"gcc -o {exe} {src} && ./{exe}"],
                description="Compile and run single file",
            )

        return TestPlan(
            argv=["echo", "No tests detected"],
            description="No tests detected",
        )

    def parse_failures(self, stdout: str, stderr: str) -> FailureInfo:
        """Parse build/test failures."""
        # TODO: Implement robust C/C++ error parsing
        # For now, return basic info
        return FailureInfo(
            failing_tests=[],
            likely_files=[],
            signature="unknown_cpp_error",
            error_message=stderr[:1000] if stderr else stdout[:1000],
        )
