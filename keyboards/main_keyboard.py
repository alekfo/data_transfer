from typing import List, Any, Dict, Optional

from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import types


# Создаем клавиатуру для приветствия
def admins_main_menu_keyboard():
    """
    Создает инлайн-клавиатуру с двумя кнопками в столбик
    """
    builder = InlineKeyboardBuilder()

    admin_menu_sections = [
        ("Добавить таблицу", "add_table"),
        ("Добавить данные в Google-таблицу", "add_data"),
        ("Все таблицы", "all_tables")
    ]

    for i_section in admin_menu_sections:
        # Добавляем кнопки по одной
        builder.row(types.InlineKeyboardButton(
            text=i_section[0],
            callback_data=i_section[1]
        ))

    return builder.as_markup()

def return_keyboard():
    """Создает клавиатуру с кнопками Вернуться в основное меню"""

    builder = ReplyKeyboardBuilder()

    builder.row(
        types.KeyboardButton(text="Вернуться в основное меню")
    )

    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def month_keyboard():
    """Создаем клавиатуру с месяцами"""

    month_list = [
        ("Январь", "january"),
        ("Февраль", "february"),
        ("Март", "march"),
        ("Апрель", "april"),
        ("Май", "may"),
        ("Июнь", "june"),
        ("Июль", "july"),
        ("Август", "august"),
        ("Сентябрь", "september"),
        ("Окторябрь", "october"),
        ("Ноябрь", "november"),
        ("Декабрь", "december"),
        ("Вернуться в меню", "back")
    ]

    builder = InlineKeyboardBuilder()

    for month in month_list:
        # Описываем все кнопки
        builder.add(
            types.InlineKeyboardButton(
                text=month[0],
                callback_data=month[1]
            )
        )
    # Указываем, как расположить кнопки: 2 в первом ряду
    builder.adjust(2, 2, 2, 2, 2, 2, 1)

    return builder.as_markup()

def yes_or_now_keyboard():
    builder = InlineKeyboardBuilder()

    admin_menu_sections = [
        ("✅Да", "yes"),
        ("❌Нет", "no")
    ]

    for i_section in admin_menu_sections:
        # Добавляем кнопки по одной
        builder.row(types.InlineKeyboardButton(
            text=i_section[0],
            callback_data=i_section[1]
        ))

    return builder.as_markup()

def actions_keyboard():

    builder = InlineKeyboardBuilder()

    admin_menu_sections = [
        ("Заявки", "tasks"),
        ("Грузчики", "loaders"),
        ("Вернуться в меню", "back")
    ]

    for i_section in admin_menu_sections:
        # Добавляем кнопки по одной
        builder.row(types.InlineKeyboardButton(
            text=i_section[0],
            callback_data=i_section[1]
        ))

    return builder.as_markup()

def choise_table_type_keyboard():

    builder = InlineKeyboardBuilder()

    admin_menu_sections = [
        ("Заявки", "for_task"),
        ("Грузчики", "for_loader"),
        ("Вернуться в меню", "back")
    ]

    for i_section in admin_menu_sections:
        # Добавляем кнопки по одной
        builder.row(types.InlineKeyboardButton(
            text=i_section[0],
            callback_data=i_section[1]
        ))

    return builder.as_markup()


def all_links_keyboard(tables_data: Dict[str, List[Dict[str, str]]]):
    """
    Создает инлайн-клавиатуру со всеми таблицами, сгруппированными по типу

    Args:
        tables_data: Словарь с таблицами из get_all_tables()
    """
    builder = InlineKeyboardBuilder()

    # Заголовок для таблиц с заявками
    if tables_data['for_task']:
        builder.row(
            types.InlineKeyboardButton(
                text="📋 ТАБЛИЦЫ ЗАЯВОК",
                callback_data="header_tasks"
            )
        )

        # Сортируем по месяцу
        sorted_tasks = sorted(tables_data['for_task'], key=lambda x: x['month'])

        for table in sorted_tasks:
            button_text = f"📅 {table['month']} - Заявки"
            builder.row(
                types.InlineKeyboardButton(
                    text=button_text,
                    url=table['url']
                )
            )

    # Заголовок для таблиц грузчиков
    if tables_data['for_loader']:
        builder.row(
            types.InlineKeyboardButton(
                text="💰 ТАБЛИЦЫ ГРУЗЧИКОВ",
                callback_data="header_loaders"
            )
        )

        # Сортируем по месяцу
        sorted_loaders = sorted(tables_data['for_loader'], key=lambda x: x['month'])

        for table in sorted_loaders:
            button_text = f"📅 {table['month']} - Грузчики"
            builder.row(
                types.InlineKeyboardButton(
                    text=button_text,
                    url=table['url']
                )
            )

    # Если таблиц нет
    if not tables_data['for_task'] and not tables_data['for_loader']:
        builder.row(
            types.InlineKeyboardButton(
                text="❌ Таблицы не найдены",
                callback_data="no_tables"
            )
        )

    # Кнопка возврата
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Вернуться в меню",
            callback_data="back_to_menu"
        )
    )

    return builder.as_markup()