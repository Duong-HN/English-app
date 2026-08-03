import tempfile
from dataclasses import dataclass
from mimetypes import guess_type
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .config import Settings

ALLOWED_MIME_TYPES = {
    "audio/aac",
    "audio/flac",
    "audio/m4a",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
    "audio/x-wav",
    "video/mp4",
    "video/quicktime",
    "video/webm",
}

EXTENSION_BY_MIME = {
    "audio/aac": ".aac",
    "audio/flac": ".flac",
    "audio/m4a": ".m4a",
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
}


@dataclass(frozen=True)
class StoredMedia:
    storage_key: str
    mime_type: str
    file_size_bytes: int


def is_object_storage(settings: Settings) -> bool:
    return settings.media_storage_backend.strip().lower() == "s3"


def _s3_client(settings: Settings):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required when MEDIA_STORAGE_BACKEND=s3") from exc
    if not settings.object_storage_bucket:
        raise RuntimeError("OBJECT_STORAGE_BUCKET is required for object storage")
    return boto3.client(
        "s3",
        region_name=settings.object_storage_region,
        endpoint_url=settings.object_storage_endpoint_url,
    )


def storage_root(settings: Settings) -> Path:
    root = Path(settings.media_storage_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_storage_path(settings: Settings, storage_key: str) -> Path:
    root = storage_root(settings)
    candidate = (root / storage_key).resolve()
    if root != candidate and root not in candidate.parents:
        raise ValueError("Invalid media storage key")
    return candidate


def _mime_type(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower().strip()
    if content_type == "application/octet-stream" or not content_type:
        guessed, _ = guess_type(upload.filename or "")
        content_type = (guessed or content_type).lower()
    return content_type


def _validate_mime(media_type: str, mime_type: str) -> None:
    if media_type not in {"audio", "video"}:
        raise ValueError("media_type must be audio or video")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError("Unsupported audio/video format")
    if not mime_type.startswith(f"{media_type}/"):
        raise ValueError(f"The uploaded file is not {media_type}")


def save_upload(
    upload: UploadFile,
    *,
    media_type: str,
    settings: Settings,
) -> StoredMedia:
    mime_type = _mime_type(upload)
    _validate_mime(media_type, mime_type)
    suffix = Path(upload.filename or "").suffix.lower() or EXTENSION_BY_MIME[mime_type]
    if len(suffix) > 10 or not suffix.replace(".", "").isalnum():
        suffix = EXTENSION_BY_MIME[mime_type]

    storage_key = f"lesson-media/{uuid4().hex}{suffix}"
    maximum_bytes = max(1, settings.media_max_size_mb) * 1024 * 1024
    total = 0
    if is_object_storage(settings):
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temporary:
                temporary_path = temporary.name
                while True:
                    chunk = upload.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > maximum_bytes:
                        raise ValueError(f"Media file exceeds {settings.media_max_size_mb} MB")
                    temporary.write(chunk)
            _s3_client(settings).upload_file(
                temporary_path,
                settings.object_storage_bucket,
                storage_key,
                ExtraArgs={"ContentType": mime_type},
            )
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
        return StoredMedia(storage_key=storage_key, mime_type=mime_type, file_size_bytes=total)

    destination = resolve_storage_path(settings, storage_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("wb") as target:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > maximum_bytes:
                    raise ValueError(f"Media file exceeds {settings.media_max_size_mb} MB")
                target.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return StoredMedia(
        storage_key=storage_key,
        mime_type=mime_type,
        file_size_bytes=total,
    )


def delete_stored_media(settings: Settings, storage_key: str | None) -> None:
    if not storage_key:
        return
    if is_object_storage(settings):
        _s3_client(settings).delete_object(Bucket=settings.object_storage_bucket, Key=storage_key)
        return
    path = resolve_storage_path(settings, storage_key)
    path.unlink(missing_ok=True)


def presigned_media_url(settings: Settings, storage_key: str, expires_seconds: int = 300) -> str:
    if not is_object_storage(settings):
        raise RuntimeError("Presigned URLs require object storage")
    return _s3_client(settings).generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.object_storage_bucket, "Key": storage_key},
        ExpiresIn=max(60, min(expires_seconds, 3600)),
    )
