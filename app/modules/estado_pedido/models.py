from sqlmodel import SQLModel, Field


class EstadoPedido(SQLModel, table=True):

    __tablename__ = "estado_pedido"

    codigo: str = Field(max_length=20, primary_key=True)   # PK semántica
    descripcion: str = Field(max_length=80)                # NN
    orden: int                                             # NN — posición en el FSM
    es_terminal: bool                                      # NN — true = no hay transiciones salientes
