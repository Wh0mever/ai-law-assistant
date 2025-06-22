#!/usr/bin/env python3
"""
Скрипт для запуска Telegram-бота "Практика.Суд"
"""

import sys
import os
import asyncio
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from main import main

if __name__ == "__main__":
    print("🚀 Запуск бота 'Практика.Суд'...")
    print("📋 Проверка переменных окружения...")
    
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("📝 Создайте файл .env с переменными:")
        print("   BOT_TOKEN=your_telegram_bot_token")
        print("   OPENAI_API_KEY=your_openai_api_key")
        sys.exit(1)
    
    # Проверяем основные зависимости
    try:
        import aiogram
        import openai
        import docx
        import fitz
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    
    print("🤖 Бот готов к запуску!")
    print("📱 Ссылка на бота: https://t.me/dimon82juris_bot")
    print("🔄 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при запуске: {e}")
        sys.exit(1) 