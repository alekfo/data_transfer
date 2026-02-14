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
from keyboards.main_keyboard import all_links_keyboard_with_delete, return_keyboard, admins_main_menu_keyboard
from data.db_control import get_all_tables, delete_table_by_id

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
            f"👇 *Нажмите на кнопку, чтобы открыть таблицу:*\n"
            f"❌ *Для удаления таблицы нажмите соответствующую кнопку*"
        )

        # Отправляем сообщение с клавиатурой ссылок и кнопками удаления
        await callback_query.message.answer(
            stats_message,
            reply_markup=all_links_keyboard_with_delete(all_tables),
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


@get_tables_route.callback_query(lambda c: c.data.startswith('delete_table_'), AdminStates.got_all_tables)
async def delete_table_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик удаления таблицы по callback_data с ID таблицы
    """
    try:
        # Извлекаем ID таблицы из callback_data
        table_id = int(callback_query.data.replace('delete_table_', ''))

        logger.info(f"🗑️ Попытка удаления таблицы с ID {table_id} пользователем {callback_query.from_user.id}")

        # Удаляем таблицу из базы
        result = delete_table_by_id(table_id)

        if result:
            await callback_query.message.answer(
                f"✅ *Таблица успешно удалена из базы данных*\n\n"
                f"Обновляю список таблиц...",
                parse_mode="Markdown"
            )

            # Получаем обновленный список таблиц
            all_tables = get_all_tables()

            # Подсчитываем статистику
            total_count = len(all_tables['for_task']) + len(all_tables['for_loader'])

            # Обновляем сообщение со списком таблиц
            stats_message = (
                f"📊 *Доступные Google-таблицы*\n\n"
                f"┌─────────────────────┐\n"
                f"│   📋 СТАТИСТИКА      │\n"
                f"└─────────────────────┘\n\n"
                f"📋 *Таблицы заявок:* `{len(all_tables['for_task'])}`\n"
                f"💰 *Таблицы грузчиков:* `{len(all_tables['for_loader'])}`\n"
                f"📚 *Всего таблиц:* `{total_count}`\n\n"
                f"👇 *Нажмите на кнопку, чтобы открыть таблицу:*\n"
                f"❌ *Для удаления таблицы нажмите соответствующую кнопку*"
            )

            await callback_query.message.answer(
                stats_message,
                reply_markup=all_links_keyboard_with_delete(all_tables),
                parse_mode="Markdown"
            )

        else:
            await callback_query.message.answer(
                f"❌ *Таблица с ID {table_id} не найдена в базе данных*",
                parse_mode="Markdown"
            )

    except ValueError:
        logger.error(f"❌ Ошибка при парсинге ID таблицы из callback_data: {callback_query.data}")
        await callback_query.message.answer(
            "❌ *Ошибка при обработке запроса на удаление*\n\n"
            "Некорректный ID таблицы",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении таблицы: {e}")
        await callback_query.message.answer(
            f"❌ *Ошибка при удалении таблицы*\n\n"
            f"`{e}`\n\n"
            f"Пожалуйста, обратитесь к разработчикам",
            parse_mode="Markdown"
        )
    finally:
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