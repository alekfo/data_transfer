from email.policy import default

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Sheet(Base):
    __tablename__ = "google_sheets"

    id = Column(Integer, primary_key=True)
    mark = Column(String(20), nullable=False) #can be "for_task" or "for_loader"
    url = Column(String(100), nullable=False)
    google_sheet_id = Column(String(100), nullable=False)
    month = Column(String(100), nullable=False)
    added_at = Column(DateTime, default=datetime.now())


    def __repr__(self):
        return (f"<Sheet(id={self.id}, "
                f"google_sheet_id={self.google_sheet_id}, "
                f"month={self.month}, "
                f"added_at='{self.added_at}')>")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    date = Column(String(50), nullable=False)
    time = Column(String(50), nullable=False)
    address = Column(String(100), nullable=False)
    loaders_count = Column(Integer, nullable=False)
    type_of_work = Column(String(500), nullable=False)
    payment = Column(Integer, nullable=False)
    performers = Column(String(500), nullable=True)
    min_hours = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now())

class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True)
    date = Column(String(50), nullable=False)
    address = Column(String(100), nullable=False)
    hours = Column(Integer, nullable=False)
    loaders_payments = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now())