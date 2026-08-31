import os
import shutil
from pathlib import Path

import boto3
from botocore.config import Config
from flask import redirect, send_file


BASE_DIR = Path(__file__).resolve().parent
LOCAL_UPLOAD_ROOT = BASE_DIR / "uploads"


class StorageManager:
    def __init__(self):
        self.backend = os.environ.get("STORAGE_BACKEND", "local").strip().lower()
        self._client = None

        LOCAL_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    @property
    def is_r2(self):
        return self.backend == "r2"

    def _r2_client(self):
        if self._client is not None:
            return self._client

        account_id = os.environ.get("R2_ACCOUNT_ID")
        access_key = os.environ.get("R2_ACCESS_KEY_ID")
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

        missing = [
            name for name, value in {
                "R2_ACCOUNT_ID": account_id,
                "R2_ACCESS_KEY_ID": access_key,
                "R2_SECRET_ACCESS_KEY": secret_key,
            }.items()
            if not value
        ]

        if missing:
            raise RuntimeError(
                "Brakuje zmiennych Cloudflare R2: " + ", ".join(missing)
            )

        self._client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        return self._client

    def _bucket(self):
        bucket = os.environ.get("R2_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("Brakuje zmiennej R2_BUCKET_NAME.")
        return bucket

    def save(self, file_storage, key, download_name=None):
        key = key.replace("\\", "/").lstrip("/")

        if self.is_r2:
            extra_args = {
                "ContentType": (
                    file_storage.mimetype
                    or "application/octet-stream"
                )
            }

            if download_name:
                safe_name = download_name.replace('"', "")
                extra_args["ContentDisposition"] = (
                    f'attachment; filename="{safe_name}"'
                )

            file_storage.stream.seek(0)

            self._r2_client().upload_fileobj(
                file_storage.stream,
                self._bucket(),
                key,
                ExtraArgs=extra_args,
            )
            return

        path = LOCAL_UPLOAD_ROOT / key
        path.parent.mkdir(parents=True, exist_ok=True)
        file_storage.save(path)

    def delete(self, key):
        if not key:
            return

        key = key.replace("\\", "/").lstrip("/")

        if self.is_r2:
            self._r2_client().delete_object(
                Bucket=self._bucket(),
                Key=key,
            )
            return

        path = LOCAL_UPLOAD_ROOT / key
        if path.exists() and path.is_file():
            path.unlink()

    def move(self, old_key, new_key):
        old_key = old_key.replace("\\", "/").lstrip("/")
        new_key = new_key.replace("\\", "/").lstrip("/")

        if old_key == new_key:
            return

        if self.is_r2:
            client = self._r2_client()
            bucket = self._bucket()

            client.copy_object(
                Bucket=bucket,
                Key=new_key,
                CopySource={"Bucket": bucket, "Key": old_key},
            )
            client.delete_object(Bucket=bucket, Key=old_key)
            return

        old_path = LOCAL_UPLOAD_ROOT / old_key
        new_path = LOCAL_UPLOAD_ROOT / new_key

        if not old_path.exists():
            return

        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))

    def exists(self, key):
        key = key.replace("\\", "/").lstrip("/")

        if self.is_r2:
            try:
                self._r2_client().head_object(
                    Bucket=self._bucket(),
                    Key=key,
                )
                return True
            except Exception:
                return False

        return (LOCAL_UPLOAD_ROOT / key).exists()

    def download_response(self, key, download_name):
        key = key.replace("\\", "/").lstrip("/")

        if self.is_r2:
            url = self._r2_client().generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._bucket(),
                    "Key": key,
                },
                ExpiresIn=300,
            )
            return redirect(url)

        path = LOCAL_UPLOAD_ROOT / key
        if not path.exists():
            return None

        return send_file(
            path,
            as_attachment=True,
            download_name=download_name,
        )


storage = StorageManager()
