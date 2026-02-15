import sys
import os
import logging
from typing import List, Any
import json

from sqlalchemy.testing import rowset

# Добавляем корневую директорию проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from google.oauth2.service_account import Credentials
import gspread
from gspread_formatting import *

from config import SERVICE_ACCOUNT_FILE
from data.models import Task, Payout
from data.db_control import get_sheet_id

logger = logging.getLogger(__name__)

def setup_sheets_api(spreadsheet_id: str):

    # 3. Настройка областей доступа
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # 4. Авторизация
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    gc = gspread.authorize(credentials)

    # 5. Открытие таблицы
    try:
        wb = gc.open_by_key(spreadsheet_id)
        logger.info("✅ Успешно подключились к таблице!")
        return wb
    except Exception as e:
        logger.warning(f"❌ Ошибка подключения: {e}")
        raise e


def format_cell(worksheet, row: int, col: int, color: str = 'yellow'):
    """
    Форматирует конкретную ячейку указанным цветом

    Args:
        worksheet: Лист Google Sheets
        row: Номер строки
        col: Номер колонки
        color: Цвет заливки ('green', 'yellow', 'white')
    """
    try:
        # Определяем цвет заливки
        if color.lower() == 'green':
            background_color = Color(0, 1, 0)  # Ярко-зеленый (Pure green)
        elif color.lower() == 'yellow':
            background_color = Color(1, 1, 0)  # Ярко-желтый (Pure yellow)
        else:  # white
            background_color = Color(1, 1, 1)  # Белый

        # Преобразуем номер колонки в буквенное обозначение
        col_letter = column_number_to_letter(col)

        # Диапазон для форматирования (только одна ячейка)
        cell_range = f'{col_letter}{row}'

        # Настройки формата ячейки
        fmt = CellFormat(
            backgroundColor=background_color,
            wrapStrategy='WRAP',
            horizontalAlignment='LEFT',
            verticalAlignment='MIDDLE',
            textFormat=TextFormat(fontSize=10)
        )

        # Применяем форматирование
        format_cell_range(worksheet, cell_range, fmt)

        logger.info(f"✅ Ячейка {cell_range} отформатирована с заливкой {color}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка форматирования ячейки {col_letter}{row}: {e}")
        raise e


def format_sheet_range(worksheet, start_row: int, end_row: int, start_col: int, end_col: int, color: str = 'white'):
    """
    Форматирует указанный диапазон ячеек

    Args:
        worksheet: Лист Google Sheets
        start_row: Начальная строка
        end_row: Конечная строка
        start_col: Начальная колонка (номер)
        end_col: Конечная колонка (номер)
        color: Цвет заливки ('green', 'yellow', 'white')
    """
    try:
        # Определяем цвет заливки
        if color.lower() == 'green':
            background_color = Color(0.8, 0.9, 0.8)  # Светло-зеленый
        elif color.lower() == 'yellow':
            background_color = Color(1, 1, 0.8)  # Светло-желтый
        else:  # white
            background_color = Color(1, 1, 1)  # Белый

        # Преобразуем номера колонок в буквенные обозначения
        start_col_letter = column_number_to_letter(start_col)
        end_col_letter = column_number_to_letter(end_col)

        # Диапазон для форматирования
        cell_range = f'{start_col_letter}{start_row}:{end_col_letter}{end_row}'

        # Настройки формата ячеек
        fmt = CellFormat(
            backgroundColor=background_color,
            wrapStrategy='WRAP',
            horizontalAlignment='LEFT',
            verticalAlignment='MIDDLE',
            textFormat=TextFormat(fontSize=10)
        )

        # Применяем форматирование
        format_cell_range(worksheet, cell_range, fmt)

        logger.info(f"✅ Диапазон {cell_range} отформатирован с заливкой {color}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка форматирования диапазона {start_col_letter}{start_row}:{end_col_letter}{end_row}: {e}")
        raise e

def get_loaders_row(worksheet, surname):
    try:
        # Получаем все значения из колонки C
        column_c = worksheet.col_values(3)
        for row, val in enumerate(column_c[1:], start=2):
            if not val:  # Пропускаем пустые строки
                continue
            val_list = val.strip().split()
            if val_list[0] != surname:
                continue
            return row
        else:
            return False
    except Exception as e:
        logger.warning(f"❌ Ошибка получения строки сотрудника: {e}")
        raise e

def get_next_row(worksheet):
    try:
        # Получаем все значения из колонки A
        column_a = worksheet.col_values(1)
        numbers = []
        for val in column_a:
            try:
                if val and str(val).strip():
                    numbers.append(int(float(val)))
            except (ValueError, TypeError):
                continue

        # Определяем следующий номер
        if numbers:
            next_number = max(numbers) + 1
        else:
            next_number = 1

        logger.info(f"📊 Последний номер в колонке A: {max(numbers) if numbers else 0}, следующий: {next_number}")

    except Exception as e:
        logger.error(f"❌ Ошибка при получении номеров строк: {e}")
        next_number = 1  # Если ошибка, начинаем с 1
        logger.info(f"📊 Используем номер по умолчанию: {next_number}")

    return next_number


