\
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Optional


class StorageError(RuntimeError):
    pass


@dataclass
class PublishResult:
    backend: str
    destination: str


class BaseStore:
    def put_dir(self, src_dir: str, dest: str) -> PublishResult:
        raise NotImplementedError


class LocalStore(BaseStore):
    def put_dir(self, src_dir: str, dest: str) -> PublishResult:
        os.makedirs(dest, exist_ok=True)
        for root, dirs, files in os.walk(src_dir):
            rel_root = os.path.relpath(root, src_dir)
            out_root = os.path.join(dest, rel_root) if rel_root != "." else dest
            os.makedirs(out_root, exist_ok=True)
            for d in dirs:
                os.makedirs(os.path.join(out_root, d), exist_ok=True)
            for f in files:
                shutil.copy2(os.path.join(root, f), os.path.join(out_root, f))
        return PublishResult(backend="local", destination=os.path.abspath(dest))


class S3Store(BaseStore):
    def __init__(self, bucket: str, prefix: str):
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def put_dir(self, src_dir: str, dest: str) -> PublishResult:
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise StorageError("boto3 is required for S3 publishing. pip install boto3") from e

        s3 = boto3.client("s3")
        base = f"{self.prefix}/{dest}".strip("/")
        for root, _, files in os.walk(src_dir):
            rel_root = os.path.relpath(root, src_dir)
            for f in files:
                local_path = os.path.join(root, f)
                key = f"{base}/{rel_root}/{f}".replace("\\", "/").replace("/./", "/")
                s3.upload_file(local_path, self.bucket, key)
        return PublishResult(backend="s3", destination=f"s3://{self.bucket}/{base}")


def make_store(
    backend: str,
    *,
    local_dir: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    s3_prefix: Optional[str] = None,
) -> BaseStore:
    backend = (backend or "local").lower()
    if backend == "local":
        if not local_dir:
            raise StorageError("local_dir required for local publishing")
        return LocalStore()
    if backend == "s3":
        if not s3_bucket or not s3_prefix:
            raise StorageError("s3_bucket and s3_prefix required for s3 publishing")
        return S3Store(bucket=s3_bucket, prefix=s3_prefix)
    raise StorageError(f"Unknown publish backend: {backend}")
