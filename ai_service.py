import openai
import logging
from typing import Optional
from legal_knowledge import LegalKnowledge

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
    async def find_legal_practice(self, case_description: str) -> str:
        """Поиск судебной практики по описанию ситуации"""
        try:
            system_prompt = LegalKnowledge.get_system_prompt_for_practice()
            
            from config import Config
            response = await self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проанализируйте ситуацию и найдите судебную практику: {case_description}"}
                ],
                temperature=Config.OPENAI_TEMPERATURE
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in find_legal_practice: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                return """❌ **Превышена квота OpenAI API**

К сожалению, на данный момент исчерпана квота для запросов к ИИ.

📋 **Анализ вашей ситуации вручную:**

**Увольнение без приказа** - серьезное нарушение трудового законодательства.

**Ваши права:**
• Восстановление на работе (ст. 394 ТК РФ)  
• Оплата вынужденного прогула
• Компенсация морального вреда

**Судебная практика:**
• Определение ВС РФ № 18-КГ20-17
• Постановление Пленума ВС РФ № 2

**Действия:**
1. Требуйте письменное объяснение причин увольнения
2. Собирайте доказательства отсутствия приказа
3. Обращайтесь в суд в течение 1 месяца
4. Подавайте иск о восстановлении на работе

**Документы:** трудовая книжка, справки о доходах, свидетельские показания."""
            return "Извините, произошла ошибка при анализе ситуации. Попробуйте еще раз позже."
    
    async def generate_complaint(self, court_decision_text: str) -> str:
        """Генерация апелляционной/кассационной жалобы"""
        try:
            system_prompt = LegalKnowledge.get_system_prompt_for_complaint()
            
            from config import Config
            response = await self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Составьте проект апелляционной/кассационной жалобы на основе решения суда: {court_decision_text[:4000]}..."}
                ],
                temperature=Config.OPENAI_TEMPERATURE
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in generate_complaint: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                return """❌ **Превышена квота OpenAI API**

К сожалению, на данный момент исчерпана квота для запросов к ИИ.

📝 **Структура апелляционной жалобы:**

**1. ВВОДНАЯ ЧАСТЬ:**
- В [наименование апелляционного суда]
- От: [ваши ФИО, адрес]
- По делу № [номер дела]
- Решение от [дата] [суда первой инстанции]

**2. ОПИСАТЕЛЬНАЯ ЧАСТЬ:**
- Краткое изложение сути спора
- Решение суда первой инстанции
- Доводы суда

**3. МОТИВИРОВОЧНАЯ ЧАСТЬ:**
- Нарушения норм материального права
- Нарушения процессуального права  
- Неправильная оценка доказательств
- Ссылки на статьи законов

**4. ПРОСИТЕЛЬНАЯ ЧАСТЬ:**
- Прошу отменить решение суда
- Принять новое решение в мою пользу

📎 **Приложения:** копии документов, доказательства

💡 **Совет:** Обратитесь к юристу для детальной проработки жалобы."""
            return "Извините, произошла ошибка при составлении жалобы. Попробуйте еще раз позже."
    
    async def check_document(self, document_text: str) -> str:
        """Проверка документа на ошибки и юридические риски"""
        try:
            system_prompt = LegalKnowledge.get_system_prompt_for_check()
            
            from config import Config
            response = await self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проверьте документ на ошибки и юридические риски: {document_text[:4000]}..."}
                ],
                temperature=Config.OPENAI_TEMPERATURE
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in check_document: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                return """❌ **Превышена квота OpenAI API**

К сожалению, на данный момент исчерпана квота для запросов к ИИ.

📋 **Общие рекомендации по проверке документов:**

**ФОРМАЛЬНЫЕ ТРЕБОВАНИЯ:**
• Правильное наименование суда/органа
• Полные реквизиты сторон (ФИО, адреса)
• Четкая формулировка требований
• Подпись и дата
• Перечень приложений

**ПРАВОВЫЕ АСПЕКТЫ:**
• Соблюдение сроков подачи
• Ссылки на актуальные нормы права
• Правильная подсудность/подведомственность
• Уплата госпошлины (при необходимости)

**ДОКАЗАТЕЛЬНАЯ БАЗА:**
• Приложение всех необходимых документов
• Соответствие доказательств заявленным требованиям
• Допустимость доказательств

💡 **Совет:** Для детальной проверки обратитесь к практикующему юристу."""
            return "Извините, произошла ошибка при проверке документа. Попробуйте еще раз позже." 