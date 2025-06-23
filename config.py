import os

class Config:
    """Конфигурация бота"""
    
    # Токены и ключи API - берутся из переменных окружения
    BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY_HERE')
    
    # Настройки файлов
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FORMATS = ['pdf', 'docx', 'txt']
    TEMP_DIR = 'temp'
    
    # Настройки OpenAI
    OPENAI_MODEL = 'gpt-4o'  # Рекомендуемая модель
    OPENAI_MAX_TOKENS = 1500  # Ограничиваем для соответствия лимитам Telegram
    OPENAI_TEMPERATURE = 0.1  # Минимальная температура для максимальной точности чтобы гпт не наебал нас с диз инфой
    
    # Настройки бота
    BOT_NAME = 'AI Law Assistant'
    BOT_USERNAME = '@Sud_praktik_bot'
    APP_LINK = 'https://onelink.to/rsv8c3'
    
    # Сообщения
    WELCOME_MESSAGE = (
        "Здравствуйте! Наш бесплатный бот найдет всю судебную практику по вашему спору, "
        "подготовит апелляционную (кассационную) жалобу на решение суда, напишет отзыв на иск, "
        "проверит документ на ошибки.\n\n"
        "Для продолжения нажмите кнопку Start."
    )
    
    ABOUT_MESSAGE = (
        "Уважаемый пользователь, благодарим Вас за пользование нашим ботом.\n\n"
        "📱 <b>Мобильное приложение для юристов и адвокатов</b>\n"
        "<b>«Календарь Юриста»</b>\n\n"
        "Контроль всех дел и сроков в одном месте:\n"
        "✅ Напоминания о сроках\n"
        "✅ Учёт дел и клиентов\n"
        "✅ Доступ к судебной информации\n"
        "✅ Удобный интерфейс\n\n"
        "🔗 <a href='{}'>📥 СКАЧАТЬ ПРИЛОЖЕНИЕ</a>\n\n"
        "Выберите нужную функцию:"
    ).format(APP_LINK)
    
    @classmethod
    def validate(cls):
        """Проверка конфигурации"""
        if not cls.BOT_TOKEN or cls.BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        if not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == 'YOUR_OPENAI_API_KEY_HERE':
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
        
        return True 