import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import openai
from ai_service import AIService
from document_processor import DocumentProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импорт конфигурации
from config import Config

# Проверяем конфигурацию
Config.validate()

# Инициализация бота и диспетчера
bot = Bot(token=Config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация сервисов
ai_service = AIService(Config.OPENAI_API_KEY)
doc_processor = DocumentProcessor()

# Состояния для FSM
class BotStates(StatesGroup):
    waiting_for_case_description = State()
    waiting_for_document_upload = State()
    waiting_for_check_document = State()

# Клавиатуры
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти судебную практику", callback_data="find_practice")],
        [InlineKeyboardButton(text="📝 Подготовить жалобу", callback_data="prepare_complaint")],
        [InlineKeyboardButton(text="📄 Проверить документ", callback_data="check_document")],
        [InlineKeyboardButton(text="📢 Поделиться ботом", callback_data="share_bot")]
    ])
    return keyboard

def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_share_keyboard():
    # Текст для WhatsApp с информацией о боте
    whatsapp_text = "🤖 Попробуйте бота *Практика.Суд* - бесплатная юридическая помощь!\n\n✅ Найти судебную практику\n✅ Подготовить жалобу\n✅ Проверить документы\n✅ ИИ консультация\n\nhttps://t.me/dimon82juris_bot"
    # Делаем URL кодирование заранее, чтобы избежать backslash в f-строке
    encoded_text = whatsapp_text.replace(' ', '%20').replace('\n', '%0A')
    whatsapp_url = f"https://wa.me/?text={encoded_text}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📲 Telegram", switch_inline_query="Попробуйте бота Практика.Суд - бесплатная юридическая помощь!")],
        [InlineKeyboardButton(text="💬 Поделиться через WhatsApp", url=whatsapp_url)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = Config.WELCOME_MESSAGE
    
    start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Start", callback_data="start_bot")]
    ])
    
    await message.answer(welcome_text, reply_markup=start_keyboard)

# Обработчик кнопки Start
@dp.callback_query(F.data == "start_bot")
async def process_start_bot(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        Config.ABOUT_MESSAGE,
        reply_markup=get_main_keyboard()
    )

# Обработчик возврата в главное меню
@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text(
        "Выберите нужную функцию:",
        reply_markup=get_main_keyboard()
    )

# Обработчик поиска судебной практики
@dp.callback_query(F.data == "find_practice")
async def process_find_practice(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_case_description)
    await callback_query.message.edit_text(
        "Опишите вашу ситуацию подробно. Например:\n"
        "\"Меня уволили без приказа, хочу восстановиться на работе\"\n\n"
        "Чем подробнее вы опишете ситуацию, тем точнее будет найдена практика.",
        reply_markup=get_back_keyboard()
    )

