"""
Сервис для работы с Perplexity API
Заменяет embeddings и веб-поиск точным поиском через интернет
"""

import requests
import logging
import json
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class PerplexityService:
    """Сервис для поиска актуальной юридической информации через Perplexity API"""
    
    def __init__(self):
        self.api_key = Config.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"
        
        # Модели Perplexity (актуальные с января 2025)
        self.model = "sonar"  # Быстрая модель с доступом в интернет
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info("✅ Perplexity API сервис инициализирован")
    
    async def search_legal_info(self, query: str, context_type: str = "general") -> str:
        """
        Поиск юридической информации через Perplexity API
        
        Args:
            query: Поисковый запрос
            context_type: Тип контекста ("bankruptcy", "labor", "civil", "general")
            
        Returns:
            Актуальная информация из интернета
        """
        try:
            # Формируем системный промпт для юридического поиска
            system_prompt = self._get_legal_system_prompt(context_type)
            
            # Улучшаем запрос для юридического поиска
            enhanced_query = self._enhance_legal_query(query, context_type)
            
            # Отправляем запрос к Perplexity API
            response = await self._make_request(system_prompt, enhanced_query)
            
            if response:
                return self._format_legal_response(response, context_type)
            else:
                return self._get_fallback_response(query, context_type)
                
        except Exception as e:
            logger.error(f"❌ Ошибка Perplexity API: {e}")
            return self._get_error_response(query, context_type)
    
    def _get_legal_system_prompt(self, context_type: str) -> str:
        """Системный промпт для юридических запросов"""
        base_prompt = """Ты - эксперт по российскому праву. Найди актуальную информацию по запросу пользователя.

ТРЕБОВАНИЯ:
1. Ищи только АКТУАЛЬНУЮ информацию на 2025 год
2. Используй только РОССИЙСКИЕ правовые источники
3. ОБЯЗАТЕЛЬНО указывай КОНКРЕТНЫЕ СТАТЬИ ЗАКОНОВ
4. ОБЯЗАТЕЛЬНО давай ССЫЛКИ НА ИСТОЧНИКИ (https://...)
5. Приводи СУДЕБНУЮ ПРАКТИКУ с номерами дел
6. Указывай КОНКРЕТНЫЕ суммы, сроки, процедуры

ПРИОРИТЕТНЫЕ ИСТОЧНИКИ:
- consultant.ru (КонсультантПлюс)
- garant.ru (Гарант)
- vsrf.ru (Верховный Суд РФ)
- ksrf.ru (Конституционный Суд РФ)
- pravo.gov.ru (Официальный интернет-портал правовой информации)
- Федеральные законы и кодексы РФ
- Постановления Пленумов ВС РФ

ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ОТВЕТА:
🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:

1. **КЛЮЧЕВЫЕ СТАТЬИ ЗАКОНОВ:**
   • **Статья X ТК РФ** - [описание]
   • **Статья Y ГК РФ** - [описание]
   • [другие статьи]

2. **ПОШАГОВЫЕ ДЕЙСТВИЯ:**
   • **Шаг 1:** [конкретное действие]
   • **Шаг 2:** [конкретное действие]
   • [другие шаги]

3. **СРОКИ И ДОКУМЕНТЫ:**
   • **Срок:** [точный срок]
   • **Документы:** [список документов]

4. **СУДЕБНАЯ ПРАКТИКА:**
   • **Решение ВС РФ** от [дата] № [номер]
   • [другие решения]

5. **ИСТОЧНИКИ ИНФОРМАЦИИ:**
   • https://[ссылка на источник 1]
   • https://[ссылка на источник 2]
   • [другие ссылки]

ВАЖНО: Используй **жирный текст** для заголовков и ключевых терминов. ВСЕГДА давай КОНКРЕТНЫЕ статьи законов и РЕАЛЬНЫЕ ссылки на источники!"""

        if context_type == "bankruptcy":
            return base_prompt + """

СПЕЦИАЛИЗАЦИЯ: БАНКРОТСТВО
Фокусируйся на:
- Федеральном законе 127-ФЗ "О несостоятельности (банкротстве)" 2025
- Внесудебном банкротстве (ххх тыс - ххх рублей)
- Судебном банкротстве (от ххх тыс рублей)
- Актуальной практике арбитражных судов 2025 года
- Процедурах в МФЦ для внесудебного банкротства"""

        elif context_type == "labor":
            return base_prompt + """

СПЕЦИАЛИЗАЦИЯ: ТРУДОВОЕ ПРАВО
Фокусируйся на:
- Трудовом кодексе РФ
- Постановлениях Пленума ВС РФ по трудовым спорам
- Трудовой инспекции и её полномочиях
- Сроках обращения в суд (1 месяц для восстановления)
- Размерах компенсаций и выплат"""

        elif context_type == "civil":
            return base_prompt + """

СПЕЦИАЛИЗАЦИЯ: ГРАЖДАНСКОЕ ПРАВО
Фокусируйся на:
- Гражданском кодексе РФ
- Договорном праве
- Защите прав потребителей
- Возмещении ущерба
- Сроках исковой давности (3 года общий)"""

        return base_prompt
    
    def _enhance_legal_query(self, query: str, context_type: str) -> str:
        """Улучшает запрос для юридического поиска"""
        # Базовые юридические термины для поиска
        legal_terms = "российское право законодательство РФ 2025"
        
        enhanced_query = f"{query} {legal_terms}"
        
        if context_type == "bankruptcy":
            enhanced_query += " банкротство несостоятельность 127-ФЗ арбитражный суд"
        elif context_type == "labor":
            enhanced_query += " трудовой кодекс трудовые права трудовая инспекция"
        elif context_type == "civil":
            enhanced_query += " гражданский кодекс гражданские права договор"
        
        return enhanced_query
    
    async def _make_request(self, system_prompt: str, query: str) -> Optional[str]:
        """Отправляет запрос к Perplexity API"""
        try:
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.1,  # Низкая температура для точности
                "max_tokens": 4000,
                "stream": False
            }
            
            logger.info(f"🌐 Отправляю запрос к Perplexity API: {query[:50]}...")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=45  # Увеличен таймаут для интернет-поиска
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Проверяем структуру ответа
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    logger.info("✅ Получен ответ от Perplexity API")
                    
                    # Добавляем информацию об источниках если есть
                    if 'search_results' in result:
                        logger.info(f"📚 Найдено {len(result['search_results'])} источников")
                    
                    return content
                else:
                    logger.error("❌ Неожиданная структура ответа от Perplexity API")
                    return None
                    
            elif response.status_code == 400:
                logger.error(f"❌ Неправильный запрос к Perplexity API: {response.text}")
                return None
            elif response.status_code == 401:
                logger.error("❌ Неверный API ключ Perplexity")
                return None
            elif response.status_code == 429:
                logger.error("❌ Превышен лимит запросов Perplexity API")
                return None
            else:
                logger.error(f"❌ Ошибка Perplexity API: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут запроса к Perplexity API")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ошибка соединения с Perplexity API")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка запроса к Perplexity: {e}")
            return None
    
    def _format_legal_response(self, response: str, context_type: str) -> str:
        """Форматирует ответ для юридического контекста"""
        # Конвертируем Markdown жирный текст в HTML
        response = self._convert_markdown_to_html(response)
        
        # Если ответ уже правильно отформатирован, возвращаем как есть
        if "🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:" in response:
            # Добавляем предупреждение в конец, если его нет
            if "⚠️ ВАЖНО:" not in response:
                response += "\n\n⚠️ ВАЖНО: Информация получена из интернета и требует проверки у практикующего юриста."
            return response
        
        # Иначе добавляем заголовок
        formatted_response = f"🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:\n\n{response}"
        
        # Добавляем предупреждение
        formatted_response += "\n\n⚠️ ВАЖНО: Информация получена из интернета и требует проверки у практикующего юриста."
        
        return formatted_response
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Конвертирует Markdown жирный текст в HTML для Telegram"""
        import re
        
        # Конвертируем **текст** в <b>текст</b>
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Конвертируем __текст__ в <b>текст</b> (альтернативный синтаксис)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
        
        # Конвертируем *текст* в <i>текст</i> (курсив)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        # Конвертируем _текст_ в <i>текст</i> (альтернативный курсив)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
        
        return text
    
    def _get_fallback_response(self, query: str, context_type: str) -> str:
        """Резервный ответ при отсутствии результатов"""
        fallback_responses = {
            "bankruptcy": f"""🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:

