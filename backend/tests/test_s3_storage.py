from io import BytesIO
from unittest.mock import Mock, patch

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.config import Settings
from app.media_storage import delete_stored_media, presigned_media_url, save_upload


def _settings() -> Settings:
    return Settings(
        media_storage_backend="s3",
        object_storage_bucket="learnmate-test",
        object_storage_region="ap-southeast-1",
    )


def test_s3_storage_upload_delete_and_presign_use_object_key():
    client = Mock()
    client.generate_presigned_url.return_value = "https://storage.example/signed"
    upload = UploadFile(
        filename="answer.mp3",
        file=BytesIO(b"audio-bytes"),
        headers=Headers({"content-type": "audio/mpeg"}),
    )

    with patch("app.media_storage._s3_client", return_value=client):
        stored = save_upload(upload, media_type="audio", settings=_settings())
        delete_stored_media(_settings(), stored.storage_key)
        signed = presigned_media_url(_settings(), stored.storage_key)

    assert stored.storage_key.startswith("lesson-media/")
    assert stored.file_size_bytes == 11
    client.upload_file.assert_called_once()
    client.delete_object.assert_called_once_with(Bucket="learnmate-test", Key=stored.storage_key)
    assert signed == "https://storage.example/signed"
