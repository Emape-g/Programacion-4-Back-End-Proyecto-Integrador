from pydantic import BaseModel


class ImagenResponse(BaseModel):
    url: str
    filename: str
