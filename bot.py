import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import json
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


BOT_TOKEN = "YOUR BOT TOKEN HERE"


BASE_URL = "http://94.72.18.202:8083"


BELLS = {
    'monday': [  
        ('8:30', '9:00'),    
        ('9:10', '10:30'),   
        ('10:40', '12:00'),  
        ('12:20', '13:40'),  
        ('13:50', '15:10'),  
        ('16:00', '17:20'),  
        ('17:30', '18:50'),  
    ],
    'other': [  
        ('8:30', '10:00'),   
        ('10:10', '11:40'),  
        ('12:10', '13:40'),  
        ('13:50', '15:20'),  
        ('15:30', '17:00'),  
        ('17:10', '18:40'),  
    ]
}


WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


MAIN_ADMIN_ID = "YOUR TG ID"  


class AdminStates(StatesGroup):
    waiting_for_announcement = State()
    waiting_for_announcement_photo = State()
    announcement_confirmation = State()
    waiting_for_new_admin = State()  


USERS_FILE = 'users.json'
CACHE_FILE = 'schedule_cache.json'
ADMINS_FILE = 'admins.json'
GROUPS_FILE = 'groups_cache.json'
TEACHERS_FILE = 'teachers_cache.json'
FAVORITES_FILE = 'favorites.json'


def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_update": None, "teachers": {}, "groups": {}}

def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    admins = [MAIN_ADMIN_ID]
    save_admins(admins)
    return admins

def save_admins(admins):
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

def load_groups_cache():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_update": None, "groups": []}

def save_groups_cache(groups_data):
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups_data, f, ensure_ascii=False, indent=2)

