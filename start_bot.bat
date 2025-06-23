@echo off
chcp 65001 >nul
title Практика.Суд - Telegram Bot

echo ===============================================
echo           Запуск бота "Практика.Суд"
echo ===============================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден! Установите Python 3.8+ 
    echo 📝 Скачайте с https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Проверяем наличие .env файла
if not exist .env (
    echo ❌ Файл .env не найден!
    echo 📝 Создайте файл .env с переменными:
    echo    BOT_TOKEN=your_telegram_bot_token
    echo    OPENAI_API_KEY=your_openai_api_key
    pause
    exit /b 1
)

REM Проверяем наличие requirements.txt
if not exist requirements.txt (
    echo ❌ Файл requirements.txt не найден!
    pause
    exit /b 1
)

echo 📦 Проверка зависимостей...
python -c "import aiogram, openai, docx, fitz" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️ Устанавливаем зависимости...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Ошибка установки зависимостей!
        pause
        exit /b 1
    )
)

echo ✅ Все проверки пройдены
echo 🚀 Запуск бота...
echo 📱 Ссылка: https://t.me/dimon82juris_bot
echo 🔄 Для остановки нажмите Ctrl+C
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Бот завершился с ошибкой
    pause
)

echo.
echo ⛔ Бот остановлен
pause 