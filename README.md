# KITiS39

# RU LANGUAGE

Telegram-бот для удобного просмотра актуального расписания учебных занятий колледжа с автоматическим обновлением данных с официального сайта.

#  Основные функции
- **👥 Расписание групп** - просмотр расписания для всех учебных групп
- **👨‍🏫 Расписание преподавателей** - расписание занятий преподавателей
- **🔔 Расписание звонков** - время пар на все дни недели
- **⭐ Система избранного** - быстрый доступ к часто используемым группам и преподавателям

###  Особенности
- **🔄 Автоматическое обновление** - данные синхронизируются с сайтом колледжа
- **💾 Умное кэширование** - работает даже при недоступности сайта
- **📱 Удобный интерфейс** - интуитивно понятные кнопки в 3 колонки
- **⚡ Быстрая работа** - оптимизированные запросы и парсинг

### Административные функции
- **📢 Рассылка объявлений** - отправка сообщений всем пользователям
- **🖼️ Объявления с фото** - поддержка медиа-контента
- **👥 Управление администраторами** - гибкая система прав

## Технические особенности

# Архитектура
- **Асинхронная архитектура** на основе asyncio для высокой производительности
- **Модульная структура** с разделением ответственности
- **Состояния FSM** для обработки многошаговых действий (объявления, добавление админов)
- **Кэширование в памяти и файлах** для отказоустойчивости

# Обработка данных
- **Интеллектуальный парсинг HTML** с автоматическим определением структуры таблиц
- **Обработка кодировок** (windows-1251, cp1251) для корректного отображения кириллицы
- **Фильтрация данных** - автоматическое удаление пустых записей ("Вакансия", "Ваканс")
- **Валидация времени** пар с учетом разных расписаний (понедельник vs другие дни)

# Безопасность и надежность
- **Проверка прав доступа** для административных функций
- **Обработка исключений** при сетевых сбоях
- **Резервное хранение** данных в JSON формате
- **Логирование операций** для отладки и мониторинга

# Оптимизации
- **Пагинация списков** для работы с большими объемами данных (группы, преподаватели)
- **Ленивая загрузка** расписания (только по запросу)
- **Оптимизация запросов** к Telegram API (задержки между сообщениями)
- **Кэширование ответов** для повторных запросов

# Конфигурация
- **Гибкая настройка** через константы в коде
- **Динамическое обновление** списков без перезапуска бота
- **Легкая миграция** между серверами
- **Минимальные зависимости** для простоты развертывания

# EN LANGUAGE

Telegram bot for convenient viewing of up-to-date college class schedules with automatic data updates from the official website.

# Main Features

# Core Functions
- **👥 Group Schedules** - view schedules for all study groups
- **👨‍🏫 Teacher Schedules** - view schedules for teachers
- **🔔 Bell Schedule** - class times for all days of the week
- **⭐ Favorites System** - quick access to frequently used groups and teachers

### Features
- **🔄 Automatic Updates** - data synchronizes with the college website
- **💾 Smart Caching** - works even when the website is unavailable
- **📱 User-Friendly Interface** - intuitive buttons in 3 columns
- **⚡ Fast Performance** - optimized requests and parsing

### Administrative Functions
- **📢 Announcement Broadcast** - send messages to all users
- **🖼️ Photo Announcements** - media content support
- **👥 Administrator Management** - flexible permission system

## Technical Features

# Architecture
- **Asynchronous Architecture** based on asyncio for high performance
- **Modular Structure** with separation of responsibilities
- **FSM States** for multi-step action processing (announcements, adding admins)
- **In-Memory and File Caching** for fault tolerance

# Data Processing
- **Intelligent HTML Parsing** with automatic table structure detection
- **Encoding Handling** (windows-1251, cp1251) for correct Cyrillic display
- **Data Filtering** - automatic removal of empty records ("Vacancy", "Vacant")
- **Time Validation** for classes considering different schedules (Monday vs other days)

# Security and Reliability
- **Access Rights Verification** for administrative functions
- **Exception Handling** during network failures
- **Backup Storage** of data in JSON format
- **Operation Logging** for debugging and monitoring

# Optimizations
- **List Pagination** for working with large volumes of data (groups, teachers)
- **Lazy Loading** of schedules (only on request)
- **Request Optimization** for Telegram API (delays between messages)
- **Response Caching** for repeated requests

# Configuration
- **Flexible Configuration** via constants in code
- **Dynamic Updates** of lists without bot restart
- **Easy Migration** between servers
- **Minimal Dependencies** for easy deployment

# Связь со мной / Contact with me
[Telegram DM](https://t.me/espadawo)

[Telegram Channel](https://t.me/onespada)
