
from typing import Optional
from sqlmodel import SQLModel, Field

class Product(SQLModel, table=True):
    sku: str = Field(primary_key=True, index=True)
    name: str
    description: str
    category: str
    price: float
    image_url: Optional[str] = None
