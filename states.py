from aiogram.fsm.state import State, StatesGroup

# 2. Создаем класс состояний
class AdminStates(StatesGroup):
    """Класс для хранения состояний админа"""
    in_admins_main_menu = State()
    getting_sheet_id = State()
    getting_month = State()
    choising_type_of_table = State()
    choise_action = State()
    getting_tasks_data = State()
    getting_loaders_data = State()
    got_all_tables = State()
