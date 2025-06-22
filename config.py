import os

class Config:
    """Конфигурация бота"""
    
    # Токены и ключи API
    BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    # OpenAI API ключ
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'sk-proj-YOUR_OPENAI_API_KEY_HERE')
    
    # Настройки файлов
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FORMATS = ['pdf', 'docx', 'txt']
    TEMP_DIR = 'temp'
    
    # Настройки OpenAI
    OPENAI_MODEL = 'gpt-3.5-turbo'  # Более дешевая модель для тестирования
    OPENAI_MAX_TOKENS = 1500
    OPENAI_TEMPERATURE = 0.3
    
    # Настройки бота
    BOT_NAME = 'Практика.Суд'
    BOT_USERNAME = '@dimon82juris_bot'
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
        f"Попробуйте также наше мобильное приложение «Календарь Юриста»: {APP_LINK}\n\n"
        "Контроль всех дел, сроков и заседаний — теперь прямо в телефоне:\n"
        "✅ Напоминания о сроках\n"
        "✅ Учёт дел, клиентов и задач\n"
        "✅ Доступ к судебной информации\n"
        "✅ Удобный интерфейс\n"
        "✅ Работает на смартфоне и компьютере\n\n"
        "Выберите нужную функцию:"
    )
    
    @classmethod
    def validate(cls):
        """Проверка конфигурации"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден в переменных окружения")
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
        
        return True 