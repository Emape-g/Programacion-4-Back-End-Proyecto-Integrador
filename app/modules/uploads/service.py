import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.modules.uploads.schemas import ImagenResponse

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB

UPLOAD_DIR = Path("static/uploads")


def _ext_from_mime(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[mime]


async def upload_imagen(file: UploadFile, folder: str = "productos") -> ImagenResponse:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {file.content_type}. "
                   f"Permitidos: {', '.join(ALLOWED_MIME)}",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo demasiado grande. Máximo: {MAX_SIZE // (1024*1024)} MB",
        )

    dest_dir = UPLOAD_DIR / folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    ext = _ext_from_mime(file.content_type)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = dest_dir / filename

    filepath.write_bytes(contents)

    url = f"/static/uploads/{folder}/{filename}"
    return ImagenResponse(url=url, filename=filename)


def delete_imagen(folder: str, filename: str) -> None:
    filepath = UPLOAD_DIR / folder / filename
    if filepath.exists():
        os.remove(filepath)