По вопросу "{query}" рекомендуем:

💰 БАНКРОТСТВО ГРАЖДАН:
• До 1 млн рублей - внесудебное банкротство через МФЦ
• От 500 тыс рублей - судебное банкротство в арбитражном суде
• Минимум 25 тыс рублей для любой процедуры

📋 ДОКУМЕНТЫ:
• Паспорт и справка о доходах
• Справки о задолженностях
• Перечень имущества

⚠️ Точную консультацию получите у практикующего юриста по банкротству.""",

            "labor": f"""🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:

По вопросу "{query}" рекомендуем:

⚖️ ТРУДОВЫЕ ПРАВА:
• Обращение в трудовую инспекцию (бесплатно)
• Срок для восстановления на работе - 1 месяц
• Компенсация морального вреда - от 5 тыс рублей

📋 ДЕЙСТВИЯ:
• Письменное требование работодателю
• Жалоба в трудовую инспекцию
• Иск в суд при необходимости

⚠️ Точную консультацию получите у практикующего юриста по трудовому праву.""",

            "general": f"""🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:

По вопросу "{query}" рекомендуем:

📚 ИСТОЧНИКИ ПРАВА:
• КонсультантПлюс (consultant.ru)
• Гарант (garant.ru)
• Официальный портал (pravo.gov.ru)

