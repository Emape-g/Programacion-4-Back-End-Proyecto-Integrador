from typing import Generic, TypeVar, Type, Sequence
from sqlmodel import Session, SQLModel, select

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """
    Repositorio genérico que implementa operaciones CRUD básicas
    para cualquier modelo basado en SQLModel.

    Principio: el repositorio solo habla con la DB.
    No contiene lógica de negocio ni levanta HTTPException.

    Este repositorio sirve como clase base para repositorios específicos,
    donde se agregan queries más complejas o reglas de acceso particulares.

    Tipado:
    - Usa Generic[ModelT] para mantener tipado fuerte en cada repositorio concreto.
    """
    def __init__(self, session: Session, model: Type[ModelT]) -> None:
        """
        Inicializa el repositorio con una sesión de base de datos y el modelo asociado.

        Args:
            session (Session): Sesión activa de SQLModel/SQLAlchemy.
                               Es inyectada generalmente por el UnitOfWork.
            model (Type[ModelT]): Clase del modelo que este repositorio gestiona.
        """
        self.session = session
        self.model = model

    def get_by_id(self, record_id: int) -> ModelT | None:
        """
        Obtiene una entidad por su ID primario.

        Args:
            record_id (int): Identificador único del registro.

        Returns:
            ModelT | None: Instancia del modelo si existe, o None si no se encuentra.

        Nota:
            No lanza excepciones. El manejo de "no encontrado" debe hacerse en la capa de servicio.
        """
        return self.session.get(self.model, record_id)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        """
        Obtiene una lista paginada de entidades.

        Args:
            offset (int): Cantidad de registros a omitir (paginación).
            limit (int): Cantidad máxima de registros a devolver.

        Returns:
            Sequence[ModelT]: Lista de entidades recuperadas.

        Nota:
            No garantiza orden si no se especifica explícitamente en la query.
        """
        return self.session.exec(
            select(self.model).offset(offset).limit(limit)
        ).all()

    def add(self, instance: ModelT) -> ModelT:
        """
        Persiste una nueva entidad en la sesión actual.

        Flujo:
        - add(): marca la entidad para inserción
        - flush(): ejecuta INSERT en la DB sin commit (genera ID)
        - refresh(): sincroniza el estado del objeto con la DB

        Args:
            instance (ModelT): Instancia a persistir.

        Returns:
            ModelT: La misma instancia, con su ID ya generado.

        Importante:
            NO hace commit. Esto lo maneja el UnitOfWork.
        """
        self.session.add(instance)
        self.session.flush()  # obtiene el ID sin hacer commit
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """
        Marca una entidad para eliminación en la base de datos.

        Flujo:
        - delete(): marca para borrado
        - flush(): ejecuta DELETE sin commit

        Args:
            instance (ModelT): Instancia a eliminar.

        Importante:
            NO hace commit. El UnitOfWork decide cuándo persistir el cambio.
        """
        self.session.delete(instance)
        self.session.flush()