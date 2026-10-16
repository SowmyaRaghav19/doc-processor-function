import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("AZURE_SQL_CONNECTION_STRING")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class UploadHistory(Base):
    __tablename__ = "UploadHistory"

    Id = Column(Integer, primary_key=True, autoincrement=True)
    Filename = Column(String(255), nullable=False)
    UploadedAt = Column(DateTime, default=datetime.utcnow)
    IsSafe = Column(Boolean, nullable=False)
    HateScore = Column(Integer)
    ViolenceScore = Column(Integer)
    SelfHarmScore = Column(Integer)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_upload_history(
    db,
    filename: str,
    is_safe: bool,
    hate_score: int,
    violence_score: int,
    self_harm_score: int,
):
    record = UploadHistory(
        Filename=filename,
        IsSafe=is_safe,
        HateScore=hate_score,
        ViolenceScore=violence_score,
        SelfHarmScore=self_harm_score,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record