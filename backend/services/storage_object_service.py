"""
backend/services/storage_object_service.py

MinIO / S3-compatible Object Storage Service — Section 14.
Manages crop image uploads, verification documents, and audit attachments.
Defaults to clean LocalDisk storage unless MinIO is explicitly enabled and reachable.
"""

import os
import socket
import logging
import uuid
from typing import Dict, Any
from config.settings import settings

logger = logging.getLogger("ObjectStorageService")


class ObjectStorageService:
    """MinIO / Local File Storage Manager with opt-in MinIO and clean local fallback."""

    def __init__(self):
        self.minio_client = None
        self._init_client()

    @property
    def is_minio_active(self) -> bool:
        """Return True if MinIO is actively connected and usable."""
        return self.minio_client is not None

    @property
    def storage_backend(self) -> str:
        """Return current active backend name."""
        return "MinIO" if self.minio_client is not None else "LocalDisk"

    def _is_minio_enabled(self) -> bool:
        """Check if MinIO is explicitly enabled via environment or settings."""
        if os.getenv("ENABLE_MINIO", "").lower() in ("1", "true", "yes"):
            return True
        if os.getenv("USE_MINIO", "").lower() in ("1", "true", "yes"):
            return True
        if getattr(settings, "ENABLE_MINIO", False):
            return True
        return False

    def _probe_minio_endpoint(self, endpoint: str, timeout: float = 1.0) -> bool:
        """Fast TCP probe to verify if the MinIO endpoint is actually reachable."""
        try:
            parts = endpoint.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 9000
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            return False

    def _init_client(self):
        """Initialize storage backend. Defaults cleanly to LocalDisk without false warnings."""
        if not self._is_minio_enabled():
            self.minio_client = None
            logger.info("MinIO disabled by default (ENABLE_MINIO=False). LocalDisk storage backend active.")
            return

        endpoint = os.getenv("MINIO_ENDPOINT", getattr(settings, "MINIO_ENDPOINT", "localhost:9000"))
        if not self._probe_minio_endpoint(endpoint):
            logger.warning(
                f"MinIO explicitly enabled but server at {endpoint} is unreachable. Falling back to LocalDisk storage."
            )
            self.minio_client = None
            return

        try:
            from minio import Minio

            access_key = os.getenv("MINIO_ACCESS_KEY", getattr(settings, "MINIO_ACCESS_KEY", "minioadmin"))
            secret_key = os.getenv("MINIO_SECRET_KEY", getattr(settings, "MINIO_SECRET_KEY", "minioadmin"))
            client = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False,
            )
            # Verify live connectivity
            client.list_buckets()
            self.minio_client = client
            logger.info(f"MinIO client connected and verified at {endpoint}.")
        except Exception as e:
            logger.warning(
                f"MinIO client initialization failed ({e}). Falling back to LocalDisk storage."
            )
            self.minio_client = None

    def upload_file(
        self,
        bucket_name: str,
        file_name: str,
        file_data: bytes,
        content_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Upload file data to MinIO bucket (if active) or local directory.
        Returns metadata including URL and storage type.
        """
        file_id = f"file_{uuid.uuid4().hex[:8]}"

        if self.minio_client is not None:
            try:
                import io

                found = self.minio_client.bucket_exists(bucket_name)
                if not found:
                    self.minio_client.make_bucket(bucket_name)

                data_stream = io.BytesIO(file_data)
                endpoint = os.getenv("MINIO_ENDPOINT", getattr(settings, "MINIO_ENDPOINT", "localhost:9000"))
                self.minio_client.put_object(
                    bucket_name,
                    file_name,
                    data_stream,
                    length=len(file_data),
                    content_type=content_type,
                )
                url = f"http://{endpoint}/{bucket_name}/{file_name}"
                return {
                    "success": True,
                    "file_id": file_id,
                    "url": url,
                    "storage": "MinIO",
                }
            except Exception as e:
                logger.warning(f"MinIO upload error: {e}. Falling back to LocalDisk storage.")

        # Local storage fallback (deterministic, offline-safe, zero network latency)
        local_dir = os.path.join("./node_storage/uploads", bucket_name)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, file_name)

        with open(local_path, "wb") as f:
            f.write(file_data)

        return {
            "success": True,
            "file_id": file_id,
            "url": f"/static/uploads/{bucket_name}/{file_name}",
            "storage": "LocalDisk",
        }


# Singleton instance
object_storage_service = ObjectStorageService()
