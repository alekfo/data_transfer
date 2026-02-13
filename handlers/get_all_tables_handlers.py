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
from keyboards.main_keyboard import all_links_keyboard, return_keyboard, admins_main_menu_keyboard
from data.db_control import get_all_tables

logger = logging.getLogger(__name__)
get_tables_route = Router()

@get_tables_route.callback_query(lambda c: c.data == "all_tables", AdminStates.in_admins_main_menu)
async def start_adding_table(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        all_tables = get_all_tables()

        # Подсчитываем общее количество таблиц
        total_count = len(all_tables['for_task']) + len(all_tables['for_loader'])

        # Формируем сообщение со статистикой
        stats_message = (
            f"📊 *Доступные Google-таблицы*\n\n"
            f"┌─────────────────────┐\n"
            f"│   📋 СТАТИСТИКА      │\n"
            f"└─────────────────────┘\n\n"
            f"📋 *Таблицы заявок:* `{len(all_tables['for_task'])}`\n"
            f"💰 *Таблицы грузчиков:* `{len(all_tables['for_loader'])}`\n"
            f"📚 *Всего таблиц:* `{total_count}`\n\n"
            f"👇 *Нажмите на кнопку, чтобы открыть таблицу:*"
        )

        # Отправляем сообщение с клавиатурой ссылок
        await callback_query.message.answer(
            stats_message,
            reply_markup=all_links_keyboard(all_tables),
            parse_mode="Markdown"
        )

        await state.set_state(AdminStates.got_all_tables)

    except Exception as e:
        logger.error(f"❌ Ошибка при получении списка таблиц: {e}")
        await callback_query.message.answer(
            f"❌ *Ошибка при получении списка таблиц*\n\n"
            f"`{e}`\n\n"
            f"Пожалуйста, обратитесь к разработчикам",
            reply_markup=return_keyboard(),
            parse_mode="Markdown"
        )
        await callback_query.answer()


@get_tables_route.callback_query(lambda c: c.data == "back_to_menu", AdminStates.got_all_tables)
async def back_to_menu_from_tables(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Возврат в главное меню из раздела таблиц
    """
    await state.set_state(AdminStates.in_admins_main_menu)

    await callback_query.message.answer(
        "Выберите действие:",
        reply_markup=admins_main_menu_keyboard()
    )
    await callback_query.answer()