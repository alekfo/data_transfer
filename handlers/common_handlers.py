import logging

from aiogram import types, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart

from states import AdminStates
from config import admin_id_first, admin_id_second
from keyboards.main_keyboard import admins_main_menu_keyboard

logger = logging.getLogger(__name__)
common_router = Router()
cancel_router = Router()

ADMIN_IDS = [admin_id_first, admin_id_second]

@common_router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Этот обработчик срабатывает на команду /start и при первом входе
    """
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer(
            f'Вы яляетесь администратором чат-бота\n\n'
            f'Выберите действие🚀',
            reply_markup=admins_main_menu_keyboard()
        )
        await state.set_state(AdminStates.in_admins_main_menu)
        return

    # Сохраняем данные пользователя в state
    await state.update_data(
        clients_id=user_id
    )

    await message.answer(
        'Вы не являетесь администратором чат-бота. Пожалуйста, обратитесь к разработчикам.'
    )

@common_router.message(StateFilter(None))
async def handle_any_message(message: types.Message, state: FSMContext):
    """Обработчик любых сообщений без состояния"""
    await cmd_start(message, state)


@cancel_router.message(Command("cancel"))
@cancel_router.message(lambda message: message.text == "Вернуться в основное меню")
async def cancel_handler(message: types.Message, state: FSMContext):
    """Сброс состояния"""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        "Используйте /start для начала работы.",
        reply_markup=types.ReplyKeyboardRemove()
    )