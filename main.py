import asyncio
import logging
import os
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
# OpenAI импорт убран - используется через AIService
from ai_service import AIService
from document_processor import DocumentProcessor
from legal_knowledge import LegalKnowledge
from tts_service import TTSService
from admin_panel import AdminPanel

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
tts_service = TTSService(Config.OPENAI_API_KEY)
admin_panel = AdminPanel()

# Состояния для FSM
class BotStates(StatesGroup):
    waiting_for_case_description = State()
    waiting_for_document_upload = State()
    waiting_for_check_document = State()

# Клавиатуры
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=Config.MENU_BUTTONS["search_practice"], callback_data="find_practice")],
        [InlineKeyboardButton(text=Config.MENU_BUTTONS["prepare_appeal"], callback_data="prepare_complaint")],
        [InlineKeyboardButton(text=Config.MENU_BUTTONS["check_documents"], callback_data="check_document")],
        [InlineKeyboardButton(text=Config.MENU_BUTTONS["share_bot"], callback_data="share_bot")]
    ])
    return keyboard

def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="main_menu")]
    ])
    return keyboard

def get_share_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 СКАЧАТЬ ПРИЛОЖЕНИЕ", url="https://onelink.to/rsv8c3")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
    return keyboard

# Функция для отправки рекламного сообщения БЕЗ голосового дублирования
async def send_promo_message_with_voice(message: types.Message):
    """Отправляет рекламное сообщение о приложении 'Календарь Юриста' только текстом"""
    try:
        promo_text = """🏛️ Уважаемый пользователь, благодарим Вас за пользование нашим ботом.

📱 Мобильное приложение для юристов и адвокатов «Календарь Юриста»

Контроль всех дел и сроков в одном месте:
✅ Напоминания о сроках
✅ Учёт дел и клиентов  
✅ Доступ к судебной информации
✅ Удобный интерфейс

Выберите нужную функцию:"""
        
        promo_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 СКАЧАТЬ ПРИЛОЖЕНИЕ", url="https://onelink.to/rsv8c3")]
        ])
        
        # Отправляем только текстовое сообщение
        await message.answer(
            promo_text,
            reply_markup=promo_keyboard,
            parse_mode='HTML'
        )
        logger.info("✅ Рекламное сообщение отправлено (только текст)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки рекламного сообщения: {e}")

