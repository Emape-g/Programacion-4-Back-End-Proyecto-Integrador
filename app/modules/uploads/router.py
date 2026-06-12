from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.auth import require_admin
from app.modules.uploads.schemas import CloudinaryResponse
from app.modules.uploads.service import delete_imagen, upload_imagen

router = APIRouter()


@router.post(
    "/imagen",
    response_model=CloudinaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir imagen a Cloudinary",
)
async def subir_imagen(
    file: UploadFile = File(...),
    folder: str = Query(default="productos"),
    _: dict = Depends(require_admin),
) -> CloudinaryResponse:
    return await upload_imagen(file, folder)


@router.delete(
    "/imagen/{public_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar imagen de Cloudinary por public_id",
)
def eliminar_imagen(
    public_id: str,
    _: dict = Depends(require_admin),
) -> None:
    delete_imagen(public_id)
