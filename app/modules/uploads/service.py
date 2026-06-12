import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.modules.uploads.schemas import CloudinaryResponse

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
    )


async def upload_imagen(file: UploadFile, folder: str = "productos") -> CloudinaryResponse:
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

    _configure_cloudinary()

    result = cloudinary.uploader.upload(
        contents,
        folder=f"foodstore/{folder}",
        resource_type="image",
        overwrite=False,
        unique_filename=True,
    )

    return CloudinaryResponse(
        secure_url=result["secure_url"],
        public_id=result["public_id"],
        width=result["width"],
        height=result["height"],
        format=result["format"],
        resource_type=result["resource_type"],
    )


def delete_imagen(public_id: str) -> None:
    _configure_cloudinary()
    result = cloudinary.uploader.destroy(public_id, resource_type="image")
    if result.get("result") not in ("ok", "not found"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando imagen: {result}",
        )