def load_teachers_cache():
    if os.path.exists(TEACHERS_FILE):
        with open(TEACHERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

            if "teachers" in data:
                filtered_teachers = [
                    teacher for teacher in data["teachers"] 
                    if teacher.get('name', '') not in ['Ваканс', 'Вакансия', 'ваканс', 'вакансия', 'ВАКАНСИЯ']
                ]
                data["teachers"] = filtered_teachers
            return data
    return {"last_update": None, "teachers": []}

def save_teachers_cache(teachers_data):
    with open(TEACHERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(teachers_data, f, ensure_ascii=False, indent=2)

def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_favorites(favorites):
    with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def create_groups_keyboard(groups: List[Dict], page: int, groups_per_page: int = 30, 
                          show_favorites: bool = False, user_id: str = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с группами в 3 колонки"""
    start_idx = page * groups_per_page
    end_idx = start_idx + groups_per_page
    page_groups = groups[start_idx:end_idx]
    
    keyboard_buttons = []
    row = []
    
    for i, group in enumerate(page_groups):
        group_name = group.get('name', 'Без названия')
        

        is_favorite = False
        if user_id and show_favorites:
            favorites = load_favorites()
            if user_id in favorites and group_name in favorites[user_id].get('groups', []):
                is_favorite = True
        

        emoji = "⭐" if is_favorite else "👥"
        button = InlineKeyboardButton(
            text=f"{emoji} {group_name}",
            callback_data=f"group:{group_name}"
        )
        row.append(button)
        

        if (i + 1) % 3 == 0:
            keyboard_buttons.append(row)
            row = []
    

    if row:
        keyboard_buttons.append(row)
    

    total_pages = (len(groups) + groups_per_page - 1) // groups_per_page
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"groups_page:{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"groups_page:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    

    action_buttons = []
    if show_favorites:
        action_buttons.append(InlineKeyboardButton(text="➕ Все группы", callback_data="groups"))
    else:
        action_buttons.append(InlineKeyboardButton(text="⭐ Избранное", callback_data="favorite_groups"))
    
    action_buttons.append(InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_groups"))
    
    keyboard_buttons.append(action_buttons)
    

    keyboard_buttons.append([
        InlineKeyboardButton(text="🏠 Главная", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def create_teachers_keyboard(teachers: List[Dict], page: int, teachers_per_page: int = 30,
                           show_favorites: bool = False, user_id: str = None) -> InlineKeyboardMarkup:
    """Создает клавиатуру с преподавателями в 3 колонки"""
    start_idx = page * teachers_per_page
    end_idx = start_idx + teachers_per_page
    page_teachers = teachers[start_idx:end_idx]
    
    keyboard_buttons = []
    row = []
    
    for i, teacher in enumerate(page_teachers):
        teacher_name = teacher.get('name', 'Без имени')
        

        is_favorite = False
        if user_id and show_favorites:
            favorites = load_favorites()
            if user_id in favorites and teacher_name in favorites[user_id].get('teachers', []):
                is_favorite = True
        
        emoji = "⭐" if is_favorite else "👨‍🏫"
        button = InlineKeyboardButton(
            text=f"{emoji} {teacher_name}",
            callback_data=f"teacher:{teacher_name}"
        )
        row.append(button)
        
        if (i + 1) % 3 == 0:
            keyboard_buttons.append(row)
            row = []
    
    if row:
        keyboard_buttons.append(row)
    
    total_pages = (len(teachers) + teachers_per_page - 1) // teachers_per_page
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"teachers_page:{page-1}"))
    
    if total_pages > 1:
        nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"teachers_page:{page+1}"))
    
    if nav_buttons:
        keyboard_buttons.append(nav_buttons)
    
    action_buttons = []
    if show_favorites:
        action_buttons.append(InlineKeyboardButton(text="➕ Все преподаватели", callback_data="teachers"))
    else:
        action_buttons.append(InlineKeyboardButton(text="⭐ Избранное", callback_data="favorite_teachers"))
    
    action_buttons.append(InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_teachers"))
    
    keyboard_buttons.append(action_buttons)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="🏠 Главная", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_lesson_time(lesson_num: int, is_monday: bool = False) -> tuple:
    """Возвращает время начала и конца пары по номеру пары"""
    if is_monday:
        bells = BELLS['monday']
    else:
        bells = BELLS['other']
    
    if 1 <= lesson_num <= len(bells):
        return bells[lesson_num - 1]
    return ("??:??", "??:??")


async def parse_group_schedule_simple(html: str, group_name: str) -> Dict[str, Any]:
    """Правильный парсинг расписания группы"""
    soup = BeautifulSoup(html, 'html.parser')
    

    title_tag = soup.find('h1')
    title = title_tag.text.strip() if title_tag else f"Группа: {group_name}"
    

    schedule_table = soup.find('table', class_='inf')
    if not schedule_table:
        return {"error": "Не найдена таблица расписания"}
    

    update_div = soup.find('div', class_='ref')
    last_update = update_div.text.strip() if update_div else None
    
    schedule_data = {
        'title': title,
        'group': group_name,
        'days': [],
        'last_update': last_update
    }
    
 
    day_rows = schedule_table.find_all('tr')
    
    current_day_index = -1
    
    for row in day_rows:

        day_cell = row.find('td', class_='hd')
        
        if day_cell and 'rowspan' in day_cell.attrs:

            current_day_index += 1
            

            day_text = day_cell.get_text(strip=True, separator='\n')
            lines = [line.strip() for line in day_text.split('\n') if line.strip()]
            
            if len(lines) >= 2:

                day_short_name = lines[1]

                day_name = get_full_day_name(day_short_name)
            else:
                day_name = WEEKDAYS[current_day_index] if current_day_index < len(WEEKDAYS) else f"День {current_day_index+1}"
            

            day_data = {
                'weekday': day_name,
                'weekday_idx': current_day_index,
                'lessons': []
            }
            schedule_data['days'].append(day_data)
            
            process_day_lessons(row, day_data, current_day_index)
        elif current_day_index >= 0:

            process_day_lessons(row, schedule_data['days'][-1], current_day_index)
    

    schedule_data['days'] = [day for day in schedule_data['days'] if day['lessons']]
    
    return schedule_data

def get_full_day_name(short_name: str) -> str:
    """Преобразует короткое название дня недели в полное"""
    day_mapping = {
        'пн': 'Понедельник',
        'вт': 'Вторник',
        'ср': 'Среда',
        'чт': 'Четверг',
        'пт': 'Пятница',
        'сб': 'Суббота',
        'вс': 'Воскресенье',
        'Пн': 'Понедельник',
        'Вт': 'Вторник',
        'Ср': 'Среда',
        'Чт': 'Четверг',
        'Пт': 'Пятница',
        'Сб': 'Суббота',
        'Вс': 'Воскресенье'
    }
    
    short_name_lower = short_name.lower()
    for short, full in day_mapping.items():
        if short_name_lower.startswith(short.lower()):
            return full
    
    return short_name

def process_day_lessons(row, day_data, day_index):
    """Обрабатывает пары в строке для конкретного дня"""
    hd_cells = row.find_all('td', class_='hd')
    if not hd_cells:
        return

    # Берём ячейку номера пары: td.hd без rowspan (rowspan обычно у ячейки дня)
    lesson_num_cell = next((c for c in hd_cells if 'rowspan' not in c.attrs), None)
    if lesson_num_cell is None:
        return

    lesson_num_text = lesson_num_cell.get_text(strip=True)
    lesson_num_match = re.search(r'(\d+)', lesson_num_text)
    lesson_num = int(lesson_num_match.group(1)) if lesson_num_match else 0

    lesson_cell = row.find('td', class_='ur')
    if not lesson_cell:
        return

    cell_text = lesson_cell.get_text(strip=True)
    if not cell_text or cell_text in ['&nbsp;', ' ', '']:
        return

    subject = ''
    teacher = ''
    room = ''

    subject_link = lesson_cell.find('a', class_='z1')
    room_link = lesson_cell.find('a', class_='z2')
    teacher_link = lesson_cell.find('a', class_='z3')

    if subject_link:
        subject = subject_link.get_text(strip=True)
    if room_link:
        room = room_link.get_text(strip=True)
    if teacher_link:
        teacher = teacher_link.get_text(strip=True)
    

    if not subject:
        all_text = lesson_cell.get_text(strip=True, separator='\n')
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        if lines:
            subject = lines[0]
            if len(lines) > 1:
                teacher = lines[-1]
    
    if subject:

        is_monday = (day_index == 0)  
        time_start, time_end = get_lesson_time(lesson_num, is_monday)
        
        day_data['lessons'].append({
            'number': lesson_num,
            'subject': subject,
            'teacher': teacher,
            'room': room,
            'time_start': time_start,
            'time_end': time_end
        })


async def parse_teacher_schedule_simple(html: str, teacher_name: str) -> Dict[str, Any]:
    """Правильный парсинг расписания преподавателя"""
    soup = BeautifulSoup(html, 'html.parser')
    
    title_tag = soup.find('h1')
    title = title_tag.text.strip() if title_tag else f"Преподаватель: {teacher_name}"
    
    schedule_table = soup.find('table', class_='inf')
    if not schedule_table:
        return {"error": "Не найдена таблица расписания"}
    
    update_div = soup.find('div', class_='ref')
    last_update = update_div.text.strip() if update_div else None
    
    schedule_data = {
        'title': title,
        'teacher': teacher_name,
        'days': [],
        'last_update': last_update
    }
    

    day_rows = schedule_table.find_all('tr')
    
    current_day_index = -1
    
    for row in day_rows:

        day_cell = row.find('td', class_='hd')
        
        if day_cell and 'rowspan' in day_cell.attrs:

            current_day_index += 1
            

            day_text = day_cell.get_text(strip=True, separator='\n')
            lines = [line.strip() for line in day_text.split('\n') if line.strip()]
            
            if len(lines) >= 2:

                day_short_name = lines[1]
                day_name = get_full_day_name(day_short_name)
            else:
                day_name = WEEKDAYS[current_day_index] if current_day_index < len(WEEKDAYS) else f"День {current_day_index+1}"
            

            day_data = {
                'weekday': day_name,
                'weekday_idx': current_day_index,
                'lessons': []
            }
            schedule_data['days'].append(day_data)
            

            process_teacher_day_lessons(row, day_data, current_day_index)
        elif current_day_index >= 0:

            process_teacher_day_lessons(row, schedule_data['days'][-1], current_day_index)
    

    schedule_data['days'] = [day for day in schedule_data['days'] if day['lessons']]
    
    return schedule_data

def process_teacher_day_lessons(row, day_data, day_index):
    """Обрабатывает пары в строке для конкретного дня преподавателя"""

    lesson_num_cell = row.find('td', class_='hd')
    if not lesson_num_cell or 'rowspan' in lesson_num_cell.attrs:
        return  
    
    lesson_num_text = lesson_num_cell.get_text(strip=True)
    lesson_num_match = re.search(r'(\d+)', lesson_num_text)
    lesson_num = int(lesson_num_match.group(1)) if lesson_num_match else 0
    

    lesson_cell = row.find('td', class_='ur')
    if not lesson_cell:
        return  
    
    cell_text = lesson_cell.get_text(strip=True)
    if not cell_text or cell_text in ['&nbsp;', ' ', '']:
        return  
    

    groups = []
    subject = ''
    room = ''
    

    groups_links = lesson_cell.find_all('a', class_='z1')
    room_link = lesson_cell.find('a', class_='z2')
    subject_link = lesson_cell.find('a', class_='z3')
    
    groups = [link.get_text(strip=True) for link in groups_links]
    if room_link:
        room = room_link.get_text(strip=True)
    if subject_link:
        subject = subject_link.get_text(strip=True)
    

    if not subject:
        all_text = lesson_cell.get_text(strip=True, separator='\n')
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        if lines:
            subject = lines[-1] if lines else ''
            if not groups and len(lines) > 1:
                groups = lines[:-1]
    
    if subject:

        is_monday = (day_index == 0)
        time_start, time_end = get_lesson_time(lesson_num, is_monday)
        
        day_data['lessons'].append({
            'number': lesson_num,
            'groups': groups,
            'subject': subject,
            'room': room,
            'time_start': time_start,
            'time_end': time_end
        })


def format_group_schedule(schedule_data: Dict) -> str:
    """Форматирует расписание группы в красивый текст"""
    if 'error' in schedule_data:
        return f"❌ {schedule_data['error']}"
    
    group_name = schedule_data.get('group', 'Неизвестная группа')
    title = schedule_data.get('title', '')
    

    result = f"📅 <b>{title}</b>\n"
    result += "―" * 40 + "\n\n"
    
    days = schedule_data.get('days', [])
    
    if not days:
        result += "📭 <i>На этой неделе пар нет</i>\n\n"
    else:

        week_days = []
        for i in range(7):
            day_found = next((day for day in days if day.get('weekday_idx') == i), None)
            if day_found:
                week_days.append(day_found)
            else:

                week_days.append({
                    'weekday': WEEKDAYS[i],
                    'weekday_idx': i,
                    'lessons': []
                })
        

        for day in week_days:
            weekday = day.get('weekday', 'Неизвестный день')
            lessons = day.get('lessons', [])
            

            result += f"📌 <b>{weekday.upper()}</b>\n"
            result += "―" * 35 + "\n"
            
            if not lessons:
                result += "│ <i>Пар нет</i>\n"
                result += "―" * 35 + "\n\n"
                continue
                

            for lesson in lessons:
                lesson_num = lesson.get('number', '?')
                subject = lesson.get('subject', 'Нет предмета').strip()
                teacher = lesson.get('teacher', '').strip()
                room = lesson.get('room', '').strip()
                time_start = lesson.get('time_start', '??:??')
                time_end = lesson.get('time_end', '??:??')
                

                result += f"<b>│ {lesson_num} пара</b> │ {time_start}-{time_end}\n"
                result += f"<b>│ 📚</b> {subject}\n"
                
                if teacher:
                    result += f"<b>│ 👨‍🏫</b> {teacher}\n"
                
                if room:
                    result += f"<b>│ 🏢</b> {room}\n"
                
                result += "―" * 35 + "\n"
            
            result += "\n"
    

    last_update = schedule_data.get('last_update')
    if last_update:
        result += f"\n🔄 <i>{last_update}</i>"
    else:
        result += f"\n🔄 <i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
    

    if len(result) > 4000:
        result = result[:3900] + "\n\n... (сообщение обрезано)"
    
    return result


def format_teacher_schedule(schedule_data: Dict) -> str:
    """Форматирует расписание преподавателя в красивый текст"""
    if 'error' in schedule_data:
        return f"❌ {schedule_data['error']}"
    
    teacher_name = schedule_data.get('teacher', 'Неизвестный преподаватель')
    title = schedule_data.get('title', '')
    
    result = f"👨‍🏫 <b>{title}</b>\n"
    result += "―" * 40 + "\n\n"
    
    days = schedule_data.get('days', [])
    
    if not days:
        result += "📭 <i>На этой неделе пар нет</i>\n\n"
    else:

        week_days = []
        for i in range(7):
            day_found = next((day for day in days if day.get('weekday_idx') == i), None)
            if day_found:
                week_days.append(day_found)
            else:

                week_days.append({
                    'weekday': WEEKDAYS[i],
                    'weekday_idx': i,
                    'lessons': []
                })
        

        for day in week_days:
            weekday = day.get('weekday', 'Неизвестный день')
            lessons = day.get('lessons', [])
            
            if not lessons:
                continue
                    
            result += f"📌 <b>{weekday.upper()}</b>\n"
            result += "―" * 35 + "\n"
            
            for lesson in lessons:
                lesson_num = lesson.get('number', '?')
                groups = lesson.get('groups', [])
                subject = lesson.get('subject', 'Нет предмета').strip()
                room = lesson.get('room', '').strip()
                time_start = lesson.get('time_start', '??:??')
                time_end = lesson.get('time_end', '??:??')
                
                result += f"<b>│ {lesson_num} пара</b> │ {time_start}-{time_end}\n"
                result += f"<b>│ 📚</b> {subject}\n"
                
                if groups:
                    groups_text = ", ".join([g for g in groups if g.strip()])
                    if groups_text:
                        result += f"<b>│ 👥</b> {groups_text}\n"
                
                if room:
                    result += f"<b>│ 🏢</b> {room}\n"
                
                result += "―" * 35 + "\n"
            
            result += "\n"
    
    last_update = schedule_data.get('last_update')
    if last_update:
        result += f"\n🔄 <i>{last_update}</i>"
    else:
        result += f"\n🔄 <i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
    
    if len(result) > 4000:
        result = result[:3900] + "\n\n... (сообщение обрезано)"
    
    return result


async def fetch_group_schedule(group_name: str, group_filename: str) -> Dict:
    """Получает и парсит расписание группы"""
    try:
        schedule_url = f"{BASE_URL}/{group_filename}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Connection': 'keep-alive',
            }
            
            async with session.get(schedule_url, timeout=15, headers=headers) as response:
                if response.status == 200:

                    try:
                        html = await response.text(encoding='windows-1251')
                    except:
                        try:
                            html = await response.text(encoding='cp1251')
                        except:
                            html = await response.text()
                    
                    logger.info(f"Загружено расписание для группы {group_name}")
                    return await parse_group_schedule_simple(html, group_name)
                else:
                    logger.error(f"Ошибка HTTP {response.status} для {schedule_url}")
                    return {"error": f"Ошибка при загрузке страницы: {response.status}"}
    except asyncio.TimeoutError:
        logger.error(f"Таймаут при загрузке расписания группы {group_name}")
        return {"error": "Таймаут при загрузке. Сайт может быть недоступен."}
    except Exception as e:
        logger.error(f"Ошибка при получении расписания группы {group_name}: {e}")
        return {"error": f"Ошибка при загрузке расписания: {str(e)[:200]}"}


async def fetch_teacher_schedule(teacher_name: str, teacher_filename: str) -> Dict:
    """Получает и парсит расписание преподавателя"""
    try:
        schedule_url = f"{BASE_URL}/{teacher_filename}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Connection': 'keep-alive',
            }
            
            async with session.get(schedule_url, timeout=15, headers=headers) as response:
                if response.status == 200:
                    try:
                        html = await response.text(encoding='windows-1251')
                    except:
                        try:
                            html = await response.text(encoding='cp1251')
                        except:
                            html = await response.text()
                    
                    logger.info(f"Загружено расписание для преподавателя {teacher_name}")
                    return await parse_teacher_schedule_simple(html, teacher_name)
                else:
                    return {"error": f"Ошибка при загрузке страницы: {response.status}"}
    except Exception as e:
        logger.error(f"Ошибка при получении расписания преподавателя {teacher_name}: {e}")
        return {"error": f"Ошибка при загрузке расписания: {str(e)[:200]}"}


async def fetch_groups_list():
    """Получает список всех групп с сайта"""
    try:
        url = f"{BASE_URL}/cg.htm"
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Connection': 'keep-alive',
            }
            
            async with session.get(url, timeout=10, headers=headers) as response:
                if response.status == 200:
                    try:
                        html = await response.text(encoding='windows-1251')
                    except:
                        html = await response.text()
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    groups = []
                    table = soup.find('table', class_='inf')
                    
                    if table:
                        rows = table.find_all('tr')[1:]
                        for row in rows:
                            link = row.find('a', class_='z0')
                            if link:
                                group_name = link.text.strip()
                                group_url = link.get('href', '')
                                filename = group_url if group_url.startswith('http') else group_url.split('/')[-1] if '/' in group_url else group_url
                                
                                groups.append({
                                    'name': group_name,
                                    'url': group_url,
                                    'filename': filename
                                })
                    
                    save_groups_cache({
                        "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "groups": groups
                    })
                    
                    logger.info(f"Загружено {len(groups)} групп")
                    return groups
                else:
                    logger.error(f"Ошибка HTTP при получении групп: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Ошибка при получении списка групп: {e}")
        return []


async def fetch_teachers_list():
    """Получает список всех преподавателей с сайта"""
    try:
        url = f"{BASE_URL}/cp.htm"
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Connection': 'keep-alive',
            }
            
            async with session.get(url, timeout=10, headers=headers) as response:
                if response.status == 200:
                    try:
                        html = await response.text(encoding='windows-1251')
                    except:
                        html = await response.text()
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    teachers = []
                    table = soup.find('table', class_='inf')
                    
                    if table:
                        rows = table.find_all('tr')[1:]
                        for row in rows:
                            link = row.find('a', class_='z0')
                            if link:
                                teacher_name = link.text.strip()
                                if teacher_name.lower() in ['ваканс', 'вакансия']:
                                    continue
                                    
                                teacher_url = link.get('href', '')
                                filename = teacher_url if teacher_url.startswith('http') else teacher_url.split('/')[-1] if '/' in teacher_url else teacher_url
                                
                                teachers.append({
                                    'name': teacher_name,
                                    'url': teacher_url,
                                    'filename': filename
                                })
                    
                    save_teachers_cache({
                        "last_update": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "teachers": teachers
                    })
                    
                    logger.info(f"Загружено {len(teachers)} преподавателей")
                    return teachers
                else:
                    logger.error(f"Ошибка HTTP при получении преподавателей: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Ошибка при получении списка преподавателей: {e}")
        return []


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id not in users:
        users.append(user_id)
        save_users(users)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Группы", callback_data="groups"),
            InlineKeyboardButton(text="👨‍🏫 Преподаватели", callback_data="teachers")
        ],
        [
            InlineKeyboardButton(text="🔔 Звонки", callback_data="bells"),
            InlineKeyboardButton(text="⭐ Избранное", callback_data="favorites_menu")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_info"),
            InlineKeyboardButton(text="📱 О боте", callback_data="about_bot")
        ]
    ])
    
    await message.answer(
        "👋 <b>Добро пожаловать в бот расписания колледжа!</b>\n\n"
        "Здесь вы можете посмотреть актуальное расписание занятий.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "bells")
async def show_bells(callback: types.CallbackQuery):
    bells_text = "🔔 <b>РАСПИСАНИЕ ЗВОНКОВ</b>\n" + "―" * 40 + "\n\n"
    
    bells_text += "📅 <b>ПОНЕДЕЛЬНИК (короткий день)</b>\n"
    for i, (start, end) in enumerate(BELLS['monday'], 1):
        bells_text += f"{i}. {start} — {end}\n"
    bells_text += "• 15:20 — 15:50 — <i>Кураторский час</i>\n"
    bells_text += "―" * 30 + "\n\n"
    
    bells_text += "📅 <b>ВТОРНИК - СУББОТА</b>\n"
    for i, (start, end) in enumerate(BELLS['other'], 1):
        bells_text += f"{i}. {start} — {end}\n"
    bells_text += "―" * 30 + "\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(bells_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "groups")
async def show_groups(callback: types.CallbackQuery):
    await callback.message.edit_text("📚 <b>Загружаем список групп...</b>", parse_mode="HTML")
    
    groups_cache = load_groups_cache()
    groups = groups_cache.get("groups", [])
    last_update = groups_cache.get("last_update", "никогда")
    
    if not groups:
        groups = await fetch_groups_list()
        groups_cache = load_groups_cache()
        last_update = groups_cache.get("last_update", "только что")
    
    if not groups:
        await callback.message.edit_text(
            "❌ <b>Не удалось загрузить список групп.</b>\nПопробуйте позже.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="groups")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    page = 0
    keyboard = create_groups_keyboard(groups, page, user_id=str(callback.from_user.id))
    
    await callback.message.edit_text(
        f"👥 <b>ВЫБЕРИТЕ ГРУППУ</b>\n\n"
        f"📊 Всего групп: <b>{len(groups)}</b>\n"
        f"🔄 Обновлено: <i>{last_update}</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("groups_page:"))
async def groups_page_navigation(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    
    groups_cache = load_groups_cache()
    groups = groups_cache.get("groups", [])
    last_update = groups_cache.get("last_update", "никогда")
    
    keyboard = create_groups_keyboard(groups, page, user_id=str(callback.from_user.id))
    
    await callback.message.edit_text(
        f"👥 <b>ВЫБЕРИТЕ ГРУППУ</b>\n\n"
        f"📊 Всего групп: <b>{len(groups)}</b>\n"
        f"🔄 Обновлено: <i>{last_update}</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("group:"))
async def show_group_schedule(callback: types.CallbackQuery):
    group_name = callback.data.split(":", 1)[1]
    
    await callback.message.edit_text(f"⏳ <b>Загружаем расписание для группы {group_name}...</b>", parse_mode="HTML")
    
    cache = load_cache()
    cache_key = f"group_{group_name}"
    
    if cache_key in cache["groups"]:
        schedule_text = cache["groups"][cache_key]
        
        favorites = load_favorites()
        user_id = str(callback.from_user.id)
        is_favorite = user_id in favorites and group_name in favorites[user_id].get('groups', [])
        
        favorite_emoji = "⭐" if is_favorite else "☆"
        favorite_text = "Удалить из избранного" if is_favorite else "Добавить в избранное"
        favorite_callback = f"remove_favorite_group:{group_name}" if is_favorite else f"add_favorite_group:{group_name}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{favorite_emoji} {favorite_text}", callback_data=favorite_callback)],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_group:{group_name}")],
            [
                InlineKeyboardButton(text="👥 К списку групп", callback_data="groups"),
                InlineKeyboardButton(text="🏠 В главное", callback_data="back_to_main")
            ]
        ])
        
        await callback.message.edit_text(schedule_text, parse_mode="HTML", reply_markup=keyboard)
    else:
        groups_cache = load_groups_cache()
        group_data = None
        
        for group in groups_cache.get("groups", []):
            if group.get('name') == group_name:
                group_data = group
                break
        
        if not group_data:
            await callback.message.edit_text(
                f"❌ <b>Группа {group_name} не найдена.</b>\n"
                f"Попробуйте обновить список групп.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_groups")],
                    [InlineKeyboardButton(text="👥 К списку групп", callback_data="groups")]
                ])
            )
            return
        
        await callback.message.edit_text(f"⏳ <b>Парсим расписание для группы {group_name}...</b>", parse_mode="HTML")
        
        schedule_data = await fetch_group_schedule(group_name, group_data.get('filename'))
        
        if 'error' in schedule_data:
            await callback.message.edit_text(
                f"❌ <b>Ошибка:</b> {schedule_data['error']}\n\n"
                f"Попробуйте позже или обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data=f"group:{group_name}")],
                    [InlineKeyboardButton(text="👥 К списку групп", callback_data="groups")]
                ])
            )
            return
        
        schedule_text = format_group_schedule(schedule_data)
        
        cache["groups"][cache_key] = schedule_text
        cache["last_update"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_cache(cache)
        
        favorites = load_favorites()
        user_id = str(callback.from_user.id)
        is_favorite = user_id in favorites and group_name in favorites[user_id].get('groups', [])
        
        favorite_emoji = "⭐" if is_favorite else "☆"
        favorite_text = "Удалить из избранного" if is_favorite else "Добавить в избранное"
        favorite_callback = f"remove_favorite_group:{group_name}" if is_favorite else f"add_favorite_group:{group_name}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{favorite_emoji} {favorite_text}", callback_data=favorite_callback)],
            [
                InlineKeyboardButton(text="👥 К списку групп", callback_data="groups"),
                InlineKeyboardButton(text="🏠 В главное", callback_data="back_to_main")
            ]
        ])
        
        await callback.message.edit_text(schedule_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "teachers")
async def show_teachers(callback: types.CallbackQuery):
    await callback.message.edit_text("👨‍🏫 <b>Загружаем список преподавателей...</b>", parse_mode="HTML")
    
    teachers_cache = load_teachers_cache()
    teachers = teachers_cache.get("teachers", [])
    last_update = teachers_cache.get("last_update", "никогда")
    
    if not teachers:
        teachers = await fetch_teachers_list()
        teachers_cache = load_teachers_cache()
        last_update = teachers_cache.get("last_update", "только что")
    
    if not teachers:
        await callback.message.edit_text(
            "❌ <b>Не удалось загрузить список преподавателей.</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="teachers")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    page = 0
    keyboard = create_teachers_keyboard(teachers, page, user_id=str(callback.from_user.id))
    
    await callback.message.edit_text(
        f"👨‍🏫 <b>ВЫБЕРИТЕ ПРЕПОДАВАТЕЛЯ</b>\n\n"
        f"📊 Всего преподавателей: <b>{len(teachers)}</b>\n"
        f"🔄 Обновлено: <i>{last_update}</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("teachers_page:"))
async def teachers_page_navigation(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    
    teachers_cache = load_teachers_cache()
    teachers = teachers_cache.get("teachers", [])
    last_update = teachers_cache.get("last_update", "никогда")
    
    keyboard = create_teachers_keyboard(teachers, page, user_id=str(callback.from_user.id))
    
    await callback.message.edit_text(
        f"👨‍🏫 <b>ВЫБЕРИТЕ ПРЕПОДАВАТЕЛЯ</b>\n\n"
        f"📊 Всего преподавателей: <b>{len(teachers)}</b>\n"
        f"🔄 Обновлено: <i>{last_update}</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("teacher:"))
async def show_teacher_schedule(callback: types.CallbackQuery):
    teacher_name = callback.data.split(":", 1)[1]
    
    await callback.message.edit_text(f"⏳ <b>Загружаем расписание для {teacher_name}...</b>", parse_mode="HTML")
    
    cache = load_cache()
    cache_key = f"teacher_{teacher_name}"
    
    if cache_key in cache["teachers"]:
        schedule_text = cache["teachers"][cache_key]
        
        favorites = load_favorites()
        user_id = str(callback.from_user.id)
        is_favorite = user_id in favorites and teacher_name in favorites[user_id].get('teachers', [])
        
        favorite_emoji = "⭐" if is_favorite else "☆"
        favorite_text = "Удалить из избранного" if is_favorite else "Добавить в избранное"
        favorite_callback = f"remove_favorite_teacher:{teacher_name}" if is_favorite else f"add_favorite_teacher:{teacher_name}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{favorite_emoji} {favorite_text}", callback_data=favorite_callback)],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data=f"refresh_teacher:{teacher_name}")],
            [
                InlineKeyboardButton(text="👨‍🏫 К списку преподавателей", callback_data="teachers"),
                InlineKeyboardButton(text="🏠 В главное", callback_data="back_to_main")
            ]
        ])
        
        await callback.message.edit_text(schedule_text, parse_mode="HTML", reply_markup=keyboard)
    else:
        teachers_cache = load_teachers_cache()
        teacher_data = None
        
        for teacher in teachers_cache.get("teachers", []):
            if teacher.get('name') == teacher_name:
                teacher_data = teacher
                break
        
        if not teacher_data:
            await callback.message.edit_text(
                f"❌ <b>Преподаватель {teacher_name} не найден.</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Обновить список", callback_data="refresh_teachers")],
                    [InlineKeyboardButton(text="👨‍🏫 К списку преподавателей", callback_data="teachers")]
                ])
            )
            return
        
        schedule_data = await fetch_teacher_schedule(teacher_name, teacher_data.get('filename'))
        schedule_text = format_teacher_schedule(schedule_data)
        
        cache["teachers"][cache_key] = schedule_text
        cache["last_update"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        save_cache(cache)
        
        favorites = load_favorites()
        user_id = str(callback.from_user.id)
        is_favorite = user_id in favorites and teacher_name in favorites[user_id].get('teachers', [])
        
        favorite_emoji = "⭐" if is_favorite else "☆"
        favorite_text = "Удалить из избранного" if is_favorite else "Добавить в избранное"
        favorite_callback = f"remove_favorite_teacher:{teacher_name}" if is_favorite else f"add_favorite_teacher:{teacher_name}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{favorite_emoji} {favorite_text}", callback_data=favorite_callback)],
            [
                InlineKeyboardButton(text="👨‍🏫 К списку преподавателей", callback_data="teachers"),
                InlineKeyboardButton(text="🏠 В главное", callback_data="back_to_main")
            ]
        ])
        
        await callback.message.edit_text(schedule_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("add_favorite_group:"))
async def add_favorite_group(callback: types.CallbackQuery):
    group_name = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    
    favorites = load_favorites()
    if user_id not in favorites:
        favorites[user_id] = {"groups": [], "teachers": []}
    
    if group_name not in favorites[user_id]["groups"]:
        favorites[user_id]["groups"].append(group_name)
        save_favorites(favorites)
    
    await show_group_schedule(callback)


@dp.callback_query(F.data.startswith("remove_favorite_group:"))
async def remove_favorite_group(callback: types.CallbackQuery):
    group_name = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    
    favorites = load_favorites()
    if user_id in favorites and group_name in favorites[user_id]["groups"]:
        favorites[user_id]["groups"].remove(group_name)
        save_favorites(favorites)
    
    await show_group_schedule(callback)


@dp.callback_query(F.data.startswith("add_favorite_teacher:"))
async def add_favorite_teacher(callback: types.CallbackQuery):
    teacher_name = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    
    favorites = load_favorites()
    if user_id not in favorites:
        favorites[user_id] = {"groups": [], "teachers": []}
    
    if teacher_name not in favorites[user_id]["teachers"]:
        favorites[user_id]["teachers"].append(teacher_name)
        save_favorites(favorites)
    
    await show_teacher_schedule(callback)


@dp.callback_query(F.data.startswith("remove_favorite_teacher:"))
async def remove_favorite_teacher(callback: types.CallbackQuery):
    teacher_name = callback.data.split(":")[1]
    user_id = str(callback.from_user.id)
    
    favorites = load_favorites()
    if user_id in favorites and teacher_name in favorites[user_id]["teachers"]:
        favorites[user_id]["teachers"].remove(teacher_name)
        save_favorites(favorites)
    
    await show_teacher_schedule(callback)


@dp.callback_query(F.data == "favorites_menu")
async def show_favorites_menu(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    favorites = load_favorites()
    
    user_favorites = favorites.get(user_id, {"groups": [], "teachers": []})
    groups_count = len(user_favorites.get("groups", []))
    teachers_count = len(user_favorites.get("teachers", []))
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Группы ({groups_count})", callback_data="favorite_groups")],
        [InlineKeyboardButton(text=f"⭐ Преподаватели ({teachers_count})", callback_data="favorite_teachers")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(
        "⭐ <b>ИЗБРАННОЕ</b>\n\n"
        f"📊 <b>Групп:</b> {groups_count}\n"
        f"👨‍🏫 <b>Преподавателей:</b> {teachers_count}\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "favorite_groups")
async def show_favorite_groups(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    favorites = load_favorites()
    
    favorite_groups_names = favorites.get(user_id, {}).get("groups", [])
    
    if not favorite_groups_names:
        await callback.message.edit_text(
            "⭐ <b>ИЗБРАННЫЕ ГРУППЫ</b>\n\n"
            "📭 У вас нет избранных групп.\n\n"
            "Чтобы добавить группу в избранное, откройте её расписание и нажмите кнопку «Добавить в избранное».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Все группы", callback_data="groups")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    groups_cache = load_groups_cache()
    all_groups = groups_cache.get("groups", [])
    favorite_groups = []
    
    for group in all_groups:
        if group.get('name') in favorite_groups_names:
            favorite_groups.append(group)
    
    page = 0
    keyboard = create_groups_keyboard(favorite_groups, page, show_favorites=True, user_id=user_id)
    
    await callback.message.edit_text(
        f"⭐ <b>ИЗБРАННЫЕ ГРУППЫ</b>\n\n"
        f"📊 Всего: <b>{len(favorite_groups)}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "favorite_teachers")
async def show_favorite_teachers(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    favorites = load_favorites()
    
    favorite_teachers_names = favorites.get(user_id, {}).get("teachers", [])
    
    if not favorite_teachers_names:
        await callback.message.edit_text(
            "⭐ <b>ИЗБРАННЫЕ ПРЕПОДАВАТЕЛИ</b>\n\n"
            "📭 У вас нет избранных преподавателей.\n\n"
            "Чтобы добавить преподавателя в избранное, откройте его расписание и нажмите кнопку «Добавить в избранное».",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨‍🏫 Все преподаватели", callback_data="teachers")],
                [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
            ])
        )
        return
    
    teachers_cache = load_teachers_cache()
    all_teachers = teachers_cache.get("teachers", [])
    favorite_teachers = []
    
    for teacher in all_teachers:
        if teacher.get('name') in favorite_teachers_names:
            favorite_teachers.append(teacher)
    
    page = 0
    keyboard = create_teachers_keyboard(favorite_teachers, page, show_favorites=True, user_id=user_id)
    
    await callback.message.edit_text(
        f"⭐ <b>ИЗБРАННЫЕ ПРЕПОДАВАТЕЛИ</b>\n\n"
        f"📊 Всего: <b>{len(favorite_teachers)}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "refresh_groups")
async def refresh_groups_list(callback: types.CallbackQuery):
    await show_groups(callback)


@dp.callback_query(F.data == "refresh_teachers")
async def refresh_teachers_list(callback: types.CallbackQuery):
    await show_teachers(callback)


@dp.callback_query(F.data.startswith("refresh_group:"))
async def refresh_group_schedule(callback: types.CallbackQuery):
    group_name = callback.data.split(":", 1)[1]
    
    cache = load_cache()
    cache_key = f"group_{group_name}"
    if cache_key in cache["groups"]:
        del cache["groups"][cache_key]
        save_cache(cache)
    
    await show_group_schedule(callback)


@dp.callback_query(F.data.startswith("refresh_teacher:"))
async def refresh_teacher_schedule(callback: types.CallbackQuery):
    teacher_name = callback.data.split(":", 1)[1]
    
    cache = load_cache()
    cache_key = f"teacher_{teacher_name}"
    if cache_key in cache["teachers"]:
        del cache["teachers"][cache_key]
        save_cache(cache)
    
    await show_teacher_schedule(callback)


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Группы", callback_data="groups"),
            InlineKeyboardButton(text="👨‍🏫 Преподаватели", callback_data="teachers")
        ],
        [
            InlineKeyboardButton(text="🔔 Звонки", callback_data="bells"),
            InlineKeyboardButton(text="⭐ Избранное", callback_data="favorites_menu")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_info"),
            InlineKeyboardButton(text="📱 О боте", callback_data="about_bot")
        ]
    ])
    
    await callback.message.edit_text(
        "👋 <b>Добро пожаловать в бот расписания колледжа!</b>\n\n"
        "Здесь вы можете посмотреть актуальное расписание занятий.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "help_info")
async def show_help(callback: types.CallbackQuery):
    help_text = """
❓ <b>ПОМОЩЬ ПО БОТУ</b>
────────────────────────────────────────

<b>Основные функции:</b>
• 👥 <b>Группы</b> - просмотр расписания для учебных групп
• 👨‍🏫 <b>Преподаватели</b> - просмотр расписания преподавателей
• 🔔 <b>Звонки</b> - расписание звонков на все дни недели
• ⭐ <b>Избранное</b> - быстрый доступ к часто используемым группам/преподавателям

<b>Как использовать:</b>
1. Выберите раздел (Группы или Преподаватели)
2. Выберите нужную группу или преподавателя из списка
3. Бот покажет расписание на текущую неделю

<b>Обновление данных:</b>
Данные обновляются автоматически при загрузке списков.
Для принудительного обновления нажмите кнопку "🔄 Обновить".

<b>Контакты:</b>
Если возникли проблемы, обратитесь к создателю бота: @espadawo.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(help_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "about_bot")
async def about_bot(callback: types.CallbackQuery):
    about_text = """
📱 <b>ИНФОРМАЦИЯ О БОТЕ</b>
────────────────────────────────────────

<b>Разработчик:</b>
Студент группы ИСа24-1

<b>Контакты:</b>
По всем вопросам писать: @espadawo

<b>Благодарности:</b>
Спасибо всем, кто пользуется ботом!
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(about_text, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(F.data == "search_groups")
async def search_groups(callback: types.CallbackQuery):
    await callback.answer("Поиск групп пока не реализован", show_alert=True)

@dp.callback_query(F.data == "search_teachers")
async def search_teachers(callback: types.CallbackQuery):
    await callback.answer("Поиск преподавателей пока не реализован", show_alert=True)


@dp.callback_query(F.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer()


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = str(message.from_user.id)
    admins = load_admins()
    
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав администратора!")
        return
    
    users_count = len(load_users())
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Сделать объявление", callback_data="make_announcement")],
        [InlineKeyboardButton(text=f"👥 Пользователи ({users_count})", callback_data="user_stats")],
        [InlineKeyboardButton(text="🔄 Обновить все списки", callback_data="force_update_lists")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
    ])
    
    await message.answer(f"👑 <b>Панель администратора</b>\n\nПользователей: {users_count}", 
                        parse_mode="HTML", reply_markup=keyboard)


@dp.message(Command("addadmin"))
async def cmd_addadmin(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    

    if user_id != MAIN_ADMIN_ID:
        await message.answer("⛔ Эта команда доступна только главному администратору!")
        return
    
    await message.answer("👑 <b>Добавление администратора</b>\n\n"
                        "Отправьте Telegram ID пользователя, которого хотите сделать администратором.\n\n"
                        "<i>ID можно получить с помощью бота @userinfobot</i>", 
                        parse_mode="HTML")
    await state.set_state(AdminStates.waiting_for_new_admin)


@dp.message(AdminStates.waiting_for_new_admin)
async def process_new_admin(message: Message, state: FSMContext):
    new_admin_id = message.text.strip()
    

    if not new_admin_id.isdigit():
        await message.answer("❌ ID должен состоять только из цифр!\n\n"
                            "Попробуйте снова или нажмите /cancel для отмены.")
        return
    
    admins = load_admins()
    
    if new_admin_id in admins:
        await message.answer(f"✅ Пользователь {new_admin_id} уже является администратором.")
    else:
        admins.append(new_admin_id)
        save_admins(admins)
        await message.answer(f"✅ Пользователь {new_admin_id} успешно добавлен в администраторы!")
    
    await state.clear()


@dp.message(Command("post"))
async def cmd_post(message: Message):
    user_id = str(message.from_user.id)
    admins = load_admins()
    
    if user_id not in admins:
        await message.answer("⛔ У вас нет прав для создания объявлений!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Текст", callback_data="announcement_text")],
        [InlineKeyboardButton(text="🖼️ Текст + фото", callback_data="announcement_photo")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_announcement")]
    ])
    
    await message.answer(
        "📢 <b>СОЗДАНИЕ ОБЪЯВЛЕНИЯ</b>\n\n"
        "Выберите тип объявления:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "announcement_text")
async def start_text_announcement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введите текст объявления:")
    await state.set_state(AdminStates.waiting_for_announcement)


@dp.callback_query(F.data == "announcement_photo")
async def start_photo_announcement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введите текст объявления (фото можно отправить следующим сообщением):")
    await state.set_state(AdminStates.waiting_for_announcement_photo)


@dp.message(AdminStates.waiting_for_announcement)
async def process_announcement_text(message: Message, state: FSMContext):
    await state.update_data(announcement_text=message.text, has_photo=False)
    await state.set_state(AdminStates.announcement_confirmation)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="send_announcement_confirm")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_announcement")]
    ])
    
    await message.answer(
        f"📢 <b>Предпросмотр объявления:</b>\n\n{message.text}\n\nОтправить всем пользователям?",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.message(AdminStates.waiting_for_announcement_photo)
async def process_announcement_photo(message: Message, state: FSMContext):

    if message.photo:

        photo_id = message.photo[-1].file_id
        caption = message.caption or ""
        
        await state.update_data(
            announcement_text=caption,
            photo_id=photo_id,
            has_photo=True
        )
        await state.set_state(AdminStates.announcement_confirmation)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="send_announcement_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_announcement")]
        ])
        

        await message.answer_photo(
            photo_id,
            caption=f"📢 <b>Предпросмотр объявления:</b>\n\n{caption}\n\nОтправить всем пользователям?",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:

        await state.update_data(
            announcement_text=message.text,
            has_photo=False
        )
        await state.set_state(AdminStates.announcement_confirmation)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data="send_announcement_confirm")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_announcement")]
        ])
        
        await message.answer(
            f"📢 <b>Предпросмотр объявления:</b>\n\n{message.text}\n\nОтправить всем пользователям?",
            parse_mode="HTML",
            reply_markup=keyboard
        )


@dp.callback_query(AdminStates.announcement_confirmation, F.data == "send_announcement_confirm")
async def send_announcement_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    announcement_text = user_data.get('announcement_text', '')
    has_photo = user_data.get('has_photo', False)
    photo_id = user_data.get('photo_id', None)
    
    if not announcement_text and not has_photo:
        await callback.answer("❌ Объявление пустое. Попробуйте снова.", show_alert=True)
        await state.clear()
        return
    
    await callback.message.edit_text("📤 Отправка объявления...")
    
    users = load_users()
    sent_count = 0
    failed_count = 0
    
    for user_id in users:
        try:
            if has_photo and photo_id:

                await bot.send_photo(
                    user_id,
                    photo_id,
                    caption=f"📢 <b>ОБЪЯВЛЕНИЕ</b>\n\n{announcement_text}" if announcement_text else "📢 <b>ОБЪЯВЛЕНИЕ</b>",
                    parse_mode="HTML"
                )
            else:

                await bot.send_message(
                    user_id, 
                    f"📢 <b>ОБЪЯВЛЕНИЕ</b>\n\n{announcement_text}", 
                    parse_mode="HTML"
                )
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Не удалось отправить объявление пользователю {user_id}: {e}")
            failed_count += 1
    
    await state.clear()
    
    result_text = f"✅ Объявление отправлено {sent_count} пользователям!"
    if failed_count > 0:
        result_text += f"\n❌ Не удалось отправить {failed_count} пользователям."
    
    await callback.message.edit_text(result_text)


@dp.callback_query(AdminStates.announcement_confirmation, F.data == "cancel_announcement")
async def cancel_announcement(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отправка объявления отменена")


async def main():
    logger.info("Бот запущен!")
    

    for file, default in [
        (USERS_FILE, []),
        (CACHE_FILE, {"last_update": None, "teachers": {}, "groups": {}}),
        (ADMINS_FILE, [MAIN_ADMIN_ID]),  
        (GROUPS_FILE, {"last_update": None, "groups": []}),
        (TEACHERS_FILE, {"last_update": None, "teachers": []}),
        (FAVORITES_FILE, {})
    ]:
        if not os.path.exists(file):
            if file == USERS_FILE:
                save_users(default)
            elif file == CACHE_FILE:
                save_cache(default)
            elif file == ADMINS_FILE:
                save_admins(default)
            elif file == GROUPS_FILE:
                save_groups_cache(default)
            elif file == TEACHERS_FILE:
                save_teachers_cache(default)
            elif file == FAVORITES_FILE:
                save_favorites(default)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())