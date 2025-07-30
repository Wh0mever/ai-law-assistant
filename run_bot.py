#!/usr/bin/env python3
"""
Запуск бота "Виртуальный юрист" с локальной базой юридических документов
"""
import asyncio
import logging
import sys
import os

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

def check_dependencies():
    """Проверка зависимостей"""
    required_files = [
        'config.py',
        'main.py', 
        'ai_service.py',
        'perplexity_service.py',
        'legal_knowledge.py',
        'document_processor.py',
        'tts_service.py',
        'admin_panel.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Отсутствуют необходимые файлы:")
        for file in missing_files:
            print(f"   • {file}")
        
        print("\n💡 Убедитесь, что все компоненты системы установлены")
        print("💡 Проверьте API ключи в config.py")
        
        return False
    
    return True

async def main():
    """Основная функция"""
    print("🏛️ Запуск бота 'Виртуальный юрист' с Perplexity AI")
    print("=" * 50)
    
    # Настройка логирования
    setup_logging()
    
    # Проверка зависимостей
    print("🔍 Проверка системы...")
    if not check_dependencies():
        print("❌ Система не готова к запуску")
        return
    
    print("✅ Все компоненты найдены")
    
    # Импорт и запуск основного модуля
    try:
        from main import main as bot_main
        print("🚀 Запуск Telegram-бота...")
        await bot_main()
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что все зависимости установлены")
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        logging.error(f"Bot startup error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1) 