def add_data_to_tasks_google_sheet(new_task: Task, month: str, date_of_the_month: str, city) -> bool:

    sheet_id = get_sheet_id(month, 'for_task')

    if not sheet_id:
        raise ValueError('Ошибка при получении ID таблицы из базы. Убедитесь, что таблица нужного месяца создана')

    wb = setup_sheets_api(sheet_id)

    if not wb:
        raise ValueError('ошибка при подключении к таблице')

    worksheet = wb.worksheet('Заявки')

    next_number = get_next_row(worksheet)

    new_row_data = [
        next_number,
        '0 ч',
        city,
        new_task.address,
        '',
        'Грузчик',
        '',
        new_task.payment,
        new_task.min_hours
    ]

    # Определяем колонку для дня
    day_column = None

    for i_day in range(1, 32):
        if int(date_of_the_month) == i_day:
            data_to_add = f'{str(new_task.loaders_count)} {new_task.time}'
            day_column = 9 + i_day  # Колонки начинаются с J (9-я колонка) для дней 1-31
        else:
            data_to_add = ''
        new_row_data.append(data_to_add)
    try:
        # Добавляем строку
        worksheet.append_row(new_row_data)

        last_row = len(worksheet.get_all_values())
        last_col = len(new_row_data)

        logger.info(f"📊 Добавлена строка с {last_col} колонками")

        # Проверим реальное количество колонок в таблице
        logger.info(f"📊 Добавлена строка с {last_col} колонками")

        # Форматируем всю строку с базовым форматированием (белый цвет)
        format_sheet_range(
            worksheet,
            start_row=last_row,
            end_row=last_row,
            start_col=1,
            end_col=last_col,
            color='white'
        )

        # Форматируем 2 ячейки цветом
        if day_column:
            format_cell(
                worksheet,
                row=last_row,
                col=day_column,
                color='yellow'
            )
            logger.info(f"✅ Ячейка {column_number_to_letter(day_column)}{last_row} выделена желтым цветом")

        logger.info(f"✅ Строка {last_row} добавлена, ячейка с данными выделена желтым")
    except Exception as e:
        logger.error(f"❌ Ошибка добавления строки: {e}")
        raise e

    return True

