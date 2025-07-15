from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class PasswordHistory(Base):
    """Model for tracking user password history."""
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", backref="password_history")
    
    def __repr__(self):
        return f"<PasswordHistory user_id={self.user_id} created_at={self.created_at}>"