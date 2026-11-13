from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import Base

class Center(Base):
    __tablename__ = "centers"
    id = Column(Integer, primary_key = True, index = True)
    name = Column(String, nullable = False)
    city = Column(String, nullable=False)
    sessions = relationship('Session', back_populates = "centers", cascade = "all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key = True, nullable = False)
    student_name = Column(String, nullable = False)
    status = Column(String, nullable = False)
    duration = Column(Integer, nullable = False)
    center_id = Column(Integer, ForeignKey("centers.id"))
    centers = relationship('Center', back_populates = "sessions")
