from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.rol.models import Rol
from app.modules.rol.schemas import RolCreate, RolList, RolPublic, RolUpdate
from app.modules.rol.unit_of_work import RolUnitOfWork


class RolService:

    def __init__(self, session: Session) -> None:
        self._session = session

    def _get_or_404(self, uow: RolUnitOfWork, codigo: str) -> Rol:
        rol = uow.roles.get_by_codigo(codigo)
        if not rol:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rol con codigo='{codigo}' no encontrado",
            )
        return rol

    def create(self, data: RolCreate) -> RolPublic:
        with RolUnitOfWork(self._session) as uow:
            if uow.roles.get_by_codigo(data.codigo.upper()):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe un rol con codigo='{data.codigo}'",
                )
            if uow.roles.get_by_nombre(data.nombre):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe un rol con nombre='{data.nombre}'",
                )
            rol = Rol(
                codigo=data.codigo.upper(),
                nombre=data.nombre,
                descripcion=data.descripcion,
            )
            uow.roles.add(rol)
            result = RolPublic.model_validate(rol)
        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> RolList:
        with RolUnitOfWork(self._session) as uow:
            items = uow.roles.get_all_paginated(offset=offset, limit=limit)
            total = uow.roles.count()
            return RolList(
                data=[RolPublic.model_validate(r) for r in items],
                total=total,
            )

    def get_by_codigo(self, codigo: str) -> RolPublic:
        with RolUnitOfWork(self._session) as uow:
            rol = self._get_or_404(uow, codigo.upper())
            return RolPublic.model_validate(rol)

    def update(self, codigo: str, data: RolUpdate) -> RolPublic:
        with RolUnitOfWork(self._session) as uow:
            rol = self._get_or_404(uow, codigo.upper())
            if data.nombre and data.nombre != rol.nombre:
                if uow.roles.get_by_nombre(data.nombre):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Ya existe un rol con nombre='{data.nombre}'",
                    )
            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(rol, field, value)
            uow.roles.add(rol)
            return RolPublic.model_validate(rol)

    def delete(self, codigo: str) -> None:
        with RolUnitOfWork(self._session) as uow:
            rol = self._get_or_404(uow, codigo.upper())
            uow.roles.delete(rol)