# Обработчик описания ситуации
@dp.message(BotStates.waiting_for_case_description)
async def process_case_description(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Показываем, что бот обрабатывает запрос
    processing_message = await message.answer(
        "🔍 Анализирую вашу ситуацию и ищу релевантную судебную практику...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Получаем анализ от ИИ
        analysis = await ai_service.find_legal_practice(message.text)
        
        # Удаляем сообщение о обработке
        await processing_message.delete()
        
        # Отправляем результат
        await message.answer(
            f"📋 **Анализ вашей ситуации:**\n\n{analysis}",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await processing_message.delete()
        await message.answer(
            "❌ Произошла ошибка при анализе ситуации. Попробуйте еще раз позже.",
            reply_markup=get_back_keyboard()
        )
        logger.error(f"Error in case analysis: {e}")

# Обработчик подготовки жалобы
@dp.callback_query(F.data == "prepare_complaint")
async def process_prepare_complaint(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_document_upload)
    await callback_query.message.edit_text(
        "📄 Загрузите решение или определение суда в формате PDF, DOCX или TXT.\n\n"
        "Бот проанализирует документ и подготовит проект апелляционной или кассационной жалобы.",
        reply_markup=get_back_keyboard()
    )

# Обработчик загрузки документа для жалобы
@dp.message(BotStates.waiting_for_document_upload)
async def process_document_for_complaint(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer(
            "❌ Пожалуйста, загрузите документ в формате PDF, DOCX или TXT.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.clear()
    
    # Проверяем формат файла
    file_extension = message.document.file_name.split('.')[-1].lower()
    if file_extension not in ['pdf', 'docx', 'txt']:
        await message.answer(
            "❌ Поддерживаются только форматы PDF, DOCX и TXT.",
            reply_markup=get_back_keyboard()
        )
        return
    
    processing_message = await message.answer(
        "📝 Обрабатываю документ и готовлю жалобу...\n"
        "Это может занять несколько минут."
    )
    
    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = f"temp_{message.document.file_id}.{file_extension}"
        await bot.download_file(file.file_path, file_path)
        
        # Извлекаем текст
        document_text = doc_processor.extract_text(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if not document_text:
            await processing_message.delete()
            await message.answer(
                "❌ Не удалось извлечь текст из документа. Проверьте, что файл не поврежден.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Генерируем жалобу с помощью ИИ
        complaint = await ai_service.generate_complaint(document_text)
        
        await processing_message.delete()
        
        # Отправляем результат
        if len(complaint) > 4000:
            # Если текст слишком длинный, отправляем файлом
            with open(f"complaint_{message.from_user.id}.txt", "w", encoding="utf-8") as f:
                f.write(complaint)
            
            await message.answer_document(
                FSInputFile(f"complaint_{message.from_user.id}.txt"),
                caption="📝 Проект жалобы готов! Файл содержит подробный анализ и рекомендации.",
                reply_markup=get_back_keyboard()
            )
            
            os.remove(f"complaint_{message.from_user.id}.txt")
        else:
            await message.answer(
                f"📝 **Проект жалобы:**\n\n{complaint}",
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await processing_message.delete()
        await message.answer(
            "❌ Произошла ошибка при обработке документа. Попробуйте еще раз позже.",
            reply_markup=get_back_keyboard()
        )
        logger.error(f"Error in document processing: {e}")

# Обработчик проверки документа
@dp.callback_query(F.data == "check_document")
async def process_check_document(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_check_document)
    await callback_query.message.edit_text(
        "📄 Загрузите документ для проверки в формате PDF, DOCX или TXT.\n\n"
        "Бот проанализирует документ на наличие ошибок, недочетов и юридических рисков.",
        reply_markup=get_back_keyboard()
    )

# Обработчик загрузки документа для проверки
@dp.message(BotStates.waiting_for_check_document)
async def process_document_for_check(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer(
            "❌ Пожалуйста, загрузите документ в формате PDF, DOCX или TXT.",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.clear()
    
    # Проверяем формат файла
    file_extension = message.document.file_name.split('.')[-1].lower()
    if file_extension not in ['pdf', 'docx', 'txt']:
        await message.answer(
            "❌ Поддерживаются только форматы PDF, DOCX и TXT.",
            reply_markup=get_back_keyboard()
        )
        return
    
    processing_message = await message.answer(
        "🔍 Проверяю документ на ошибки и юридические риски...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = f"temp_{message.document.file_id}.{file_extension}"
        await bot.download_file(file.file_path, file_path)
        
        # Извлекаем текст
        document_text = doc_processor.extract_text(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if not document_text:
            await processing_message.delete()
            await message.answer(
                "❌ Не удалось извлечь текст из документа. Проверьте, что файл не поврежден.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Проверяем документ с помощью ИИ
        analysis = await ai_service.check_document(document_text)
        
        await processing_message.delete()
        
        # Отправляем результат
        await message.answer(
            f"📋 **Анализ документа:**\n\n{analysis}",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await processing_message.delete()
        await message.answer(
            "❌ Произошла ошибка при проверке документа. Попробуйте еще раз позже.",
            reply_markup=get_back_keyboard()
        )
        logger.error(f"Error in document check: {e}")

# Обработчик кнопки "Поделиться ботом"
@dp.callback_query(F.data == "share_bot")
async def process_share_bot(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📢 Расскажите о нашем боте друзьям и коллегам!\n\n"
        "🤖 Бот Практика.Суд поможет:\n"
        "• Найти судебную практику по любому спору\n"
        "• Подготовить апелляционную жалобу\n"
        "• Проверить документы на ошибки\n"
        "• Получить юридическую консультацию с ИИ\n\n"
        "Все услуги бесплатны!",
        reply_markup=get_share_keyboard()
    )

# Обработчик неизвестных команд
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "❓ Не понимаю вашу команду. Используйте кнопки меню для взаимодействия с ботом.",
        reply_markup=get_main_keyboard()
    )

# Основная функция
async def main():
    logger.info("Запуск бота Практика.Суд")
    
    try:
        # Проверяем конфигурацию
        Config.validate()
        
        # Устанавливаем команды бота
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запустить бота")
        ])
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 