📋 ОБЩИЕ РЕКОМЕНДАЦИИ:
• Изучите актуальное законодательство РФ
• Соберите все документы по делу
• Соблюдайте процессуальные сроки

⚠️ Для точной правовой оценки обратитесь к практикующему юристу."""
        }
        
        return fallback_responses.get(context_type, fallback_responses["general"])
    
    def _get_error_response(self, query: str, context_type: str) -> str:
        """Ответ при ошибке API"""
        error_responses = {
            "bankruptcy": f"""❌ ВРЕМЕННАЯ ОШИБКА ПОИСКА ПО БАНКРОТСТВУ

К сожалению, поиск актуальной информации по банкротству временно недоступен.

💰 ОБЩИЕ РЕКОМЕНДАЦИИ ПО БАНКРОТСТВУ:
• До 1 млн рублей - внесудебное банкротство через МФЦ
• От 500 тыс рублей - судебное банкротство в арбитражном суде
• Минимум 25 тыс рублей для любой процедуры

🏛️ ПОЛЕЗНЫЕ РЕСУРСЫ:
• Арбитражные суды РФ (vsrf.ru)
• Официальный сайт судов общей юрисдикции
• КонсультантПлюс для изучения 127-ФЗ

📞 Бесплатная юридическая консультация: @ZachitaPrava02""",

            "labor": f"""❌ ВРЕМЕННАЯ ОШИБКА ПОИСКА ПО ТРУДОВОМУ ПРАВУ

К сожалению, поиск актуальной информации по трудовым вопросам временно недоступен.

👔 ОБЩИЕ РЕКОМЕНДАЦИИ ПО ТРУДОВЫМ СПОРАМ:
• Обращение в трудовую инспекцию (бесплатно)
• Срок для восстановления на работе - 1 месяц
• Компенсация морального вреда - от 5 тыс рублей

🏛️ ПОЛЕЗНЫЕ РЕСУРСЫ:
• Трудовая инспекция (git.rostrud.gov.ru)
• Трудовой кодекс РФ в КонсультантПлюс
• Практика судов по трудовым спорам

📞 Бесплатная юридическая консультация: @ZachitaPrava02""",

            "general": f"""❌ ВРЕМЕННАЯ ОШИБКА ПОИСКА

К сожалению, поиск актуальной информации по запросу "{query}" временно недоступен.

💡 РЕКОМЕНДАЦИИ:
• Обратитесь к КонсультантПлюс (consultant.ru)
• Проверьте информацию на pravo.gov.ru
• Получите консультацию практикующего юриста

📞 Бесплатная юридическая консультация: @ZachitaPrava02"""
        }
        
        return error_responses.get(context_type, error_responses["general"])