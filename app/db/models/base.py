from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import as_declarative, Mapped, mapped_column
from sqlalchemy.ext.declarative import declared_attr


@as_declarative()
class Base:
    """Base class for all database models"""

    __allow_unmapped__: ClassVar[bool] = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