def add_loader_data_to_loader_google_sheet(new_payout: Payout, month: str, date_of_the_month: str) -> bool:

    sheet_id = get_sheet_id(month, 'for_loader')


    if not sheet_id:
        raise ValueError('Ошибка при получении ID таблицы из базы. Убедитесь, что таблица нужного месяца создана')

    wb = setup_sheets_api(sheet_id)

    if not wb:
        raise ValueError('ошибка при подключении к таблице')

    worksheet = wb.worksheet('Грузчики')


    loaders_payment_str = new_payout.loaders_payments
    loaders_payment_list = loaders_payment_str.split(',')
    for i_loaders_payment in loaders_payment_list:

        if not i_loaders_payment:
            continue

        parts = i_loaders_payment.split('-')
        if len(parts) != 2:
            logger.error(f"❌ Неверный формат строки: {i_loaders_payment}")
            continue

        loaders, payment = parts
        loaders = loaders.strip()
        payment = payment.strip()
        payment = int(payment)

        loaders_list = loaders.split()
        surname = loaders_list[0]

        loaders_row = get_loaders_row(worksheet, surname)

        if not loaders_row:

            next_number = get_next_row(worksheet)

            # Ставка за час = выплата / количество часов
            rate_per_hour = int(payment / new_payout.hours)

            new_row_data = [
                next_number,  # A: Пп
                new_payout.address,  # B: Адрес
                loaders,  # C: ФИО
                '',  # D: тел номер
                rate_per_hour,  # E: Ставка магазина
                rate_per_hour,  # F: Ставка /час
            ]

            # Определяем колонку для дня
            day_column = None

            for i_day in range(1, 32):
                if int(date_of_the_month) == i_day:
                    data_to_add = new_payout.hours
                    day_column = 6 + i_day  # Колонки начинаются с G (7-я колонка) для дней 1-31
                else:
                    data_to_add = ''
                new_row_data.append(data_to_add)

            additional_info = [
                '',  # AK: Пустая колонка после дней! ⚠️ ЭТО ВАЖНО
                new_payout.hours if int(date_of_the_month) <= 15 else 0,  # AL: Кол-во час с 1 по 15
                new_payout.hours if int(date_of_the_month) > 15 else 0,  # AM: Кол-во час с 16 по 31
                new_payout.hours,  # AN: Итого час/sku
                '',  # AO: Удержание
                payment,  # AP: Выплата
                payment,  # AQ: Итого к оплате
                payment,  # AR: Итого сумма за месяц
                '',  # AS: Доп траты
                '',  # AT: ФИО держателя карты
                '',  # AU: № карты
                '',  # AV: Наименование банка
                ''  # AW: Телефон номер
            ]

            new_row_data += additional_info

            try:
                # Добавляем строку
                worksheet.append_row(new_row_data)

                # Форматируем добавленную строку
                last_row = len(worksheet.get_all_values())
                last_col = len(new_row_data)

                logger.info(f"📊 Добавлена новая строка для {surname} с {last_col} колонками")

                # Форматируем всю строку с базовым форматированием (белый цвет)
                format_sheet_range(
                    worksheet,
                    start_row=last_row,
                    end_row=last_row,
                    start_col=1,
                    end_col=last_col,
                    color='white'
                )

                # Форматируем конкретную ячейку с часами зеленым цветом
                if day_column:
                    format_cell(
                        worksheet,
                        row=last_row,
                        col=day_column,
                        color='green'
                    )
                logger.info(f"✅ Ячейка {column_number_to_letter(day_column)}{last_row} выделена зеленым цветом")

                # Добавляем комментарий к ячейке выплаты (колонка AQ)
                cell_address = f"AQ{last_row}"
                worksheet.insert_note(cell_address, new_payout.comment)
                logger.info(f"✅ Добавлен комментарий к ячейке {cell_address}: {new_payout.comment}")

                logger.info(f"✅ Добавлена новая строка {last_row} для сотрудника {surname}, ячейка с часами выделена зеленым")

            except Exception as e:
                logger.error(f"❌ Ошибка добавления строки: {e}")
                raise e
        else:
            try:
                row_number = loaders_row

                #Определяем ставку работника
                employee_rate_cell = worksheet.cell(row_number, 6)

                if not employee_rate_cell.value:
                    raise ValueError('отсутствует значение ставки работника за час')

                current_employee_rate = int(employee_rate_cell.value)

                # Дни начинаются с колонки G (7-я колонка)
                day_column = 6 + int(date_of_the_month)

                # Получаем текущие часы
                current_cell = worksheet.cell(row_number, day_column)
                current_hours = int(current_cell.value) if current_cell.value else 0

                # Добавляем новые часы
                new_hours = current_hours + int(new_payout.hours)
                worksheet.update_cell(row_number, day_column, new_hours)

                # Обновляем итоговые колонки
                # Кол-во час с 1 по 15
                if int(date_of_the_month) <= 15:
                    first_half_cell = worksheet.cell(row_number, 39)
                    first_half = int(first_half_cell.value) if first_half_cell.value else 0
                    worksheet.update_cell(row_number, 39, first_half + int(new_payout.hours))
                else:
                    # Кол-во час с 16 по 31
                    second_half_cell = worksheet.cell(row_number, 40)
                    second_half = int(second_half_cell.value) if second_half_cell.value else 0
                    worksheet.update_cell(row_number, 40, second_half + int(new_payout.hours))

                # Итого час (колонка 41)
                total_hours_cell = worksheet.cell(row_number, 41)
                total_hours = int(total_hours_cell.value) if total_hours_cell.value else 0
                worksheet.update_cell(row_number, 41, total_hours + int(new_payout.hours))

                # Обновляем Итого к оплате (колонка 44)
                new_total_payment = int(new_payout.hours) * current_employee_rate
                worksheet.update_cell(row_number, 44, new_total_payment)

                # Обновляем выплату (колонка 43)
                payment_cell = worksheet.cell(row_number, 43)
                current_payment = int(payment_cell.value) if payment_cell.value else 0
                worksheet.update_cell(row_number, 43, current_payment + new_total_payment)

                # Получаем текущий комментарий к ячейке (колонка AQ)
                cell_address = f"AQ{row_number}"
                current_note = worksheet.get_note(cell_address)  # Используем строковый адрес


                # Если комментарий уже существует, добавляем новую информацию
                if current_note:
                    new_note = current_note + "\n---\n" + new_payout.comment
                else:
                    new_note = new_payout.comment

                # Обновляем комментарий (колонка 43)
                worksheet.insert_note(cell_address, new_note)  # Используем строковый адрес
                logger.info(f"✅ Обновлен комментарий к ячейке {cell_address}")

                # Итого сумма за месяц (колонка 45)
                month_total_cell = worksheet.cell(row_number, 45)
                month_total = int(month_total_cell.value) if month_total_cell.value else 0
                worksheet.update_cell(row_number, 45, month_total + new_total_payment)

                # Форматируем всю строку с базовым форматированием (белый цвет)
                max_col = 49  # Колонка AW
                format_sheet_range(
                    worksheet,
                    start_row=row_number,
                    end_row=row_number,
                    start_col=1,
                    end_col=max_col,
                    color='white'
                )

                # Форматируем обновленную ячейку с часами зеленым цветом
                format_cell(
                    worksheet,
                    row=row_number,
                    col=day_column,
                    color='green'
                )

                logger.info(f"✅ Обновлена строка {row_number} для сотрудника {surname}, ячейка {column_number_to_letter(day_column)}{row_number} выделена зеленым")

            except Exception as e:
                logger.error(f"❌ Ошибка при обновлении строки для {surname}: {e}")
                raise e

    return True


def column_number_to_letter(col_num: int) -> str:
    """Преобразует номер колонки в буквенное обозначение (A, B, ..., Z, AA, AB, ...)"""
    letters = ''
    while col_num > 0:
        col_num -= 1
        letters = chr(col_num % 26 + 65) + letters
        col_num = col_num // 26
    return letters

