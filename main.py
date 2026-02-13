import logging

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from data.db_control import init_db
from handlers.common_handlers import common_router, cancel_router
from handlers.add_table_handlers import add_table_route
from handlers.add_data_handlers import add_data_route
from handlers.get_all_tables_handlers import get_tables_route


# Включаем логирование, чтобы видеть что происходит
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Инициализируем бота и диспетчер
logger = logging.getLogger('main_logger')
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


dp.include_router(cancel_router)
dp.include_router(common_router)
dp.include_router(add_table_route)
dp.include_router(add_data_route)
dp.include_router(get_tables_route)

# Главная асинхронная функция
async def main():
    """
    Запуск бота
    """
    init_db()
    # Запускаем polling (постоянный опрос серверов Telegram)
    logger.info('Бот запущен')
    # Установка команд бота
    await bot.set_my_commands([
        BotCommand(command="/start", description="Начать"),
        BotCommand(command="/cancel", description="Отменить текущее действие")
    ])
    await dp.start_polling(bot)


# Точка входа в программу
if __name__ == "__main__":
    try:
        # Запускаем бота
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info('Бот остановлен')
    except Exception as e:
        logger.error(f'Ошибка запуска бота: {e}')