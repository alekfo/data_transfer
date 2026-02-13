import os
import json
from datetime import datetime, timedelta
from typing import List, Any, Dict, Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, func, extract, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from data.models import Base, Sheet, Task, Payout


engine = create_engine("sqlite:///data/google_sheets.db", echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def add_table(sheet_type: str, url: str, sheet_id: str, month: str) -> Optional[Sheet]:
    with SessionLocal() as session:
        new_sheet = Sheet(
            mark=sheet_type,
            url=url,
            google_sheet_id=sheet_id,
            month=month
        )
        session.add(new_sheet)
        session.commit()
        session.refresh(new_sheet)
        return new_sheet

def add_task(data: dict) -> Task:
    with SessionLocal() as session:
        performers_str = ', '.join(data['performers']) if data['performers'] else ''

        new_task = Task(
            date=data['date'],
            time = data['time'],
            address=data['address'],
            loaders_count=data['loaders_count'],
            type_of_work=data['type_of_work'],
            payment=data['payment'],
            performers=performers_str
        )
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task

def find_task(data: dict) -> Optional[Task]:
    with SessionLocal() as session:
        return session.query(Task).filter(
            Task.date == data['date'],
            Task.time == data['time'],
            Task.address == data['address'],
            Task.loaders_count == data['loaders_count'],
            Task.type_of_work == data['type_of_work'],
            Task.payment == data['payment']
        ).first()

def get_sheet_id(month: str, sheet_type: str) -> Optional[str]:
    with SessionLocal() as session:
        sheet = session.query(Sheet).filter(Sheet.month == month, Sheet.mark == sheet_type).one_or_none()
        if sheet:
            return sheet.google_sheet_id
        return None

def add_payout(date: str, address: str, hours: int, loaders_payments: List[dict]) -> Payout:
    with SessionLocal() as session:
        loaders_payments_str = ''
        for i_load in loaders_payments:
            loaders_payments_str += f"{i_load['name']}-{i_load['payment']},"

        new_payout = Payout(
            date = date,
            address = address,
            hours = hours,
            loaders_payments = loaders_payments_str
        )
        session.add(new_payout)
        session.commit()
        session.refresh(new_payout)
        return new_payout

def find_payout(data: dict) -> Optional[Payout]:
    with SessionLocal() as session:
        loaders_payments_str = ''
        for i_load in data['loaders_payments']:
            loaders_payments_str += f"{i_load['name']}-{i_load['payment']},"

        return session.query(Payout).filter(
            Payout.date == data['date'],
            Payout.address == data['address'],
            Payout.hours == data['hours'],
            Payout.loaders_payments == loaders_payments_str
        ).first()


def get_all_tables() -> Dict[str, List[Dict[str, str]]]:
    with SessionLocal() as session:
        sheets = session.query(Sheet).order_by(Sheet.month, Sheet.mark).all()

        result = {
            'for_task': [],
            'for_loader': []
        }

        for sheet in sheets:
            sheet_data = {
                'id': sheet.id,
                'month': sheet.month,
                'url': sheet.url,
                'google_sheet_id': sheet.google_sheet_id,
                'added_at': sheet.added_at.strftime('%d.%m.%Y') if sheet.added_at else ''
            }

            if sheet.mark == 'for_task':
                result['for_task'].append(sheet_data)
            elif sheet.mark == 'for_loader':
                result['for_loader'].append(sheet_data)

        return result

def is_table_exist(month: str, sheet_type: str) -> Optional[Sheet]:
    with SessionLocal() as session:
        sheet = session.query(Sheet).filter(Sheet.month == month, Sheet.mark == sheet_type).one_or_none()
        return sheet

