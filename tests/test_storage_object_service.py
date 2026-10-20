"""
tests/test_storage_object_service.py

Unit tests for ObjectStorageService:
- Verifies clean LocalDisk default with zero connection latency or unhandled warnings
- Verifies upload_file persists to local filesystem
- Verifies graceful fallback when MinIO is enabled but unreachable
- Verifies mock MinIO upload path
"""

import os
import time
import pytest
from unittest.mock import MagicMock, patch
from backend.services.storage_object_service import ObjectStorageService


@pytest.fixture(autouse=True)
def clean_minio_env(monkeypatch):
    """Ensure MinIO is disabled by default for tests unless explicitly tested."""
    monkeypatch.delenv("ENABLE_MINIO", raising=False)
    monkeypatch.delenv("USE_MINIO", raising=False)


def test_default_storage_service_uses_local_disk():
    """Verify that by default, ObjectStorageService uses LocalDisk without network probes."""
    start_time = time.time()
    service = ObjectStorageService()
    duration = time.time() - start_time

    assert duration < 0.1, "Initialization should be instantaneous when MinIO is disabled"
    assert service.minio_client is None
    assert service.is_minio_active is False
    assert service.storage_backend == "LocalDisk"


def test_default_upload_file_writes_to_disk(tmp_path):
    """Verify upload_file saves bytes to local path and returns accurate URL."""
    service = ObjectStorageService()
    bucket = "test_crops"
    filename = "potato_quality_check.png"
    sample_data = b"\x89PNG\r\n\x1a\nFakePngImageData"

    result = service.upload_file(
        bucket_name=bucket,
        file_name=filename,
        file_data=sample_data,
        content_type="image/png"
    )

    assert result["success"] is True
    assert result["storage"] == "LocalDisk"
    assert result["file_id"].startswith("file_")
    assert result["url"] == f"/static/uploads/{bucket}/{filename}"

    # Verify actual written file on disk
    expected_path = os.path.join("./node_storage/uploads", bucket, filename)
    assert os.path.exists(expected_path)
    with open(expected_path, "rb") as f:
        assert f.read() == sample_data


def test_minio_enabled_but_unreachable_falls_back_gracefully(monkeypatch):
    """Verify that when ENABLE_MINIO=true but port is dead, it falls back to LocalDisk cleanly."""
    monkeypatch.setenv("ENABLE_MINIO", "true")
    monkeypatch.setenv("MINIO_ENDPOINT", "127.0.0.1:59999")  # Non-existent port

    start_time = time.time()
    service = ObjectStorageService()
    duration = time.time() - start_time

    # Fast probe ensures timeout is under 1.5 seconds rather than standard 30s TCP hang
    assert duration < 2.0
    assert service.storage_backend == "LocalDisk"
    assert service.is_minio_active is False

    # Upload still succeeds smoothly via LocalDisk
    res = service.upload_file("contracts", "c1.pdf", b"Contract Data")
    assert res["success"] is True
    assert res["storage"] == "LocalDisk"


def test_minio_upload_when_client_active(monkeypatch):
    """Verify that when MinIO client is active, put_object is invoked with the expected parameters."""
    service = ObjectStorageService()

    # Mock MinIO client
    mock_minio = MagicMock()
    mock_minio.bucket_exists.return_value = False
    service.minio_client = mock_minio

    assert service.is_minio_active is True
    assert service.storage_backend == "MinIO"

    file_bytes = b"sample contract text"
    res = service.upload_file("agri_agreements", "agreement_001.pdf", file_bytes, content_type="application/pdf")

    assert res["success"] is True
    assert res["storage"] == "MinIO"
    assert "agreement_001.pdf" in res["url"]

    # Check make_bucket was called because bucket_exists was False
    mock_minio.make_bucket.assert_called_once_with("agri_agreements")
    mock_minio.put_object.assert_called_once()
    args, kwargs = mock_minio.put_object.call_args
    assert args[0] == "agri_agreements"
    assert args[1] == "agreement_001.pdf"
    assert kwargs["length"] == len(file_bytes)
    assert kwargs["content_type"] == "application/pdf"
