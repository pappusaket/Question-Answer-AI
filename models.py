from sqlalchemy import Column, Integer, String, DateTime, Date, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserActivity(Base):
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    subject = Column(String(100), nullable=False)
    last_used_date = Column(Date, nullable=False)
    questions_generated = Column(Integer, default=0)

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(100), nullable=False)
    chapter = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(Text)  # JSON string of options
    correct_answer = Column(String(500), nullable=False)
    difficulty = Column(String(50), default="medium")
    language = Column(String(10), default="english")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