# Функция для отправки ответа с голосовым дублированием
async def send_response_with_voice(message: types.Message, text_response: str, reply_markup=None):
    """Отправляет текстовый ответ и его голосовую версию"""
    try:
        # Логируем активность пользователя и запрос
        admin_panel.log_user_activity(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        
        # Логируем запрос пользователя  
        admin_panel.log_user_request(
            user_id=message.from_user.id,
            request_type="bot_response",
            request_text=text_response[:500] + "..." if len(text_response) > 500 else text_response,
            response_text="Response sent with voice",
            processing_time=0.0
        )
        
        # Отправляем текстовый ответ
        if len(text_response) > 4000:
            # Если ответ слишком длинный, отправляем файлом
            filename = f"response_{message.from_user.id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text_response)
            
            await message.answer_document(
                FSInputFile(filename),
                caption="📋 Подробный ответ готов!",
                reply_markup=reply_markup or get_back_keyboard()
            )
            
            try:
                os.remove(filename)
            except Exception:
                pass
        else:
            # Отправляем обычным сообщением
            await message.answer(
                text_response,
                reply_markup=reply_markup or get_back_keyboard(),
                parse_mode='HTML'
            )
        
        # Генерируем голосовое сообщение
        logger.info("🎤 Генерирую голосовую версию ответа...")
        voice_data = await tts_service.text_to_speech(text_response)
        
        if voice_data:
            # Отправляем голосовое сообщение через BufferedInputFile
            voice_file = BufferedInputFile(
                voice_data, 
                filename="response.mp3"  # Telegram поддерживает MP3
            )
            
            await message.answer_voice(
                voice=voice_file,
                caption="""🎤 Голосовая версия ответа

❓ Не нашли ответа? Возникли вопросы?
🆓 Бесплатная юридическая консультация @ZachitaPrava02"""
            )
            logger.info("✅ Голосовой ответ отправлен")
        else:
            logger.warning("⚠️ Не удалось создать голосовой ответ")
        
        # Отправляем рекламное сообщение
        await send_promo_message_with_voice(message)
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки ответа с голосом: {e}")
        
        # В случае ошибки НЕ отправляем текстовый ответ повторно
        # (он уже был отправлен выше)
        logger.warning("⚠️ Голосовое сообщение не отправлено, но текстовый ответ пользователь получил")

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = Config.WELCOME_TEXT
    
    # Отправляем только приветствие без промо
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# Обработчик кнопки Start (удален, теперь команда /start сразу показывает меню)

# Обработчик возврата в главное меню
@dp.callback_query(F.data == "main_menu")
async def process_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text(
        "🏛️ Главное меню\n\nВыберите нужную функцию:",
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
        Config.TEXTS["processing"]
    )
    
    # Логируем активность пользователя
    admin_panel.log_user_activity(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    try:
        # Определяем тип сообщения и получаем текст
        if message.voice:
            # Это голосовое сообщение - обрабатываем через AI
            logger.info(f"🎤 Получено голосовое сообщение в состоянии waiting_for_case_description от пользователя {message.from_user.id}")
            
            # Обновляем сообщение о обработке
            try:
                await processing_message.edit_text("🎤 Обрабатываю голосовое сообщение и анализирую ситуацию...")
            except Exception:
                pass
            
            # Получаем голосовой файл
            voice = message.voice
            file_info = await bot.get_file(voice.file_id)
            voice_file_io = await bot.download_file(file_info.file_path)
            voice_file_bytes = voice_file_io.read()
            
            # Определяем формат файла
            file_format = "ogg"
            if file_info.file_path:
                file_extension = file_info.file_path.split('.')[-1].lower()
                if file_extension in ['ogg', 'mp3', 'wav', 'm4a', 'mp4']:
                    file_format = file_extension
            
            # Сначала транскрибируем голосовое сообщение
            transcribed_text = await ai_service.transcribe_voice_message(voice_file_bytes, file_format)
            
            # Проверяем, что транскрипция успешна
            if transcribed_text.startswith("❌") or not transcribed_text:
                logger.error("❌ Транскрипция не удалась")
                try:
                    await processing_message.delete()
                except Exception:
                    pass
                await message.answer(
                    "❌ Не удалось распознать голосовое сообщение. Попробуйте еще раз или напишите текстом.",
                    reply_markup=get_back_keyboard()
                )
                return
                
            # Логируем запрос как голосовой
            admin_panel.log_user_request(
                user_id=message.from_user.id,
                request_type="voice_legal_practice_search",
                request_text=transcribed_text,
                response_text="",
                processing_time=0.0
            )
            
            # Получаем анализ от ИИ на основе транскрибированного текста
            analysis = await ai_service.find_legal_practice(transcribed_text)
            
            # Добавляем информацию о том, что это было голосовое сообщение
            voice_header = f"""🎤 <b>Распознанный текст:</b> "{transcribed_text}"

📋 <b>АНАЛИЗ ВАШЕЙ СИТУАЦИИ:</b>

"""
            analysis = voice_header + analysis
            
        elif message.text:
            # Это текстовое сообщение - обрабатываем как обычно
            logger.info(f"📝 Получено текстовое сообщение в состоянии waiting_for_case_description от пользователя {message.from_user.id}")
            
            # Логируем запрос как текстовый
            admin_panel.log_user_request(
                user_id=message.from_user.id,
                request_type="legal_practice_search", 
                request_text=message.text,
                response_text="",
                processing_time=0.0
            )
            
            # Получаем анализ от ИИ
            analysis = await ai_service.find_legal_practice(message.text)
        
        else:
            # Неподдерживаемый тип сообщения
            logger.error(f"❌ Получено сообщение неподдерживаемого типа от пользователя {message.from_user.id}")
            try:
                await processing_message.delete()
            except Exception:
                pass
            await message.answer(
                "❌ Пожалуйста, отправьте текстовое сообщение с описанием вашей ситуации или голосовое сообщение.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Удаляем сообщение о обработке
        try:
            await processing_message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        # Проверяем, является ли analysis списком частей
        if isinstance(analysis, list):
            # Отправляем каждую часть отдельно
            for i, part in enumerate(analysis):
                # Добавляем рекламу только к последней части
                if i == len(analysis) - 1:
                    part_with_ad = f"""{part}

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
                    await send_response_with_voice(message, part_with_ad)
                else:
                    # Без рекламы для промежуточных частей
                    await message.answer(part, parse_mode='HTML', reply_markup=get_back_keyboard())
                    
                # Небольшая задержка между сообщениями
                await asyncio.sleep(1)
        else:
            # Обычная обработка одного ответа
            if len(analysis) > 4000:
                # Если ответ слишком длинный, отправляем файлом
                with open(f"analysis_{message.from_user.id}.txt", "w", encoding="utf-8") as f:
                    f.write(analysis)
                
                await message.answer_document(
                    FSInputFile(f"analysis_{message.from_user.id}.txt"),
                    caption="📋 Анализ вашей ситуации готов! Файл содержит подробное рассмотрение.",
                    reply_markup=get_back_keyboard()
                )
                
                os.remove(f"analysis_{message.from_user.id}.txt")
            else:
                # Отправляем результат с голосовым дублированием
                await send_response_with_voice(message, analysis)
        
    except Exception as e:
        try:
            await processing_message.delete()
        except Exception:
            pass
        await message.answer(
            Config.TEXTS["error"],
            reply_markup=get_back_keyboard(),
            parse_mode='HTML'
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
    
    # Проверяем размер файла
    if message.document.file_size > Config.MAX_FILE_SIZE:
        await message.answer(
            Config.TEXTS["file_too_large"],
            reply_markup=get_back_keyboard()
        )
        return

    # Проверяем формат файла
    file_extension = '.' + message.document.file_name.split('.')[-1].lower()
    if file_extension not in Config.ALLOWED_EXTENSIONS:
        await message.answer(
            Config.TEXTS["unsupported_format"],
            reply_markup=get_back_keyboard()
        )
        return
    
    processing_message = await message.answer(
        Config.TEXTS["processing"]
    )
    
    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = f"{Config.UPLOAD_DIR}/temp_{message.document.file_id}{file_extension}"
        await bot.download_file(file.file_path, file_path)
        
        # Извлекаем текст
        document_text = doc_processor.extract_text(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if not document_text:
            try:
                await processing_message.delete()
            except Exception:
                pass
            await message.answer(
                Config.TEXTS["error"],
                reply_markup=get_back_keyboard()
            )
            return
        
        # Генерируем жалобу с помощью ИИ
        complaint = await ai_service.generate_complaint(document_text)
        
        try:
            await processing_message.delete()
        except Exception:
            pass
        
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
            await send_response_with_voice(message, complaint)
            
    except Exception as e:
        try:
            await processing_message.delete()
        except Exception:
            pass
        await message.answer(
            Config.TEXTS["error"],
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
    
    # Проверяем размер файла
    if message.document.file_size > Config.MAX_FILE_SIZE:
        await message.answer(
            Config.TEXTS["file_too_large"],
            reply_markup=get_back_keyboard()
        )
        return

    # Проверяем формат файла
    file_extension = '.' + message.document.file_name.split('.')[-1].lower()
    if file_extension not in Config.ALLOWED_EXTENSIONS:
        await message.answer(
            Config.TEXTS["unsupported_format"],
            reply_markup=get_back_keyboard()
        )
        return
    
    processing_message = await message.answer(
        Config.TEXTS["analyzing"]
    )
    
    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_path = f"{Config.UPLOAD_DIR}/temp_{message.document.file_id}{file_extension}"
        await bot.download_file(file.file_path, file_path)
        
        # Извлекаем текст
        document_text = doc_processor.extract_text(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if not document_text:
            try:
                await processing_message.delete()
            except Exception:
                pass
            await message.answer(
                Config.TEXTS["error"],
                reply_markup=get_back_keyboard()
            )
            return
        
        # Проверяем документ с помощью ИИ
        analysis = await ai_service.check_document(document_text)
        
        try:
            await processing_message.delete()
        except Exception:
            pass
        
        # Проверяем длину ответа
        if len(analysis) > 4000:
            # Если ответ слишком длинный, отправляем файлом
            with open(f"document_check_{message.from_user.id}.txt", "w", encoding="utf-8") as f:
                f.write(analysis)
            
            await message.answer_document(
                FSInputFile(f"document_check_{message.from_user.id}.txt"),
                caption="📋 Анализ документа готов! Файл содержит подробную проверку.",
                reply_markup=get_back_keyboard()
            )
            
            os.remove(f"document_check_{message.from_user.id}.txt")
        else:
            # Отправляем результат с голосовым дублированием  
            await send_response_with_voice(message, analysis)
        
    except Exception as e:
        try:
            await processing_message.delete()
        except Exception:
            pass
        await message.answer(
            Config.TEXTS["error"],
            reply_markup=get_back_keyboard(),
            parse_mode='HTML'
        )
        logger.error(f"Error in document check: {e}")

# Обработчик кнопки "Поделиться ботом"
@dp.callback_query(F.data == "share_bot")
async def process_share_bot(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        Config.TEXTS["share"],
        reply_markup=get_share_keyboard()
    )

# Обработчик голосовых сообщений (только когда нет активного FSM состояния)
@dp.message(F.voice)
async def process_voice_message(message: types.Message, state: FSMContext):
    """Обработка голосовых сообщений с распознаванием речи и поиском практики"""
    
    # Проверяем, не находится ли пользователь в FSM состоянии
    current_state = await state.get_state()
    if current_state is not None:
        logger.info(f"🎤 Голосовое сообщение пропущено - пользователь в состоянии {current_state}")
        return  # Пропускаем, пусть обрабатывает FSM обработчик
    
    # Показываем сообщение о начале обработки
    processing_message = await message.answer(
        "🎤 <b>Обрабатываю голосовое сообщение...</b>\n\n"
        "⏳ Распознаю речь через Whisper-1...\n"
        "🔍 Затем найду подходящую судебную практику...",
        parse_mode='HTML'
    )
    
    try:
        logger.info(f"🎤 Получено голосовое сообщение от пользователя {message.from_user.id}")
        
        # Получаем информацию о голосовом файле
        voice = message.voice
        logger.info(f"📊 Информация о голосовом сообщении: длительность {voice.duration}с, размер {voice.file_size} байт")
        
        # Проверяем длительность (ограничиваем слишком длинными сообщениями)
        if voice.duration > 300:  # 5 минут
            await processing_message.edit_text(
                "❌ <b>Голосовое сообщение слишком длинное</b>\n\n"
                "⚠️ Максимальная длительность: 5 минут\n"
                "💡 Попробуйте записать более короткое сообщение или напишите текстом.",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        # Обновляем статус обработки
        await processing_message.edit_text(
            "🎤 <b>Обрабатываю голосовое сообщение...</b>\n\n"
            "📡 Загружаю аудио файл...",
            parse_mode='HTML'
        )
        
        # Получаем файл с серверов Telegram
        file_info = await bot.get_file(voice.file_id)
        voice_file_io = await bot.download_file(file_info.file_path)
        
        # Извлекаем байты из BytesIO объекта
        voice_file_bytes = voice_file_io.read()
        voice_file_io.seek(0)  # Возвращаем указатель в начало для повторного использования
        
        logger.info(f"✅ Голосовой файл загружен, размер: {len(voice_file_bytes)} байт")
        
        # Обновляем статус
        await processing_message.edit_text(
            "🎤 <b>Обрабатываю голосовое сообщение...</b>\n\n"
            "✅ Файл загружен\n"
            "🎯 Распознаю речь и анализирую ситуацию...",
            parse_mode='HTML'
        )
        
        # Определяем формат файла (Telegram обычно присылает .ogg)
        file_format = "ogg"
        if file_info.file_path:
            file_extension = file_info.file_path.split('.')[-1].lower()
            if file_extension in ['ogg', 'mp3', 'wav', 'm4a', 'mp4']:
                file_format = file_extension
        
        logger.info(f"🎵 Формат аудио файла: {file_format}")
        
        # Отправляем на обработку в AI сервис
        analysis_result = await ai_service.process_voice_message(voice_file_bytes, file_format)
        
        # Удаляем сообщение о обработке
        try:
            await processing_message.delete()
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение об обработке: {e}")
        
        # Проверяем длину ответа
        if len(analysis_result) > 4000:
            # Если ответ слишком длинный, отправляем файлом
            filename = f"voice_analysis_{message.from_user.id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(analysis_result)
            
            await message.answer_document(
                FSInputFile(filename),
                caption="🎤 <b>Анализ голосового сообщения готов!</b>\n\n"
                       "📋 Файл содержит распознанный текст и подробный анализ ситуации.",
                reply_markup=get_back_keyboard(),
                parse_mode='HTML'
            )
            
            # Удаляем временный файл
            try:
                os.remove(filename)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {filename}: {e}")
        else:
            # Отправляем результат с голосовым дублированием
            await send_response_with_voice(message, analysis_result)
        
        logger.info(f"✅ Голосовое сообщение успешно обработано для пользователя {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке голосового сообщения: {e}")
        
        # Удаляем сообщение о обработке в случае ошибки
        try:
            await processing_message.delete()
        except Exception:
            pass
        
        # Отправляем сообщение об ошибке
        error_message = "❌ <b>Ошибка обработки голосового сообщения</b>\n\n"
        
        if "insufficient_quota" in str(e) or "429" in str(e):
            error_message += "⚠️ Превышена квота OpenAI API\n"
            error_message += "💡 Попробуйте позже или напишите вопрос текстом"
        elif "audio" in str(e).lower() or "format" in str(e).lower():
            error_message += "⚠️ Проблема с аудио файлом\n"
            error_message += "💡 Попробуйте записать сообщение еще раз"
        else:
            error_message += "⚠️ Временная техническая проблема\n"
            error_message += "💡 Попробуйте написать вопрос текстом или повторите позже"
        
        await message.answer(
            error_message,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

# Обработчик команды /admin
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Обработчик команды админ-панели"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer(
            "❌ У вас нет прав доступа к админ-панели.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Логируем вход администратора
    admin_panel.log_system_event(
        event_type="admin_login", 
        event_data=f"Администратор {message.from_user.username or message.from_user.first_name} вошел в панель",
        user_id=message.from_user.id
    )
    
    # Получаем статистику
    stats = await get_admin_statistics()
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_analytics")],
        [InlineKeyboardButton(text="📝 Запросы", callback_data="admin_requests")],
        [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(
        f"""🛠️ <b>АДМИН-ПАНЕЛЬ "Виртуальный юрист"</b>

📊 <b>СТАТИСТИКА:</b>
👥 Всего пользователей: {stats['total_users']}
🔥 Активных за день: {stats['active_today']}
📝 Запросов сегодня: {stats['requests_today']}
⭐ Топ пользователь: {stats['top_user']}

🎯 <b>ДЕЙСТВИЯ:</b>
Выберите нужную функцию ниже""",
        reply_markup=admin_keyboard,
        parse_mode='HTML'
    )

# Функция получения статистики для админов
async def get_admin_statistics():
    """Получает статистику для админ-панели"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        logger.info("🗄️ Подключение к базе данных...")
        conn = sqlite3.connect(admin_panel.db_path, timeout=5.0)  # Добавляем таймаут
        cursor = conn.cursor()
        
        # Общее количество пользователей
        logger.info("👥 Получение количества пользователей...")
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0
        logger.info(f"✅ Пользователей: {total_users}")
        
        # Активные за день
        logger.info("🔥 Получение активных пользователей...")
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (yesterday.isoformat(),))
        active_today = cursor.fetchone()[0] or 0
        logger.info(f"✅ Активных: {active_today}")
        
        # Запросы сегодня
        logger.info("📝 Получение запросов за сегодня...")
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM user_requests WHERE DATE(timestamp) = ?", (today,))
        requests_today = cursor.fetchone()[0] or 0
        logger.info(f"✅ Запросов: {requests_today}")
        
        # Топ пользователь
        logger.info("⭐ Получение топ пользователя...")
        cursor.execute("""
            SELECT first_name, username, total_requests 
            FROM users 
            WHERE total_requests IS NOT NULL AND total_requests > 0
            ORDER BY total_requests DESC 
            LIMIT 1
        """)
        top_user_data = cursor.fetchone()
        if top_user_data:
            first_name = top_user_data[0] or ""
            username = top_user_data[1] or ""
            total_requests = top_user_data[2] or 0
            name = first_name or username or "Неизвестный"
            top_user = f"{name} ({total_requests} запросов)"
        else:
            top_user = "Нет данных"
        logger.info(f"✅ Топ пользователь: {top_user}")
        
        conn.close()
        logger.info("✅ Статистика успешно получена")
        
        return {
            'total_users': total_users,
            'active_today': active_today, 
            'requests_today': requests_today,
            'top_user': top_user
        }
        
    except sqlite3.OperationalError as e:
        logger.error(f"❌ Ошибка базы данных: {e}")
        return {
            'total_users': 0,
            'active_today': 0,
            'requests_today': 0,
            'top_user': "БД недоступна"
        }
    except Exception as e:
        logger.error(f"❌ Общая ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'active_today': 0,
            'requests_today': 0,
            'top_user': "Ошибка загрузки"
        }

# Обработчики админ кнопок
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin_actions(callback_query: types.CallbackQuery):
    """Обработчик действий админ-панели"""
    if not admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    action = callback_query.data.split("_")[1]
    
    if action == "users":
        await show_users_list(callback_query)
    elif action == "analytics":
        await show_analytics(callback_query)
    elif action == "requests":
        await show_requests_list(callback_query)
    elif action == "export":
        await show_export_options(callback_query)
    elif action == "back":
        # Перенаправляем на admin_back
        await admin_back(callback_query)
    else:
        logger.warning(f"⚠️ Неизвестное действие админ-панели: {action}")
        await callback_query.answer("❌ Неизвестное действие", show_alert=True)

async def show_users_list(callback_query: types.CallbackQuery):
    """Показывает список пользователей"""
    try:
        import sqlite3
        conn = sqlite3.connect(admin_panel.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, first_name, username, total_requests, last_activity
            FROM users 
            ORDER BY total_requests DESC 
            LIMIT 20
        """)
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            await callback_query.message.edit_text(
                "👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n\nПользователи не найдены.",
                parse_mode='HTML'
            )
            return
        
        users_text = "👥 <b>ТОП-20 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:</b>\n\n"
        
        for i, (user_id, first_name, username, requests, last_activity) in enumerate(users, 1):
            name = first_name or username or f"ID{user_id}"
            requests_count = requests or 0
            activity_text = last_activity[:16] if last_activity else "Неизвестно"
            users_text += f"{i}. <b>{name}</b>\n"
            users_text += f"   📝 Запросов: {requests_count}\n"
            users_text += f"   🕐 Последняя активность: {activity_text}\n\n"
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
        ])
        
        # Используем edit_text для корректной работы кнопок
        await callback_query.message.edit_text(
            users_text,
            reply_markup=back_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка показа пользователей: {e}")
        await callback_query.answer("❌ Ошибка загрузки данных", show_alert=True)

async def show_analytics(callback_query: types.CallbackQuery):
    """Показывает аналитику"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect(admin_panel.db_path)
        cursor = conn.cursor()
        
        # Статистика за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute("SELECT COUNT(*) FROM user_requests WHERE timestamp > ?", (week_ago,))
        requests_week = cursor.fetchone()[0]
        
        # Популярные типы запросов
        cursor.execute("""
            SELECT request_type, COUNT(*) as count 
            FROM user_requests 
            GROUP BY request_type 
            ORDER BY count DESC 
            LIMIT 5
        """)
        popular_types = cursor.fetchall()
        
        conn.close()
        
        analytics_text = f"""📊 <b>АНАЛИТИКА СИСТЕМЫ</b>

📈 <b>АКТИВНОСТЬ:</b>
• Запросов за неделю: {requests_week}
• Среднее в день: {requests_week // 7}

🔥 <b>ПОПУЛЯРНЫЕ ТИПЫ ЗАПРОСОВ:</b>
"""
        
        for i, (req_type, count) in enumerate(popular_types, 1):
            analytics_text += f"{i}. {req_type}: {count} раз\n"
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
        ])
        
        # Используем edit_text для корректной работы кнопок
        await callback_query.message.edit_text(
            analytics_text,
            reply_markup=back_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка показа аналитики: {e}")
        await callback_query.answer("❌ Ошибка загрузки аналитики", show_alert=True)

async def show_requests_list(callback_query: types.CallbackQuery):
    """Показывает последние запросы"""
    try:
        import sqlite3
        conn = sqlite3.connect(admin_panel.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ur.timestamp, u.first_name, u.username, ur.request_type, ur.request_text
            FROM user_requests ur
            JOIN users u ON ur.user_id = u.user_id
            ORDER BY ur.timestamp DESC
            LIMIT 10
        """)
        requests = cursor.fetchall()
        conn.close()
        
        if not requests:
            await callback_query.message.edit_text(
                "📝 <b>ЗАПРОСЫ</b>\n\nЗапросы не найдены.",
                parse_mode='HTML'
            )
            return
        
        requests_text = "📝 <b>ПОСЛЕДНИЕ 10 ЗАПРОСОВ:</b>\n\n"
        
        for timestamp, first_name, username, req_type, req_text in requests:
            name = first_name or username or "Неизвестный"
            # Проверяем req_text на None и пустые значения
            if req_text is None:
                short_text = "Нет текста запроса"
            elif len(req_text) > 50:
                short_text = req_text[:50] + "..."
            else:
                short_text = req_text
            requests_text += f"🕐 {timestamp[:16]}\n"
            requests_text += f"👤 <b>{name}</b>\n"
            requests_text += f"📋 Тип: {req_type or 'Неизвестный'}\n"
            requests_text += f"💬 {short_text}\n\n"
        
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
        ])
        
        # Используем edit_text для корректной работы кнопок
        await callback_query.message.edit_text(
            requests_text,
            reply_markup=back_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка показа запросов: {e}")
        await callback_query.answer("❌ Ошибка загрузки запросов", show_alert=True)

async def show_export_options(callback_query: types.CallbackQuery):
    """Показывает опции экспорта"""
    export_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Экспорт пользователей", callback_data="export_users")],
        [InlineKeyboardButton(text="📝 Экспорт запросов", callback_data="export_requests")],
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
    ])
    
    await callback_query.message.edit_text(
        "💾 <b>ЭКСПОРТ ДАННЫХ</b>\n\nВыберите что экспортировать:",
        reply_markup=export_keyboard,
        parse_mode='HTML'
    )

# Обработчики экспорта данных
@dp.callback_query(F.data.startswith("export_"))
async def process_export(callback_query: types.CallbackQuery):
    """Обработчик экспорта данных"""
    if not admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    export_type = callback_query.data.split("_")[1]
    
    try:
        await callback_query.answer("⏳ Создаю экспорт...")
        
        if export_type == "users":
            await export_users_data(callback_query)
        elif export_type == "requests":
            await export_requests_data(callback_query)
            
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта: {e}")
        await callback_query.answer("❌ Ошибка экспорта данных", show_alert=True)

async def export_users_data(callback_query: types.CallbackQuery):
    """Экспорт данных пользователей в CSV"""
    try:
        import sqlite3
        import csv
        from datetime import datetime
        
        conn = sqlite3.connect(admin_panel.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, first_name, last_name, 
                   registration_date, last_activity, total_requests
            FROM users 
            ORDER BY total_requests DESC
        """)
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
            ])
            await callback_query.message.edit_text(
                "❌ Нет данных для экспорта",
                reply_markup=back_keyboard,
                parse_mode='HTML'
            )
            return
        
        # Создаем CSV файл
        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID пользователя', 'Username', 'Имя', 'Фамилия', 
                           'Дата регистрации', 'Последняя активность', 'Всего запросов'])
            
            for user in users:
                writer.writerow(user)
        
        # Отправляем файл
        await callback_query.message.answer_document(
            FSInputFile(filename),
            caption=f"📊 <b>Экспорт пользователей</b>\n\n"
                   f"📈 Всего записей: {len(users)}\n"
                   f"📅 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Удаляем временный файл
        try:
            os.remove(filename)
        except Exception:
            pass
            
        # Возвращаемся к админ-панели через кнопку назад
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
        ])
        
        # Редактируем сообщение с результатом экспорта
        await callback_query.message.edit_text(
            "✅ Экспорт пользователей выполнен успешно!",
            reply_markup=back_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта пользователей: {e}")
        await callback_query.answer("❌ Ошибка создания экспорта", show_alert=True)

async def export_requests_data(callback_query: types.CallbackQuery):
    """Экспорт данных запросов в CSV"""
    try:
        import sqlite3
        import csv
        from datetime import datetime
        
        conn = sqlite3.connect(admin_panel.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ur.timestamp, u.first_name, u.username, ur.request_type, 
                   ur.request_text, ur.processing_time, ur.status
            FROM user_requests ur
            JOIN users u ON ur.user_id = u.user_id
            ORDER BY ur.timestamp DESC
            LIMIT 1000
        """)
        requests = cursor.fetchall()
        conn.close()
        
        if not requests:
            back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
            ])
            await callback_query.message.edit_text(
                "❌ Нет данных для экспорта",
                reply_markup=back_keyboard,
                parse_mode='HTML'  
            )
            return
        
        # Создаем CSV файл
        filename = f"requests_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Дата и время', 'Имя пользователя', 'Username', 
                           'Тип запроса', 'Текст запроса', 'Время обработки', 'Статус'])
            
            for request in requests:
                writer.writerow(request)
        
        # Отправляем файл
        await callback_query.message.answer_document(
            FSInputFile(filename),
            caption=f"📊 <b>Экспорт запросов</b>\n\n"
                   f"📈 Всего записей: {len(requests)}\n"
                   f"📅 Создан: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Удаляем временный файл
        try:
            os.remove(filename)
        except Exception:
            pass
            
        # Возвращаемся к админ-панели через кнопку назад
        back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_back")]
        ])
        
        # Редактируем сообщение с результатом экспорта
        await callback_query.message.edit_text(
            "✅ Экспорт запросов выполнен успешно!",
            reply_markup=back_keyboard,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта запросов: {e}")
        await callback_query.answer("❌ Ошибка создания экспорта", show_alert=True)

async def admin_back(callback_query: types.CallbackQuery):
    """Возврат в админ-панель"""
    try:
        logger.info("🔄 Возврат в админ-панель - начало")
        
        # Сначала отвечаем на callback чтобы убрать индикатор загрузки
        await callback_query.answer()
        
        logger.info("📊 Получение статистики...")
        # Получаем статистику с таймаутом
        try:
            stats = await get_admin_statistics()
            logger.info("✅ Статистика получена")
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            stats = {
                'total_users': 0,
                'active_today': 0,
                'requests_today': 0,
                'top_user': "Ошибка загрузки"
            }
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_analytics")],
            [InlineKeyboardButton(text="📝 Запросы", callback_data="admin_requests")],
            [InlineKeyboardButton(text="💾 Экспорт данных", callback_data="admin_export")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ])
        
        logger.info("📝 Обновление сообщения...")
        await callback_query.message.edit_text(
            f"""🛠️ <b>АДМИН-ПАНЕЛЬ "Виртуальный юрист"</b>

📊 <b>СТАТИСТИКА:</b>
👥 Всего пользователей: {stats['total_users']}
🔥 Активных за день: {stats['active_today']}
📝 Запросов сегодня: {stats['requests_today']}
⭐ Топ пользователь: {stats['top_user']}

🎯 <b>ДЕЙСТВИЯ:</b>
Выберите нужную функцию ниже""",
            reply_markup=admin_keyboard,
            parse_mode='HTML'
        )
        logger.info("✅ Админ-панель обновлена")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в admin_back: {e}")
        try:
            await callback_query.answer("❌ Ошибка загрузки админ-панели", show_alert=True)
        except Exception:
            pass

# Обработчик неизвестных команд
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "❓ Не понимаю вашу команду. Используйте кнопки меню для взаимодействия с ботом.",
        reply_markup=get_main_keyboard()
    )

# Основная функция
async def main():
    logger.info("Запуск бота Виртуальный юрист")
    
    try:
        # Проверяем конфигурацию
        Config.validate()
        
        # Устанавливаем команды бота
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Запустить бота"),
            types.BotCommand(command="admin", description="Админ-панель (только для администраторов)")
        ])
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 