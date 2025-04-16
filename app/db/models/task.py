from sqlalchemy import Column, String, Text

from app.db.models.base import Base


class Task(Base):
    """Task database model"""

    title = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"Task(id={self.id}, title={self.title})"
