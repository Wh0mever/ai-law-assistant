#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}          Запуск бота 'Практика.Суд'${NC}"
echo -e "${BLUE}===============================================${NC}"
echo

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден! Установите Python 3.8+${NC}"
    exit 1
fi

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo -e "${YELLOW}📝 Создайте файл .env с переменными:${NC}"
    echo "   BOT_TOKEN=your_telegram_bot_token"
    echo "   OPENAI_API_KEY=your_openai_api_key"
    exit 1
fi

# Проверяем наличие requirements.txt
if [ ! -f requirements.txt ]; then
    echo -e "${RED}❌ Файл requirements.txt не найден!${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Проверка зависимостей...${NC}"

# Проверяем зависимости
python3 -c "import aiogram, openai, docx, fitz" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️ Устанавливаем зависимости...${NC}"
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Ошибка установки зависимостей!${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Все проверки пройдены${NC}"
echo -e "${BLUE}🚀 Запуск бота...${NC}"
echo -e "${BLUE}📱 Ссылка: https://t.me/dimon82juris_bot${NC}"
echo -e "${YELLOW}🔄 Для остановки нажмите Ctrl+C${NC}"
echo

# Запускаем бота
python3 main.py

echo
echo -e "${YELLOW}⛔ Бот остановлен${NC}" 