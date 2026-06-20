from datetime import datetime, timezone
from typing import Any, Generic, Sequence, Type, TypeVar

from sqlmodel import Session, SQLModel, func, select

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):

    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get_by_id(self, record_id: Any) -> ModelT | None:
        return self.session.get(self.model, record_id)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        return self.session.exec(
            select(self.model).offset(offset).limit(limit)
        ).all()

    def list_all(self) -> Sequence[ModelT]:
        return self.session.exec(select(self.model)).all()

    def count(self) -> int:
        return self.session.exec(
            select(func.count()).select_from(self.model)
        ).one()

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def update(self, instance: ModelT, patch: dict[str, Any]) -> ModelT:
        for key, value in patch.items():
            setattr(instance, key, value)
        if hasattr(instance, "updated_at"):
            instance.updated_at = datetime.now(timezone.utc)
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def soft_delete(self, instance: ModelT) -> ModelT:
        if not hasattr(instance, "deleted_at"):
            raise AttributeError(
                f"{self.model.__name__} no soporta soft-delete (sin deleted_at)"
            )
        instance.deleted_at = datetime.now(timezone.utc)
        self.session.add(instance)
        self.session.flush()
        return instance

    def hard_delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()

    def delete(self, instance: ModelT) -> None:
        self.hard_delete(instance)
