from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.auth import require_admin
from app.modules.uploads.schemas import ImagenResponse
from app.modules.uploads.service import delete_imagen, upload_imagen

router = APIRouter()


@router.post(
    "/imagen",
    response_model=ImagenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen",
)
async def subir_imagen(
    file: UploadFile = File(...),
    folder: str = Query(default="productos"),
    _: dict = Depends(require_admin),
) -> ImagenResponse:
    return await upload_imagen(file, folder)


@router.delete(
    "/imagen/{folder}/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen por folder y filename",
)
def eliminar_imagen(
    folder: str,
    filename: str,
    _: dict = Depends(require_admin),
) -> None:
    delete_imagen(folder, filename)
