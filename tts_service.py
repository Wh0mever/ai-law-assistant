"""
TTS (Text-to-Speech) сервис для генерации голосовых ответов
Использует OpenAI TTS API (tts-1-hd-1106) для конвертации текста в голос
"""

import os
import io
import tempfile
import logging
from typing import Optional, BinaryIO
from openai import OpenAI

# Безопасный импорт pydub с обработкой ошибок
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError as e:
    PYDUB_AVAILABLE = False
    AudioSegment = None
    print(f"⚠️ pydub недоступен: {e}")
    print("💡 Для полной функциональности TTS установите: pip install pydub")

logger = logging.getLogger(__name__)

class TTSService:
    """Сервис для генерации голосовых ответов через OpenAI TTS API"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "tts-1-hd"  # Высококачественная модель TTS
        self.voice = "alloy"     # Голос по умолчанию (можно изменить на nova, echo, fable, onyx, shimmer)
        
    async def text_to_speech(self, text: str, max_length: int = 4000) -> Optional[bytes]:
        """
        Конвертирует текст в голосовое сообщение (OGG формат для Telegram)
        
        Args:
            text: Текст для озвучивания
            max_length: Максимальная длина текста (TTS API ограничение)
            
        Returns:
            bytes: Аудио в формате OGG или None при ошибке
        """
        try:
            # Проверяем длину текста
            if not text or not text.strip():
                logger.warning("⚠️ Пустой текст для TTS")
                return None
                
            # Очищаем текст от HTML тегов и длинных частей
            clean_text = self._clean_text_for_tts(text, max_length)
            
            if len(clean_text) == 0:
                logger.warning("⚠️ Текст стал пустым после очистки")
                return None
                
            logger.info(f"🎤 Генерирую голосовое сообщение (длина: {len(clean_text)} символов)")
            
            # Генерируем речь через OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=clean_text,
                speed=1.0  # Нормальная скорость речи
            )
            
            # Получаем MP3 данные
            mp3_data = response.content
            logger.info(f"✅ TTS API ответил, размер MP3: {len(mp3_data)} байт")
            
            # Конвертируем MP3 в OGG для Telegram
            ogg_data = self._convert_mp3_to_ogg(mp3_data)
            
            if ogg_data:
                logger.info(f"✅ Конвертация в OGG завершена, размер: {len(ogg_data)} байт")
                return ogg_data
            else:
                logger.error("❌ Не удалось конвертировать MP3 в OGG")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации TTS: {e}")
            
            # Проверяем типы ошибок
            if "insufficient_quota" in str(e) or "429" in str(e):
                logger.error("❌ Превышена квота OpenAI API для TTS")
            elif "invalid_request_error" in str(e):
                logger.error("❌ Неверный запрос к TTS API")
            
            return None
    
    def _clean_text_for_tts(self, text: str, max_length: int) -> str:
        """
        Очищает и сокращает текст для TTS API
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина
        
        Returns:
            str: Очищенный текст
        """
        try:
            import re
            
            # Удаляем HTML теги
            clean_text = re.sub(r'<[^>]+>', '', text)
            
            # Удаляем специальные символы и форматирование
            clean_text = re.sub(r'[📄📋🔍⚖️🏛️📊📎📖✅❌⚠️💡🎯🔗📥📱🎤]', '', clean_text)
            
            # Удаляем повторяющиеся пробелы и переносы строк
            clean_text = re.sub(r'\n+', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            
            # Удаляем технические части (ссылки, метаданные)
            lines = clean_text.split('\n')
            filtered_lines = []
            
            for line in lines:
                line = line.strip()
                # Пропускаем технические строки
                if any(skip in line.lower() for skip in [
                    'источник:', 'ссылка:', 'релевантность:', 'найдено:',
                    'документ предоставлен', 'консультантплюс', '==='
                ]):
                    continue
                    
                if line and len(line) > 10:  # Только содержательные строки
                    filtered_lines.append(line)
            
            clean_text = ' '.join(filtered_lines)
            
            # Обрезаем до максимальной длины
            if len(clean_text) > max_length:
                # Находим ближайший конец предложения
                truncated = clean_text[:max_length]
                last_period = truncated.rfind('.')
                last_exclamation = truncated.rfind('!')
                last_question = truncated.rfind('?')
                
                end_pos = max(last_period, last_exclamation, last_question)
                
                if end_pos > max_length // 2:  # Если нашли разумное место для обрезки
                    clean_text = truncated[:end_pos + 1]
                else:
                    clean_text = truncated + "..."
            
            # Финальная очистка
            clean_text = clean_text.strip()
            
            logger.info(f"🧹 Текст очищен: {len(text)} → {len(clean_text)} символов")
            return clean_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки текста: {e}")
            # Возвращаем обрезанный исходный текст как fallback
            return text[:max_length] if len(text) > max_length else text
    
    def _convert_mp3_to_ogg(self, mp3_data: bytes) -> Optional[bytes]:
        """
        Конвертирует MP3 в OGG формат для Telegram
        
        Args:
            mp3_data: MP3 данные в байтах
            
        Returns:
            bytes: OGG данные или None при ошибке
        """
        # Проверяем доступность pydub
        if not PYDUB_AVAILABLE:
            logger.warning("⚠️ pydub недоступен, возвращаем MP3 данные как есть")
            logger.info("💡 Telegram может принять MP3, но OGG предпочтительнее")
            return mp3_data  # Возвращаем MP3 как fallback
        
        try:
            # Создаем временные файлы
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_temp:
                mp3_temp.write(mp3_data)
                mp3_temp_path = mp3_temp.name
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as ogg_temp:
                ogg_temp_path = ogg_temp.name
            
            try:
                # Загружаем MP3 и конвертируем в OGG
                audio = AudioSegment.from_mp3(mp3_temp_path)
                
                # Экспортируем в OGG формат (Opus кодек для Telegram)
                audio.export(
                    ogg_temp_path, 
                    format="ogg",
                    codec="libopus",
                    parameters=["-ar", "48000", "-ac", "1"]  # 48kHz моно для оптимального размера
                )
                
                # Читаем результат
                with open(ogg_temp_path, 'rb') as ogg_file:
                    ogg_data = ogg_file.read()
                
                logger.info(f"🔄 Конвертация MP3→OGG: {len(mp3_data)} → {len(ogg_data)} байт")
                return ogg_data
                
            finally:
                # Удаляем временные файлы
                try:
                    os.unlink(mp3_temp_path)
                    os.unlink(ogg_temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Не удалось удалить временные файлы: {cleanup_error}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации MP3→OGG: {e}")
            
            # Проверяем наличие pydub и ffmpeg
            if "ffmpeg" in str(e).lower():
                logger.error("❌ FFmpeg не найден. Установите FFmpeg для конвертации аудио")
                logger.info("💡 Возвращаю MP3 данные без конвертации")
                return mp3_data  # Fallback к MP3
            elif "pydub" in str(e).lower() or "audioread" in str(e).lower():
                logger.error("❌ Ошибка pydub. Проверьте установку: pip install pydub")
                logger.info("💡 Возвращаю MP3 данные без конвертации") 
                return mp3_data  # Fallback к MP3
                
            logger.warning("⚠️ Неизвестная ошибка конвертации, возвращаю MP3")
            return mp3_data  # Fallback к MP3
    
    def set_voice(self, voice: str):
        """
        Устанавливает голос для TTS
        
        Args:
            voice: Имя голоса (alloy, echo, fable, onyx, nova, shimmer)
        """
        available_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        
        if voice in available_voices:
            self.voice = voice
            logger.info(f"🎵 Голос TTS изменен на: {voice}")
        else:
            logger.warning(f"⚠️ Неизвестный голос: {voice}. Доступные: {available_voices}")
    
    def get_voice_info(self) -> dict:
        """Возвращает информацию о текущих настройках TTS"""
        return {
            "model": self.model,
            "voice": self.voice,
            "available_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        } 