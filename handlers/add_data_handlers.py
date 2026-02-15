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
from keyboards.main_keyboard import month_keyboard, return_keyboard, yes_or_now_keyboard, actions_keyboard
from data.db_control import add_table, add_task, find_task, add_payout, find_payout
from google_sheet_service.manage_google_sheet import add_data_to_tasks_google_sheet, add_loader_data_to_loader_google_sheet

logger = logging.getLogger(__name__)
add_data_route = Router()

MONTH_NUMBERS = {
        1: "Январь",
        2: "Февраль",
        3: "Март",
        4: "Апрель",
        5: "Май",
        6: "Июнь",
        7: "Июль",
        8: "Август",
        9: "Сентябрь",
        10: "Октябрь",
        11: "Ноябрь",
        12: "Декабрь"
    }

@add_data_route.callback_query(lambda c: c.data == "add_data", AdminStates.in_admins_main_menu)
async def start_adding_data(callback_query: types.CallbackQuery, state: FSMContext):

    await state.set_state(AdminStates.choise_action)
    await callback_query.message.answer(f"В какую таблицу хотите добавить данные?",
                                        reply_markup=actions_keyboard(),
                                        parse_mode="Markdown"
                                        )

@add_data_route.callback_query(AdminStates.choise_action)
async def start_adding_data(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса от кнопки "Добавить данные в таблицу"
    только в состоянии AdminStates.in_admins_main_menu
    """
    gotten_data = callback_query.data.strip()

    if gotten_data == "back":
        await cancel_handler(callback_query.message, state)
        return
    elif gotten_data == "tasks":
        await state.set_state(AdminStates.getting_tasks_data)
        await callback_query.message.answer(f"Пришлите данные для добавления в таблицу. Формат:\n\n"
                                            "📎 *СКОПИРУЙТЕ ЭТОТ ШАБЛОН:*\n\n"
                                            "\n"
                                            "Дата 11.11.2026  к 09:00 часам\n"
                                            "Югорск, Столичный Сити  ул. Ленина, 2\n"
                                            "\n"
                                            "На подработку требуются в магазины \"Галамарт\" - 2 грузчика\n"
                                            "\n"
                                            "Характер работы: подготовить склад для разгрузки, выбросить картон, выгрузка по коробочно товар из машины перенести на склад, расформировать товар по местам хранения.\n"
                                            "( оплата от 3 ч )\n"
                                            "Оплата 300 руб/час , выплата по окончанию смены\n"
                                            "\n"
                                            "Петров Игорь\n"
                                            "Брезгин Денис\n"
                                            "\n\n"
                                            "🔄 *Замените данные и отправьте сообщение*",
                                            parse_mode="Markdown"
                                            )
    elif gotten_data == "loaders":
        await state.set_state(AdminStates.getting_loaders_data)
        await callback_query.message.answer(f"Пришлите данные для добавления в таблицу. Формат:\n\n"
                                            "📎 *Воспользуйтесь ШАБЛОНОМ:*\n\n"
                                            "Реестр оплачен  09.02.2026\n"
                                            "Югорск, Столичный Сити  ул. Ленина, 2\n"
                                            "\n"
                                            "Петров Игорь\n"
                                            "900 рублей\n"
                                            "\n"
                                            "Брезгин Денис\n"
                                            "900\n"
                                            "\n"
                                            "3 часа\n\n"
                                            "🔄 *Замените данные и отправьте сообщение*",
                                            parse_mode="Markdown"
                                            )

@add_data_route.message(AdminStates.getting_tasks_data)
async def parse_task_data(message: types.Message, state: FSMContext):

    text = message.text
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    # 1. Парсим дату и время
    date_time_pattern = r'Дата\s+(\d{2}\.\d{2}\.\d{4})\s+к\s+(\d{2}:\d{2})\s+часам'
    date_time_match = re.search(date_time_pattern, text)
    date = date_time_match.group(1) if date_time_match else None
    time = date_time_match.group(2) if date_time_match else None

    # 2. ПАРСИМ АДРЕС (вторая строка)
    address = None
    if len(lines) > 1:
        # Ищем строку с адресом (содержит ул., г., Сити и т.д.)
        for line in lines[1:3]:
            if any(word in line.lower() for word in ['ул.', 'улица', 'г.', 'город', 'сити', 'пр.', 'проспект']):
                address = line
                break

    # 3. ПАРСИМ КОЛИЧЕСТВО ГРУЗЧИКОВ
    loaders_count = None
    loaders_patterns = [
        r'[-–—]\s*(\d+)\s*грузчик',  # - 2 грузчика
        r'требуются.*?(\d+)\s*грузчик',  # требуются 2 грузчика
        r'(\d+)\s*грузчика',  # 2 грузчика
        r'(\d+)\s*чел\.?\s*грузчиков',  # 2 чел. грузчиков
    ]
    for pattern in loaders_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            loaders_count = int(match.group(1))
            break

    # 4. Парсим минимальное количество часов из строки "( оплата от 3 ч )"
    min_hours = None
    hours_patterns = [
        r'\(\s*оплата\s+от\s+(\d+)\s*ч\s*\)',  # ( оплата от 3 ч )
        r'оплата\s+от\s+(\d+)\s*часа?',  # оплата от 3 часа
        r'от\s+(\d+)\s*ч\.?\s*\)?',  # от 3 ч
    ]

    for pattern in hours_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            min_hours = int(match.group(1))
            logger.info(f"✅ Найдено минимальное количество часов: {min_hours}")
            break

    # 5. Парсим тип работ (все что между "Характер работы:" и "( оплата от")
    work_pattern = r'Характер работы:\s*(.+?)\s*\(\s*оплата от'
    work_match = re.search(work_pattern, text, re.DOTALL)

    type_of_work = work_match.group(1).strip() if work_match else None

    # 6. Парсим оплату
    payment_pattern = r'Оплата\s+(\d+)\s*руб/час'
    payment_match = re.search(payment_pattern, text)
    payment = int(payment_match.group(1)) if payment_match else None

    # 7. ПАРСИМ ФАМИЛИИ ГРУЗЧИКОВ (только русские фамилии с именами)
    performers = []
    # Ищем строки, которые содержат фамилию и имя (Фамилия Имя)
    performer_pattern = r'^([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)$'

    for line in lines:
        line = line.strip()
        # Пропускаем строки, которые явно не являются фамилиями
        if (line.startswith('Дата') or
                line.startswith('На подработку') or
                line.startswith('Характер работы') or
                line.startswith('( оплата') or
                line.startswith('Оплата') or
                'ул.' in line or
                'Сити' in line or
                'грузчик' in line.lower()):
            continue

        # Проверяем, похожа ли строка на фамилию и имя
        if re.match(performer_pattern, line):
            # Дополнительная проверка: не является ли это адресом или другим текстом
            if not any(city in line for city in ['Югорск', 'Ленина', 'Москва', 'Оренбург']):
                performers.append(line)

    # Формируем результат
    parsed_data = {
        "date": date,
        "time": time,
        "address": address,
        "loaders_count": loaders_count,
        "type_of_work": type_of_work,
        "payment": payment,
        "min_hours": min_hours,
        "performers": performers,
        "raw_text": text
    }

    # Сохраняем в state
    await state.update_data(parsed_task=parsed_data)

    # Формируем красивый ответ с эмодзи (используем HTML вместо Markdown)
    response = (
        f"✅ <b>ДАННЫЕ УСПЕШНО РАСПОЗНАНЫ</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│   📋 РЕЗУЛЬТАТ       │\n"
        f"└─────────────────────┘\n\n"
        f"📅 <b>Дата:</b> <code>{date if date else 'нет данных'}</code>\n"
        f"⏰ <b>Время:</b> <code>{time if time else 'нет данных'}</code>\n"
        f"📍 <b>Адрес:</b> <code>{address if address else 'нет данных'}</code>\n"
        f"👷 <b>Требуется грузчиков (чел):</b> <code>{loaders_count if loaders_count else '❌нет данных'}</code>\n"
        f"⏱️ <b>Мин. часов:</b> <code>{min_hours if min_hours else '❌нет данных'}</code>\n"
        f"📋 <b>Характер работ:</b> <code>{type_of_work[:50] if type_of_work else '❌нет данных'}...</code>\n"
        f"💰 <b>Оплата (руб/час):</b> <code>{payment if payment else 'нет данных'}</code>\n"
    )

    # Добавляем исполнителей, если они есть
    if performers:
        performers_text = '\n  • '.join(performers)
        response += f"👤 <b>Исполнители:</b>\n  • {performers_text}\n\n"
    else:
        response += f"👤 <b>Исполнители:</b> ❌нет данных\n\n"

    response += f"\n<b>Всё верно?</b>"

    await message.answer(
        response,
        reply_markup=yes_or_now_keyboard(),
        parse_mode="HTML"  # Меняем на HTML
    )

@add_data_route.callback_query(lambda c: c.data == "yes", AdminStates.getting_tasks_data)
async def got_yes(callback_query: types.CallbackQuery, state: FSMContext):

    saved_data = await state.get_data()
    try:
        new_task = find_task(saved_data['parsed_task'])
        if not new_task:
            new_task = add_task(saved_data['parsed_task'])
            logger.info(f'Задача успешно добавлена в базу (id #{new_task.id})')
            await callback_query.message.answer(f"✅Задача успешно добавлена в базу.\n\n"
                                            f"Добавляем данные в Google-таблицу...",
                                            parse_mode="Markdown"
                                            )
        else:
            await callback_query.message.answer(f"✅Задача уже существует в базе.\n\n"
                                                f"Осталось добавить данные в Google-таблицу...",
                                                parse_mode="Markdown"
                                                )
    except Exception as e:
        await callback_query.message.answer(f"❌Ошибка при добавлении задачи в базу: {e}.\n\n"
                                            f"Обратитесть к разработчикам",
                                            parse_mode="Markdown",
                                            reply_markup=return_keyboard()
                                            )
        return
    else:

        address_list = new_task.address.split(',')

        city = address_list[0]

        date_of_the_month, month_number, year = new_task.date.split('.')

        month = MONTH_NUMBERS[int(month_number)]

        try:
            result = add_data_to_tasks_google_sheet(new_task, month, int(date_of_the_month), city)
        except Exception as e:
            await callback_query.message.answer(f"❌Ошибка при обновлении google-таблицы по заявкам: {e}.\n\n"
                                                f"Обратитесть к разработчикам",
                                                parse_mode="Markdown",
                                                reply_markup=return_keyboard()
                                                )
            return
        if result:
            await callback_query.message.answer(f"✅Данные успешно добавлены в таблицу Заявки.\n",
                                                    reply_markup=return_keyboard(),
                                                    parse_mode="Markdown"
                                                    )


@add_data_route.callback_query(lambda c: c.data == "no", AdminStates.getting_tasks_data)
async def got_no(callback_query: types.CallbackQuery, state: FSMContext):

    # Получаем сохраненные данные для логирования
    saved_data = await state.get_data()
    parsed_task = saved_data.get('parsed_task', {})

    # Логируем ошибочное распознавание
    logger.warning(
        f"❌ Пользователь {callback_query.from_user.id} отклонил распознанные данные:\n"
        f"Дата: {parsed_task.get('date')}\n"
        f"Время: {parsed_task.get('time')}\n"
        f"Оплата: {parsed_task.get('payment')}\n"
        f"Текст: {parsed_task.get('type_of_work')[:50] if parsed_task.get('type_of_work') else None}..."
    )

    # Отправляем сообщение с шаблоном
    await callback_query.message.answer(
        "❌ *Данные не приняты*\n\n"
        "Пожалуйста, отправьте информацию в *правильном формате*:\n\n"
        "┌──────────────────────────────┐\n"
        "│     📋 **ШАБЛОН СООБЩЕНИЯ**    │\n"
        "└──────────────────────────────┘\n\n"
        "📅 *1. ДАТА И ВРЕМЯ:*\n"
        "`Дата 11.11.2026  к 09:00 часам`\n\n"
        "📍 *2. АДРЕС:*\n"
        "`Югорск, Столичный Сити  ул. Ленина, 2`\n\n"
        "👷 *3. ТРЕБОВАНИЯ И КОЛИЧЕСТВО:*\n"
        "`На подработку требуются в магазины \"Галамарт\" - 2 грузчика`\n"
        "   ⚠️ *ВАЖНО:* Укажите количество грузчиков через дефис (- 2 грузчика)\n\n"
        "📋 *4. ХАРАКТЕР РАБОТЫ:*\n"
        "`Характер работы: подготовить склад для разгрузки, выбросить картон, выгрузка по коробочно товар из машины перенести на склад, расформировать товар по местам хранения.`\n"
        "   ⚠️ *ВАЖНО:* Начинайте с фразы \"Характер работы:\"\n\n"
        "⏱️ *5. МИНИМАЛЬНОЕ КОЛИЧЕСТВО ЧАСОВ:*\n"
        "`( оплата от 3 ч )`\n"
        "   ⚠️ *ВАЖНО:* Укажите в скобках \"( оплата от X ч )\"\n\n"
        "💰 *6. ОПЛАТА:*\n"
        "`( оплата от 3 ч )`\n"
        "`Оплата 300 руб/час , выплата по окончанию смены`\n"
        "   ⚠️ *ВАЖНО:* Укажите \"Оплата XXX руб/час\"\n\n"
        "👤 *7. ФАМИЛИИ ГРУЗЧИКОВ:*\n"
        "`Петров Игорь`\n"
        "`Брезгин Денис`\n"
        "   ⚠️ *ВАЖНО:* Каждая фамилия с именем на новой строке\n\n"
        "──────────────────────────────\n\n"
        "📎 *СКОПИРУЙТЕ ЭТОТ ШАБЛОН:*\n\n"
        "\n"
        "Дата 11.11.2026  к 09:00 часам\n"
        "Югорск, Столичный Сити  ул. Ленина, 2\n"
        "\n"
        "На подработку требуются в магазины \"Галамарт\" - 2 грузчика\n"
        "\n"
        "Характер работы: подготовить склад для разгрузки, выбросить картон, выгрузка по коробочно товар из машины перенести на склад, расформировать товар по местам хранения.\n"
        "( оплата от 3 ч )\n"
        "Оплата 300 руб/час , выплата по окончанию смены\n"
        "\n"
        "Петров Игорь\n"
        "Брезгин Денис\n"
        "\n\n"
        "🔄 *Замените данные и отправьте сообщение*",
        parse_mode="Markdown",
        reply_markup=return_keyboard()  # Кнопка возврата в меню
    )

@add_data_route.message(AdminStates.getting_loaders_data)
async def parse_loaders_data(message: types.Message, state: FSMContext):

    text = message.text
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

    #Забираем 1 строку как комментарий
    comment = lines[0]

    # 1. Парсим дату из первой строки
    date_pattern = r'Реестр оплачен\s+(\d{2}\.\d{2}\.\d{4})'
    date_match = re.search(date_pattern, text)
    date = date_match.group(1) if date_match else None

    # 2. Парсим адрес (вторая строка)
    address = None
    if len(lines) > 1:
        # Ищем строку с адресом (содержит ул., г., Сити и т.д.)
        for line in lines[1:3]:
            if any(word in line.lower() for word in ['ул.', 'улица', 'г.', 'город', 'сити', 'пр.', 'проспект']):
                address = line
                break

    # 3. Парсим время работы
    hours_pattern = r'(\d+)\s*часа?'
    hours_match = re.search(hours_pattern, text)
    hours = int(hours_match.group(1)) if hours_match else None

    # 4. Парсим грузчиков и их выплаты
    loaders_payments = []

    # Проходим по строкам и ищем пары: ФИО -> сумма
    i = 0
    while i < len(lines):
        line = lines[i]

        # Проверяем, является ли строка фамилией и именем (русские буквы, минимум 2 слова)
        if re.match(r'^[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?$', line):
            loader_name = line
            payment_amount = None

            # Проверяем следующую строку на сумму
            if i + 1 < len(lines):
                next_line = lines[i + 1]

                # Ищем сумму в следующей строке
                payment_patterns = [
                    r'(\d+)\s*руб',  # 900 руб, 900 рублей
                    r'(\d+)\s*₽',  # 900 ₽
                    r'^(\d+)$'  # просто 900
                ]

                for pattern in payment_patterns:
                    payment_match = re.search(pattern, next_line)
                    if payment_match:
                        payment_amount = int(payment_match.group(1))
                        break

            if loader_name and payment_amount:
                loaders_payments.append({
                    'name': loader_name,
                    'payment': payment_amount
                })
                i += 2  # Пропускаем строку с суммой
            else:
                i += 1
        else:
            i += 1

    # Формируем результат
    parsed_loader_data = {
        "comment": comment,
        "date": date,
        "address": address,
        "hours": hours,
        "loaders_payments": loaders_payments,
        "raw_text": text
    }

    # Сохраняем в state
    await state.update_data(parsed_loaders=parsed_loader_data)

    # Формируем красивый ответ с эмодзи (используем HTML)
    response = (
        f"✅ <b>ДАННЫЕ О ВЫПЛАТАХ УСПЕШНО РАСПОЗНАНЫ</b>\n\n"
        f"┌─────────────────────┐\n"
        f"│   💰 РЕЗУЛЬТАТ       │\n"
        f"└─────────────────────┘\n\n"
        f"📅 <b>Дата реестра:</b> <code>{date if date else '❌нет данных'}</code>\n"
        f"📍 <b>Адрес:</b> <code>{address if address else '❌нет данных'}</code>\n"
        f"⏱️ <b>Отработано часов:</b> <code>{hours if hours else '❌нет данных'}</code>\n\n"
        f"📍 <b>Комментарий:</b> <code>{comment if comment else '❌нет данных'}</code>\n"
        f"👥 <b>Выплаты грузчикам:</b>\n"
    )

    # Добавляем информацию о каждом грузчике
    if loaders_payments:
        for idx, loader in enumerate(loaders_payments, 1):
            response += f"  {idx}. 👤 <b>{loader['name']}</b> — 💵 {loader['payment']} руб.\n"

        # Подсчитываем общую сумму
        total_payment = sum(loader['payment'] for loader in loaders_payments)
        response += f"\n💳 <b>Общая сумма выплат:</b> <code>{total_payment} руб.</code>\n"
        response += f"👷 <b>Всего грузчиков:</b> <code>{len(loaders_payments)} чел.</code>\n"
    else:
        response += f"  ❌ <b>Грузчики не найдены</b>\n\n"
        response += f"  Проверьте формат:\n"
        response += f"  • Фамилия Имя\n"
        response += f"  • Сумма (900 руб / 900 / 900₽)\n"

    response += f"\n<b>Всё верно?</b>"

    await message.answer(
        response,
        reply_markup=yes_or_now_keyboard(),
        parse_mode="HTML"  # Меняем на HTML
    )

@add_data_route.callback_query(lambda c: c.data == "yes", AdminStates.getting_loaders_data)
async def save_loaders_data(callback_query: types.CallbackQuery, state: FSMContext):
    saved_data = await state.get_data()
    parsed_loader_data = saved_data.get('parsed_loaders', {})

    try:
        new_payout = find_payout(saved_data['parsed_loaders'])
        if not new_payout:
            new_payout = add_payout(parsed_loader_data['comment'],
                                    parsed_loader_data['date'],
                                    parsed_loader_data['address'],
                                    parsed_loader_data['hours'],
                                    parsed_loader_data['loaders_payments'])
            logger.info(f'Выплата успешно добавлена в базу (id #{new_payout.id})')
            await callback_query.message.answer(f"✅Выплата успешно добавлена в базу.\n\n"
                                            f"Добавляем данные в Google-таблицу...",
                                            parse_mode="Markdown"
                                            )
        else:
            await callback_query.message.answer(f"✅Выплата уже существует в базе.\n\n"
                                                f"Осталось добавить данные в Google-таблицу...",
                                                parse_mode="Markdown"
                                                )
    except Exception as e:
        await callback_query.message.answer(f"❌Ошибка при добавлении Выплата в базу: {e}.\n\n"
                                            f"Обратитесть к разработчикам",
                                            parse_mode="Markdown",
                                            reply_markup=return_keyboard()
                                            )
        return

    try:

        date_of_the_month, month_number, year = new_payout.date.split('.')

        month = MONTH_NUMBERS[int(month_number)]

        result = add_loader_data_to_loader_google_sheet(new_payout, month, date_of_the_month)
    except Exception as e:
        await callback_query.message.answer(f"❌Ошибка при обновлении google-таблицы по грузчикам: {e}.\n\n"
                                            f"Обратитесть к разработчикам",
                                            parse_mode="Markdown",
                                            reply_markup=return_keyboard()
                                            )
        return

    if result:
        await callback_query.message.answer(f"✅Данные успешно добавлены в таблицу Грузчики.\n",
                                            reply_markup=return_keyboard(),
                                            parse_mode="Markdown"
                                            )

@add_data_route.callback_query(lambda c: c.data == "no", AdminStates.getting_loaders_data)
async def reject_loaders_data(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем сохраненные данные для логирования
    saved_data = await state.get_data()
    parsed_data = saved_data.get('parsed_loaders', {})
    # Логируем ошибочное распознавание
    logger.warning(
        f"❌ Пользователь {callback_query.from_user.id} отклонил данные о выплатах:\n"
        f"Дата: {parsed_data.get('date')}\n"
        f"Адрес: {parsed_data.get('address')}\n"
        f"Часов: {parsed_data.get('hours')}\n"
        f"Грузчиков: {len(parsed_data.get('loaders_payments', []))}"
    )

    # Отправляем сообщение с шаблоном
    await callback_query.message.answer(
        "❌ *Данные не приняты*\n\n"
        "Пожалуйста, отправьте информацию в *правильном формате*:\n\n"
        "┌──────────────────────────────┐\n"
        "│     📋 **ШАБЛОН СООБЩЕНИЯ**    │\n"
        "└──────────────────────────────┘\n\n"
        "📅 *1. ЗАГОЛОВОК И ДАТА:*\n"
        "`Реестр оплачен  09.02.2026`\n"
        "   ⚠️ *ВАЖНО:* Начинайте с фразы \"Реестр оплачен\"\n\n"
        "📍 *2. АДРЕС:*\n"
        "`Югорск, Столичный Сити  ул. Ленина, 2`\n\n"
        "👤 *3. ГРУЗЧИКИ И СУММЫ:*\n"
        "`Петров Игорь`\n"
        "`900 рублей`\n"
        "`Брезгин Денис`\n"
        "`900`\n"
        "   ⚠️ *ВАЖНО:* \n"
        "   • Каждый грузчик на отдельной строке (Фамилия Имя)\n"
        "   • Сумма выплаты на следующей строке\n"
        "   • Можно указывать: `900`, `900 руб`, `900 рублей`, `900₽`\n\n"
        "⏱️ *4. ОТРАБОТАННОЕ ВРЕМЯ:*\n"
        "`3 часа`\n"
        "   ⚠️ *ВАЖНО:* Укажите количество часов в конце сообщения\n\n"
        "──────────────────────────────\n\n"
        "📎 *СКОПИРУЙТЕ ЭТОТ ШАБЛОН:*\n\n"
        "Реестр оплачен  09.02.2026\n"
        "Югорск, Столичный Сити  ул. Ленина, 2\n"
        "\n"
        "Петров Игорь\n"
        "900 рублей\n"
        "\n"
        "Брезгин Денис\n"
        "900\n"
        "\n"
        "3 часа\n\n"
        "🔄 *Замените данные и отправьте сообщение*",
        parse_mode="Markdown",
        reply_markup=return_keyboard()
    )

