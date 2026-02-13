from math import lgamma
from datetime import datetime
from io import BytesIO
import logging
import re

from aiogram import types, F, Router, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram.types import ReplyKeyboardRemove

from config import admin_id_first, admin_id_second
from states import AdminStates
from handlers.common_handlers import cancel_handler
from keyboards.main_keyboard import month_keyboard, return_keyboard, choise_table_type_keyboard
from data.db_control import add_table, is_table_exist

logger = logging.getLogger(__name__)
add_table_route = Router()

@add_table_route.callback_query(lambda c: c.data == "add_table", AdminStates.in_admins_main_menu)
async def start_adding_table(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.choising_type_of_table)

    await callback_query.message.answer(f"*Выберите тип таблицы*\n",
                                        reply_markup=choise_table_type_keyboard(),
                                        parse_mode="Markdown"
                                        )



@add_table_route.callback_query(AdminStates.choising_type_of_table)
async def start_adding_table(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса от кнопки "Добавить таблицу"
    только в состоянии AdminStates.in_admins_main_menu
    """

    gotten_data = callback_query.data.strip()

    if gotten_data == "back":
        await cancel_handler(callback_query.message, state)
        return
    await state.update_data(
        sheet_type=gotten_data
    )

    await state.set_state(AdminStates.getting_sheet_id)

    await callback_query.message.answer(f"Пришлите *URL таблицы.*\n\n"
                                        f"*URL Google-таблицы* можно найти, кликнув на адресную строку с таблицей",
                                        parse_mode="Markdown"
    )

@add_table_route.message(AdminStates.getting_sheet_id)
async def got_table_id(message: types.Message, state: FSMContext):

    url = message.text.strip()

    # Извлекаем ID между /d/ и /edit или до следующего знака
    pattern = r'/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, url)

    if match:

        gotten_sheet_id = match.group(1)

        await state.update_data(
            sheet_id=gotten_sheet_id,
            url=url
        )

        await state.set_state(AdminStates.getting_month)

        await message.answer(
            f"За какой месяц таблица?",
            reply_markup=month_keyboard()
        )
    else:
        await message.answer(
            "❌❌Не удалось распознать ID таблицы."
            "Пожалуйста, отправьте корректную ссылку на Google таблицу или вернитесь в основное меню.\n"
            "Пример: https://docs.google.com/spreadsheets/d/ID_ТАБЛИЦЫ/edit...",
            reply_markup=return_keyboard()
        )

@add_table_route.callback_query(AdminStates.getting_month)
async def start_adding_table(callback_query: types.CallbackQuery, state: FSMContext):

    MONTH_NAMES = {
        "january": "Январь",
        "february": "Февраль",
        "march": "Март",
        "april": "Апрель",
        "may": "Май",
        "june": "Июнь",
        "july": "Июль",
        "august": "Август",
        "september": "Сентябрь",
        "october": "Октябрь",
        "november": "Ноябрь",
        "december": "Декабрь"
    }

    gotten_data = callback_query.data.strip()
    button_text = MONTH_NAMES.get(gotten_data, gotten_data)

    await state.update_data(
        month=button_text
    )

    saved_data = await state.get_data()

    if gotten_data == "back":
        await cancel_handler(callback_query.message, state)
        return

    try:
        table = is_table_exist(button_text, saved_data['sheet_type'])
    except Exception as e:
        await callback_query.message.answer(
            f"❌Ошибка при проверке существования таблицы в базе: {e}.\n\n"
            f"Обратитесь к разработчикам",
            reply_markup=return_keyboard()
        )
        return

    if table:
        await callback_query.message.answer(
            f"В базе уже существует таблица за {button_text}.\n\n"
            f"Уточните данные и попробуйте позже",
            reply_markup=return_keyboard()
        )
        return
    if saved_data['sheet_type'] == 'for_task':
        target_for_output = 'задач'
    elif saved_data['sheet_type'] == 'for_loader':
        target_for_output = 'грузчиков'
    else:
        target_for_output = '***'

    try:
        table = add_table(saved_data['sheet_type'], saved_data['url'], saved_data['sheet_id'], saved_data['month'])
        if table:
            await callback_query.message.answer(
                f"✅Таблица за *{button_text}* для *{target_for_output}* успешно добавлена в базу",
                reply_markup=return_keyboard(),
                parse_mode="Markdown"
            )
    except Exception as e:
        await callback_query.message.answer(
            f"❌Ошибка при добавлении таблицы в базу: {e}.\n\n"
            f"Обратитесь к разработчикам",
            reply_markup=return_keyboard()
        )

@add_table_route.message(AdminStates.getting_month)
async def got_road(message: types.Message, state: FSMContext):
    await message.answer(
        f"❌Выберите действие из предложенных или вернитесь в основное меню:",
        reply_markup=month_keyboard()
    )