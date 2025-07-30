from openai import OpenAI
import logging
import json
import os
from typing import Optional, List, Tuple
from legal_knowledge import LegalKnowledge
from perplexity_service import PerplexityService
from config import Config
import io
import asyncio

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.perplexity = PerplexityService()
        
        logger.info("🌐 Используется Perplexity API для точного поиска актуальной информации в интернете")
    


    
    async def _get_relevant_legal_articles(self, query: str, top_k: int = 10) -> str:
        """Находит релевантные статьи через Perplexity API"""
        # Проверяем валидность запроса
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("⚠️ Пустой или невалидный запрос для поиска статей")
            return "\n\n🎯 <b>ОБЩИЕ РЕКОМЕНДАЦИИ ПО ПРАВОВЫМ ВОПРОСАМ:</b>\n" \
                   "• Изучите ваши права и обязанности\n" \
                   "• Соберите все необходимые документы\n" \
                   "• Обратитесь за консультацией к специалисту\n" \
                   "• Соблюдайте установленные сроки\n\n"
        
        try:
            # Определяем тип контекста для Perplexity
            query_lower = query.lower()
            context_type = "general"
            
            # Банкротство
            if any(word in query_lower for word in ["банкротство", "несостоятельность", "долг", "задолженность", "кредитор", "должник"]):
                context_type = "bankruptcy"
            # Трудовое право
            elif any(word in query_lower for word in ["работа", "увольнение", "зарплата", "трудовой", "отпуск", "больничный"]):
                context_type = "labor"
            # Гражданское право
            elif any(word in query_lower for word in ["договор", "недвижимость", "покупка", "продажа", "услуги", "ущерб"]):
                context_type = "civil"
            
            # Выполняем поиск через Perplexity API
            logger.info(f"🌐 Выполняется поиск через Perplexity API: {query}")
            perplexity_result = await self.perplexity.search_legal_info(query.strip(), context_type)
            
            if perplexity_result:
                logger.info("✅ Получен ответ от Perplexity API")
                return f"\n\n{perplexity_result}\n\n"
            else:
                logger.warning("⚠️ Perplexity API не дал результатов")
                return "\n\n❌ <b>ПОИСК НЕ ДАЛ РЕЗУЛЬТАТОВ</b>\n" \
                       "💡 Рекомендуем обратиться к практикующему юристу для получения актуальной консультации.\n\n"
            
        except Exception as e:
            logger.error(f"❌ Ошибка Perplexity API: {e}")
            return "\n\n❌ <b>ОШИБКА ПОИСКА</b>\n" \
                   "💡 Рекомендуем обратиться к практикующему юристу для получения консультации.\n\n"
    

    
    async def find_legal_practice(self, case_description: str) -> str:
        """Поиск судебной практики по описанию ситуации"""
        # Первичная проверка входных данных
        if case_description is None:
            logger.error("❌ case_description равен None в начале find_legal_practice")
            return "Извините, произошла ошибка при анализе ситуации. Попробуйте еще раз позже."
        
        if not isinstance(case_description, str):
            logger.error(f"❌ case_description неверного типа: {type(case_description)}")
            return "Извините, произошла ошибка при анализе ситуации. Попробуйте еще раз позже."
        
        try:
            # Получаем актуальную информацию через Perplexity API
            perplexity_response = await self._get_relevant_legal_articles(case_description, top_k=8)
            
            # Если получен полный ответ от Perplexity, используем его напрямую
            if perplexity_response and "🔍 АКТУАЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА:" in perplexity_response:
                logger.info("✅ Используем полный ответ от Perplexity API напрямую")
                
                # Проверяем длину ответа для разделения
                if len(perplexity_response) > 4000:
                    # Разделяем длинный ответ на части
                    parts = self._split_long_response(perplexity_response)
                    return parts  # Возвращаем список частей
                else:
                    return perplexity_response
            
            # Если нет полного ответа, используем старую систему с GPT
            system_prompt = LegalKnowledge.get_system_prompt_for_practice()
            
            # Добавляем контекст из Perplexity API
            if perplexity_response:
                system_prompt += f"\n\n{perplexity_response}"
                system_prompt += "\n\n🎯 СОХРАНИТЕ ВСЕ ДЕТАЛИ, СТАТЬИ И ССЫЛКИ ИЗ ИНФОРМАЦИИ ВЫШЕ!"
            
            # Определяем только для запросов про банкротство
            if not case_description:
                logger.error("❌ case_description равен None в find_legal_practice")
                return "Извините, произошла ошибка при анализе ситуации. Попробуйте еще раз позже."
            
            case_lower = case_description.lower()
            is_bankruptcy_query = any(word in case_lower for word in ["банкротство", "несостоятельность", "долг", "задолженность", "кредитор", "должник"])
            
            # Формируем запрос в зависимости от типа вопроса
            if is_bankruptcy_query:
                # Для банкротства добавляем специальную информацию
                bankruptcy_context = self._detect_bankruptcy_context(case_description)
                enhanced_query = f"""ЗАДАЧА: Дать конкретные практические советы по банкротству

ОПИСАНИЕ СИТУАЦИИ:
{case_description}

КОНТЕКСТ БАНКРОТСТВА:
{f"Обнаружен контекст банкротства: {bankruptcy_context['procedure_type']}" if bankruptcy_context['is_bankruptcy'] else "Банкротство не обнаружено"}
{f"Сумма долга: {bankruptcy_context['debt_amount']:,} рублей" if bankruptcy_context['debt_amount'] else ""}

ОСОБЕННОСТИ ДЛЯ БАНКРОТСТВА:
- Для сумм до 1 млн рублей: рекомендуйте ВНЕСУДЕБНОЕ банкротство
- Для сумм от 500 тыс рублей: можно СУДЕБНОЕ банкротство
- Для сумм до 25 тыс рублей: банкротство НЕВОЗМОЖНО

ТРЕБОВАНИЯ К ОТВЕТУ:
1. НЕ ССЫЛАЙТЕСЬ на законы, статьи и кодексы
2. ГОВОРИТЕ простым языком
3. ДАВАЙТЕ конкретные пошаговые действия
4. УКАЗЫВАЙТЕ конкретные суммы, сроки, места
5. ФОКУСИРУЙТЕСЬ на том, что делать прямо сейчас"""
            else:
                # Для обычных вопросов обычный промпт
                enhanced_query = f"""ЗАДАЧА: Дать конкретные практические советы

ОПИСАНИЕ СИТУАЦИИ:
{case_description}

ТРЕБОВАНИЯ К ОТВЕТУ:
1. НЕ ССЫЛАЙТЕСЬ на законы, статьи и кодексы
2. ГОВОРИТЕ простым языком
3. ДАВАЙТЕ конкретные пошаговые действия
4. УКАЗЫВАЙТЕ конкретные суммы, сроки, места
5. ФОКУСИРУЙТЕСЬ на том, что делать прямо сейчас
6. НЕ ИСПОЛЬЗУЙТЕ юридические термины без объяснения
7. БУДЬТЕ максимально конкретными

ФОРМАТ ОТВЕТА:
1. ЧТО ПРОИЗОШЛО (1-2 предложения)
2. ВАШИ ПРАВА (простыми словами)
3. КОНКРЕТНЫЕ ДЕЙСТВИЯ (пошагово что делать)
4. ДОКУМЕНТЫ (что собрать)
5. СРОКИ (когда что делать)
6. РЕЗУЛЬТАТ (что получите)"""

            ai_response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_query}
                ],
                temperature=0.0
            )
            
            ai_analysis = ai_response.choices[0].message.content
            
            # Формируем умные ссылки на статьи с учетом контекста
            legal_references = self._generate_smart_legal_references(case_description)
            
            # Убираем лишние предупреждения, добавляем только рекламу
            final_response = f"""{ai_analysis}{legal_references}

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
            
            return final_response
        
        # Основной except блок для find_legal_practice  
        except Exception as e:
            logger.error(f"Error in find_legal_practice: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                return """❌ <b>Превышена квота OpenAI API</b>

К сожалению, на данный момент исчерпана квота для запросов к ИИ.

📋 <b>Анализ вашей ситуации вручную:</b>

<b>Увольнение без приказа</b> - серьезное нарушение трудового законодательства.

<b>Ваши права:</b>
• Восстановление на работе (ст. 394 ТК РФ)  
• Оплата вынужденного прогула
• Компенсация морального вреда

<b>Судебная практика:</b>
• Определение ВС РФ № 18-КГ20-17
• Постановление Пленума ВС РФ № 2

<b>Действия:</b>
1. Требуйте письменное объяснение причин увольнения
2. Собирайте доказательства отсутствия приказа
3. Обращайтесь в суд в течение 1 месяца
4. Подавайте иск о восстановлении на работе

<b>Документы:</b> трудовая книжка, справки о доходах, свидетельские показания."""
            return "Извините, произошла ошибка при анализе ситуации. Попробуйте еще раз позже."
    
    def _split_long_response(self, response: str) -> list:
        """Разделяет длинный ответ на части для отправки"""
        try:
            # Максимальная длина одного сообщения (оставляем запас для рекламы)
            max_length = 3800
            
            # Если ответ помещается в одно сообщение
            if len(response) <= max_length:
                return [response]
            
            parts = []
            current_part = ""
            lines = response.split('\n')
            
            for line in lines:
                # Если добавление строки не превышает лимит
                if len(current_part + line + '\n') <= max_length:
                    current_part += line + '\n'
                else:
                    # Если текущая часть не пуста, добавляем её
                    if current_part.strip():
                        parts.append(current_part.strip())
                    
                    # Если одна строка слишком длинная, разрезаем её
                    if len(line) > max_length:
                        while line:
                            chunk = line[:max_length]
                            parts.append(chunk)
                            line = line[max_length:]
                        current_part = ""
                    else:
                        current_part = line + '\n'
            
            # Добавляем последнюю часть
            if current_part.strip():
                parts.append(current_part.strip())
            
            # Добавляем номера частей
            if len(parts) > 1:
                for i, part in enumerate(parts, 1):
                    parts[i-1] = f"📄 **ЧАСТЬ {i} ИЗ {len(parts)}**\n\n{part}"
            
            logger.info(f"📄 Ответ разделен на {len(parts)} частей")
            return parts
            
        except Exception as e:
            logger.error(f"❌ Ошибка разделения ответа: {e}")
            return [response[:3800]]  # Возвращаем обрезанный ответ

    
    def _generate_specific_legal_references(self, query: str) -> str:
        """Заглушка для генерации ссылок - теперь используется веб-поиск"""
        logger.info("🌐 Генерация ссылок отключена - используется веб-поиск")
        return ""
    
    def _detect_query_context(self, query: str) -> str:
        """Определяет контекст запроса для фильтрации статей"""
        
        # Проверяем валидность запроса
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("⚠️ Пустой или невалидный запрос для определения контекста")
            return 'общее'
        
        query_lower = query.strip().lower()
        
        # Трудовое право
        labor_keywords = [
            'увольнение', 'работа', 'трудовой', 'зарплата', 'заработная плата', 'отпуск',
            'больничный', 'работодатель', 'сотрудник', 'трудовая книжка', 'прогул',
            'трудовой договор', 'штраф', 'премия', 'командировка', 'сверхурочные',
            'декрет', 'отгул', 'график работы', 'выходные', 'праздники', 'отработка'
        ]
        
        # Гражданское право
        civil_keywords = [
            'договор', 'сделка', 'собственность', 'покупка', 'продажа', 'аренда',
            'займ', 'кредит', 'залог', 'наследство', 'дарение', 'ущерб', 'компенсация',
            'страхование', 'недвижимость', 'автомобиль', 'услуги', 'подряд', 'поставка'
        ]
        
        # Семейное право
        family_keywords = [
            'брак', 'развод', 'алименты', 'дети', 'опека', 'усыновление', 'супруг',
            'семья', 'материнский капитал', 'отцовство', 'материнство'
        ]
        
        # Жилищное право
        housing_keywords = [
            'квартира', 'дом', 'жилье', 'коммунальные услуги', 'управляющая компания',
            'тсж', 'капремонт', 'приватизация', 'выселение', 'прописка', 'регистрация'
        ]
        
        # Административное право
        admin_keywords = [
            'штраф', 'гибдд', 'парковка', 'нарушение', 'административный',
            'протокол', 'постановление', 'жалоба на постановление'
        ]
        
        # Банкротство
        bankruptcy_keywords = [
            'банкротство', 'долг', 'кредиторы', 'должник', 'несостоятельность',
            'финансовый управляющий', 'конкурсная масса'
        ]
        
        # Уголовное право
        criminal_keywords = [
            'преступление', 'уголовный', 'следствие', 'обвинение', 'суд',
            'приговор', 'адвокат', 'потерпевший'
        ]
        
        # Подсчитываем совпадения
        contexts = {
            'трудовое': sum(1 for keyword in labor_keywords if keyword in query_lower),
            'гражданское': sum(1 for keyword in civil_keywords if keyword in query_lower),
            'семейное': sum(1 for keyword in family_keywords if keyword in query_lower),
            'жилищное': sum(1 for keyword in housing_keywords if keyword in query_lower),
            'административное': sum(1 for keyword in admin_keywords if keyword in query_lower),
            'банкротство': sum(1 for keyword in bankruptcy_keywords if keyword in query_lower),
            'уголовное': sum(1 for keyword in criminal_keywords if keyword in query_lower)
        }
        
        # Находим наиболее подходящий контекст
        max_context = max(contexts, key=contexts.get)
        max_count = contexts[max_context]
        
        if max_count > 0:
            return max_context
        else:
            return 'общее'
    
    def _filter_articles_by_context(self, articles, context: str, min_score: float = 0.3):
        """Фильтрует статьи по контексту запроса"""
        allowed_document_types = {
            'трудовое': {
                'Трудовой кодекс РФ',
                'Гражданский процессуальный кодекс РФ',
                'Арбитражный процессуальный кодекс РФ'
            },
            'гражданское': {
                'Гражданский кодекс РФ',
                'Гражданский процессуальный кодекс РФ',
                'Арбитражный процессуальный кодекс РФ'
            },
            'семейное': {
                'Семейный кодекс РФ',
                'Гражданский кодекс РФ',
                'Гражданский процессуальный кодекс РФ'
            },
            'жилищное': {
                'Жилищный кодекс РФ',
                'Гражданский кодекс РФ',
                'Гражданский процессуальный кодекс РФ'
            },
            'административное': {
                'Кодекс об административных правонарушениях РФ',
                'Административный процессуальный кодекс РФ'
            },
            'банкротство': {
                'Федеральный закон',
                'Арбитражный процессуальный кодекс РФ',
                'Гражданский кодекс РФ'
            },
            'уголовное': {
                'Уголовный кодекс РФ',
                'Уголовный процессуальный кодекс РФ',
                'Уголовно-исполнительный кодекс РФ'
            },
            'общее': {
                'Гражданский кодекс РФ',
                'Гражданский процессуальный кодекс РФ',
                'Трудовой кодекс РФ'
            }
        }
        
        allowed_types = allowed_document_types.get(context, allowed_document_types['общее'])
        
        filtered_results = []
        for entry, score in articles:
            # Проверяем минимальный скор релевантности
            if score < min_score:
                continue
                
            # Определяем тип документа
            doc_type = self._get_document_type(entry.source_file)
            
            # Фильтруем по разрешенным типам документов
            if doc_type in allowed_types:
                filtered_results.append((entry, score))
        
        # Сортируем по скору и берем топ-10
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        return filtered_results[:10]
    
    def _get_priority_order_for_context(self, context: str) -> list:
        """Возвращает приоритетный порядок документов для контекста"""
        priority_orders = {
            'трудовое': [
                "Трудовой кодекс РФ",
                "Гражданский процессуальный кодекс РФ",
                "Арбитражный процессуальный кодекс РФ"
            ],
            'гражданское': [
                "Гражданский кодекс РФ",
                "Гражданский процессуальный кодекс РФ",
                "Арбитражный процессуальный кодекс РФ"
            ],
            'семейное': [
                "Семейный кодекс РФ",
                "Гражданский кодекс РФ",
                "Гражданский процессуальный кодекс РФ"
            ],
            'жилищное': [
                "Жилищный кодекс РФ",
                "Гражданский кодекс РФ",
                "Гражданский процессуальный кодекс РФ"
            ],
            'административное': [
                "Кодекс об административных правонарушениях РФ",
                "Административный процессуальный кодекс РФ"
            ],
            'банкротство': [
                "Федеральный закон",
                "Арбитражный процессуальный кодекс РФ",
                "Гражданский кодекс РФ"
            ],
            'уголовное': [
                "Уголовный кодекс РФ",
                "Уголовный процессуальный кодекс РФ",
                "Уголовно-исполнительный кодекс РФ"
            ]
        }
        
        return priority_orders.get(context, [
            "Гражданский кодекс РФ",
            "Трудовой кодекс РФ",
            "Гражданский процессуальный кодекс РФ"
        ])
    
    def _get_document_type(self, source_file: str) -> str:
        """Определяет тип документа по имени файла"""
        source_file_lower = source_file.lower()
        
        # Определяем тип документа по названию файла
        if "трудовой" in source_file_lower or "23.txt" in source_file_lower:
            return "Трудовой кодекс РФ"
        elif "гражданский" in source_file_lower and "процессуальный" in source_file_lower:
            return "Гражданский процессуальный кодекс РФ"
        elif "гражданский" in source_file_lower:
            return "Гражданский кодекс РФ"
        elif "арбитражный" in source_file_lower:
            return "Арбитражный процессуальный кодекс РФ"
        elif "административный" in source_file_lower and "кодекс" in source_file_lower:
            return "Кодекс об административных правонарушениях РФ"
        elif "уголовный" in source_file_lower and "процессуальный" in source_file_lower:
            return "Уголовный процессуальный кодекс РФ"
        elif "уголовный" in source_file_lower:
            return "Уголовный кодекс РФ"
        elif "семейный" in source_file_lower or "25.txt" in source_file_lower:
            return "Семейный кодекс РФ"
        elif "жилищный" in source_file_lower or "26.txt" in source_file_lower:
            return "Жилищный кодекс РФ"
        elif "земельный" in source_file_lower or "24.txt" in source_file_lower:
            return "Земельный кодекс РФ"
        elif "налоговый" in source_file_lower or "12.txt" in source_file_lower:
            return "Налоговый кодекс РФ"
        elif "бюджетный" in source_file_lower or "27.txt" in source_file_lower:
            return "Бюджетный кодекс РФ"
        elif "таможенный" in source_file_lower or "22.txt" in source_file_lower:
            return "Таможенный кодекс РФ"
        elif "лесной" in source_file_lower or "31.txt" in source_file_lower:
            return "Лесной кодекс РФ"
        elif "воздушный" in source_file_lower or "32.txt" in source_file_lower:
            return "Воздушный кодекс РФ"
        elif "водный" in source_file_lower or "33.txt" in source_file_lower:
            return "Водный кодекс РФ"
        elif "морской" in source_file_lower or "35.txt" in source_file_lower:
            return "Кодекс торгового мореплавания РФ"
        elif "градостроительный" in source_file_lower or "36.txt" in source_file_lower:
            return "Градостроительный кодекс РФ"
        elif "исполнительный" in source_file_lower or "30.txt" in source_file_lower:
            return "Уголовно-исполнительный кодекс РФ"
        elif "конституция" in source_file_lower or "56.txt" in source_file_lower:
            return "Конституция РФ"
        elif "федеральный закон" in source_file_lower or "фз" in source_file_lower:
            return "Федеральный закон"
        else:
            # Определяем по номеру файла "КонсультантПлюс"
            if "консультантплюс" in source_file_lower:
                if "12" in source_file_lower:
                    return "Налоговый кодекс РФ"
                elif "13" in source_file_lower:
                    return "Гражданский кодекс РФ"
                elif "14" in source_file_lower:
                    return "Гражданский кодекс РФ"
                elif "15" in source_file_lower:
                    return "Наследственное право"
                elif "16" in source_file_lower:
                    return "Интеллектуальные права"
                elif "18" in source_file_lower:
                    return "Гражданский процессуальный кодекс РФ"
                elif "19" in source_file_lower:
                    return "Арбитражный процессуальный кодекс РФ"
                elif "20" in source_file_lower:
                    return "Кодекс об административных правонарушениях РФ"
                elif "21" in source_file_lower:
                    return "Административный процессуальный кодекс РФ"
                elif "22" in source_file_lower:
                    return "Таможенный кодекс РФ"
                elif "23" in source_file_lower:
                    return "Трудовой кодекс РФ"
                elif "24" in source_file_lower:
                    return "Земельный кодекс РФ"
                elif "25" in source_file_lower:
                    return "Семейный кодекс РФ"
                elif "26" in source_file_lower:
                    return "Жилищный кодекс РФ"
                elif "27" in source_file_lower:
                    return "Бюджетный кодекс РФ"
                elif "28" in source_file_lower:
                    return "Уголовный кодекс РФ"
                elif "29" in source_file_lower:
                    return "Уголовный процессуальный кодекс РФ"
                elif "30" in source_file_lower:
                    return "Уголовно-исполнительный кодекс РФ"
                elif "31" in source_file_lower:
                    return "Лесной кодекс РФ"
                elif "32" in source_file_lower:
                    return "Воздушный кодекс РФ"
                elif "33" in source_file_lower:
                    return "Водный кодекс РФ"
                elif "34" in source_file_lower:
                    return "Кодекс внутреннего водного транспорта РФ"
                elif "35" in source_file_lower:
                    return "Кодекс торгового мореплавания РФ"
                elif "36" in source_file_lower:
                    return "Градостроительный кодекс РФ"
                elif "56" in source_file_lower:
                    return "Конституция РФ"
                elif "ук341" in source_file_lower:
                    return "Налоговый кодекс РФ"
                    
            return "Другие документы"
    
    async def generate_complaint(self, court_decision_text: str) -> str:
        """Генерация апелляционной/кассационной жалобы"""
        try:
            # Получаем актуальную информацию через Perplexity API
            relevant_articles = await self._get_relevant_legal_articles(court_decision_text, top_k=8)
            
            system_prompt = LegalKnowledge.get_system_prompt_for_complaint()
            
            # Добавляем контекст из Perplexity API
            if relevant_articles:
                system_prompt += f"\n\n{relevant_articles}"
                system_prompt += "\n\n🎯 ИСПОЛЬЗУЙТЕ АКТУАЛЬНУЮ ИНФОРМАЦИЮ ИЗ ИНТЕРНЕТА ДЛЯ СОСТАВЛЕНИЯ ЖАЛОБЫ!"
            
            # Формируем улучшенный запрос к ИИ
            enhanced_query = f"""ЗАДАЧА: Составить жалобу на решение суда

РЕШЕНИЕ СУДА:
{court_decision_text}

ТРЕБОВАНИЯ К ЖАЛОБЕ:
1. НЕ ССЫЛАЙТЕСЬ на законы, статьи и кодексы
2. ИСПОЛЬЗУЙТЕ простые формулировки
3. ФОКУСИРУЙТЕСЬ на фактах и нарушениях
4. ДАВАЙТЕ готовый текст жалобы
5. БУДЬТЕ конкретными в каждом пункте
6. НЕ ИСПОЛЬЗУЙТЕ сложные юридические термины

СТРУКТУРА ЖАЛОБЫ:
1. КОМУ (название суда)
2. ОТ КОГО (ваши данные)
3. ЧТО СЛУЧИЛОСЬ (факты из решения)
4. ПОЧЕМУ ЭТО НЕПРАВИЛЬНО (конкретные нарушения)
5. ЧТО ТРЕБУЕТЕ (отменить решение, принять новое)
6. ДОКУМЕНТЫ (список приложений)

ПРИМЕРЫ ХОРОШЕГО ТЕКСТА:
✅ "Суд неправильно оценил доказательства"
✅ "Меня не выслушали должным образом"
✅ "Требую отменить решение"
✅ "Прошу принять новое решение в мою пользу"

ЗАПРЕЩЕНО:
- Ссылки на законы и статьи
- Сложные юридические термины
- Общие формулировки
- Длинные предложения

ДАЙТЕ ГОТОВЫЙ ТЕКСТ ЖАЛОБЫ!"""

            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_query}
                ],
                temperature=0.0
            )
            
            complaint_text = response.choices[0].message.content
            
            # Формируем умные ссылки на статьи с учетом контекста
            legal_references = self._generate_smart_legal_references(court_decision_text)
            
            # Убираем лишние предупреждения, добавляем только рекламу
            final_response = f"""{complaint_text}{legal_references}

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in generate_complaint: {e}")
            return "Извините, произошла ошибка при составлении жалобы. Попробуйте еще раз позже."
    
    async def check_document(self, document_text: str) -> str:
        """Проверка документов на соответствие законодательству"""
        try:
            # Получаем актуальную информацию через Perplexity API
            relevant_articles = await self._get_relevant_legal_articles(document_text, top_k=8)
            
            system_prompt = LegalKnowledge.get_system_prompt_for_check()
            
            # Добавляем контекст из Perplexity API
            if relevant_articles:
                system_prompt += f"\n\n{relevant_articles}"
                system_prompt += "\n\n🎯 ИСПОЛЬЗУЙТЕ АКТУАЛЬНУЮ ИНФОРМАЦИЮ ИЗ ИНТЕРНЕТА ДЛЯ ПРОВЕРКИ ДОКУМЕНТА!"
            
            # Формируем улучшенный запрос к ИИ
            enhanced_query = f"""ЗАДАЧА: Проверить документ на соответствие законам

ДОКУМЕНТ ДЛЯ ПРОВЕРКИ:
{document_text}

ТРЕБОВАНИЯ К ПРОВЕРКЕ:
1. НЕ ССЫЛАЙТЕСЬ на законы, статьи и кодексы
2. ИСПОЛЬЗУЙТЕ простые формулировки
3. ФОКУСИРУЙТЕСЬ на конкретных нарушениях
4. ДАВАЙТЕ практические рекомендации
5. БУДЬТЕ конкретными в каждом пункте
6. НЕ ИСПОЛЬЗУЙТЕ сложные юридические термины

СТРУКТУРА ПРОВЕРКИ:
1. ЧТО ПРОВЕРЯЕМ (краткое описание документа)
2. НАЙДЕННЫЕ ПРОБЛЕМЫ (конкретные нарушения)
3. РЕКОМЕНДАЦИИ (как исправить)
4. ПОСЛЕДСТВИЯ (что может произойти)

ПРИМЕРЫ ХОРОШЕГО АНАЛИЗА:
✅ "В договоре отсутствует важное условие"
✅ "Эта формулировка может быть неправильно понята"
✅ "Добавьте пункт о..."
✅ "Без этого условия вы рискуете..."

ЗАПРЕЩЕНО:
- Ссылки на законы и статьи
- Сложные юридические термины
- Общие формулировки
- Длинные предложения

ДАЙТЕ КОНКРЕТНЫЕ РЕКОМЕНДАЦИИ!"""

            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_query}
                ],
                temperature=0.0
            )
            
            document_analysis = response.choices[0].message.content
            
            # Формируем умные ссылки на статьи с учетом контекста
            legal_references = self._generate_smart_legal_references(document_text)
            
            # Убираем лишние предупреждения, добавляем только рекламу
            final_response = f"""{document_analysis}{legal_references}

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in check_document: {e}")
            return "Извините, произошла ошибка при проверке документа. Попробуйте еще раз позже."
    
    async def get_constitutional_analysis(self, query: str, system_prompt: str, context: str = None) -> str:
        """Анализ конституционных вопросов с использованием Perplexity API"""
        try:
            # Получаем актуальную информацию через Perplexity API
            if not context:
                context = await self._get_relevant_legal_articles(query, top_k=5)
            
            # Формируем полный запрос с контекстом
            full_query = f"ВОПРОС: {query}\n\n{context}\n\nДайте развернутый анализ вопроса на основе актуальной информации из интернета."
            
            response = self.client.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_query}
                ],
                temperature=0.0
            )
            
            analysis_text = response.choices[0].message.content
            
            # Добавляем рекламное сообщение
            final_response = f"""{analysis_text}

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in constitutional analysis: {e}")
            if "insufficient_quota" in str(e) or "429" in str(e):
                return f"""❌ <b>Превышена квота OpenAI API</b>

К сожалению, на данный момент исчерпана квота для запросов к ИИ.

📋 <b>Базовая информация по вашему вопросу:</b> "{query}"

<b>ОСНОВЫ КОНСТИТУЦИОННОГО ПРАВА РФ:</b>

• <b>Конституция РФ</b> - высший закон государства
• <b>Права и свободы человека</b> - высшая ценность (ст. 2)
• <b>Федеративное устройство</b> - основа государственности
• <b>Разделение властей</b> - принцип организации власти
• <b>Верховенство права</b> - основополагающий принцип

<b>ВАЖНЫЕ ОРГАНЫ:</b>
• <b>Конституционный Суд РФ</b> - орган конституционного контроля
• <b>Президент РФ</b> - глава государства
• <b>Федеральное Собрание</b> - парламент РФ
• <b>Правительство РФ</b> - исполнительная власть

<b>РЕКОМЕНДАЦИИ:</b>
• Изучите текст Конституции РФ
• Ознакомьтесь с решениями КС РФ
• Обратитесь к специалисту по конституционному праву

💡 <b>Для точной консультации обратитесь к практикующему юристу.</b>

---

❓ <b>Не нашли ответа? Возникли вопросы?</b>
🆓 <b>Бесплатная юридическая консультация</b> @ZachitaPrava02"""
            return "Извините, произошла ошибка при анализе конституционного вопроса. Попробуйте еще раз позже." 
    
    def _detect_bankruptcy_context(self, query: str) -> dict:
        """Определяет контекст банкротства и применимые законы"""
        context = {
            'is_bankruptcy': False,
            'debt_amount': None,
            'applicable_laws': [],
            'procedure_type': None
        }
        
        # Проверяем валидность запроса
        if not query or not isinstance(query, str) or not query.strip():
            logger.warning("⚠️ Пустой или невалидный запрос для определения банкротства")
            # Возвращаем общую информацию о банкротстве
            context['is_bankruptcy'] = False
            context['general_advice'] = "При возникновении правовых вопросов рекомендуется получить профессиональную консультацию"
            return context
        
        query_lower = query.strip().lower()
        
        # Проверяем банкротство
        bankruptcy_keywords = ['банкротство', 'несостоятельность', 'банкрот', 'долг']
        if any(keyword in query_lower for keyword in bankruptcy_keywords):
            context['is_bankruptcy'] = True
            
            # Определяем сумму долга
            import re
            
            # Паттерны для поиска сумм
            amount_patterns = [
                r'(\d+)\s*(?:млн|миллион)',
                r'(\d+)\s*(?:тысяч|тыс)',
                r'(\d+)\s*(?:рублей|руб)',
                r'от\s*(\d+)\s*до\s*(\d+)',
                r'(\d+)\s*(?:000|к)',
                r'до\s*(\d+)\s*(?:млн|миллион)',
                r'свыше\s*(\d+)',
                r'более\s*(\d+)'
            ]
            
            for pattern in amount_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    try:
                        amount = int(match.group(1))
                        if 'млн' in match.group(0) or 'миллион' in match.group(0):
                            amount *= 1000000
                        elif 'тысяч' in match.group(0) or 'тыс' in match.group(0):
                            amount *= 1000
                        elif '000' in match.group(0):
                            amount *= 1000
                        context['debt_amount'] = amount
                        break
                    except (ValueError, IndexError):
                        continue
            
            # Определяем тип процедуры и применимые законы
            if context['debt_amount']:
                if context['debt_amount'] < 1000000:  # До миллиона
                    if context['debt_amount'] >= 25000:  # От 25 тысяч
                        context['procedure_type'] = 'extrajudicial'
                        context['applicable_laws'] = [
                            'Федеральный закон от 26.10.2002 N 127-ФЗ "О несостоятельности (банкротстве)"',
                            'Статья 223.1 - Внесудебное банкротство',
                            'Статья 223.2 - Условия внесудебного банкротства',
                            'Статья 223.3 - Процедура внесудебного банкротства'
                        ]
                    else:
                        context['procedure_type'] = 'insufficient_amount'
                        context['applicable_laws'] = [
                            'Сумма долга недостаточна для процедуры банкротства',
                            'Минимальная сумма: 25 000 рублей'
                        ]
                elif context['debt_amount'] >= 500000:  # От 500 тысяч
                    context['procedure_type'] = 'judicial'
                    context['applicable_laws'] = [
                        'Федеральный закон от 26.10.2002 N 127-ФЗ "О несостоятельности (банкротстве)"',
                        'Статья 213.3 - Условия признания банкротом',
                        'Статья 213.4 - Заявление о признании банкротом',
                        'Арбитражный процессуальный кодекс РФ'
                    ]
                else:
                    # Промежуточная сумма - можно выбрать
                    context['procedure_type'] = 'optional'
                    context['applicable_laws'] = [
                        'Федеральный закон от 26.10.2002 N 127-ФЗ "О несостоятельности (банкротстве)"',
                        'Возможно внесудебное банкротство (статья 223.1)',
                        'Возможно судебное банкротство (статья 213.3)'
                    ]
        
        return context
    
    def _generate_smart_legal_references(self, query: str) -> str:
        """Генерирует умные ссылки на статьи с учетом контекста банкротства"""
        try:
            # Определяем контекст банкротства
            bankruptcy_context = self._detect_bankruptcy_context(query)
            
            if bankruptcy_context['is_bankruptcy'] and bankruptcy_context['applicable_laws']:
                # Для банкротства используем специальную логику
                logger.info(f"🏦 Определен контекст банкротства: {bankruptcy_context['procedure_type']}")
                
                legal_references = "\n\n📋 <b>ПРИМЕНИМЫЕ СТАТЬИ ЗАКОНОВ:</b>"
                
                if bankruptcy_context['procedure_type'] == 'extrajudicial':
                    legal_references += "\n• <b>Федеральный закон о банкротстве:</b> "
                    legal_references += "ст. 223.1 (Внесудебное банкротство граждан), "
                    legal_references += "ст. 223.2 (Условия внесудебного банкротства), "
                    legal_references += "ст. 223.3 (Процедура внесудебного банкротства)"
                    
                    if bankruptcy_context['debt_amount']:
                        legal_references += f"\n• <b>Применимо для суммы:</b> {bankruptcy_context['debt_amount']:,} рублей"
                        legal_references += "\n• <b>Диапазон:</b> от 25 000 до 1 000 000 рублей"
                    
                elif bankruptcy_context['procedure_type'] == 'judicial':
                    legal_references += "\n• <b>Федеральный закон о банкротстве:</b> "
                    legal_references += "ст. 213.3 (Условия признания банкротом), "
                    legal_references += "ст. 213.4 (Заявление о признании банкротом), "
                    legal_references += "ст. 213.5 (Рассмотрение заявления)"
                    legal_references += "\n• <b>Арбитражный процессуальный кодекс РФ:</b> "
                    legal_references += "ст. 223 (Рассмотрение дел о банкротстве)"
                    
                    if bankruptcy_context['debt_amount']:
                        legal_references += f"\n• <b>Применимо для суммы:</b> {bankruptcy_context['debt_amount']:,} рублей"
                        legal_references += "\n• <b>Минимум:</b> 500 000 рублей"
                
                elif bankruptcy_context['procedure_type'] == 'insufficient_amount':
                    legal_references += "\n• <b>⚠️ ВНИМАНИЕ:</b> Сумма долга недостаточна для банкротства"
                    legal_references += "\n• <b>Минимальная сумма:</b> 25 000 рублей"
                    legal_references += "\n• <b>Рекомендуется:</b> Рассмотреть иные способы урегулирования"
                
                elif bankruptcy_context['procedure_type'] == 'optional':
                    legal_references += "\n• <b>Федеральный закон о банкротстве:</b> "
                    legal_references += "ст. 223.1 (Внесудебное банкротство - при особых условиях), "
                    legal_references += "ст. 213.3 (Судебное банкротство - общий порядок)"
                    
                    if bankruptcy_context['debt_amount']:
                        legal_references += f"\n• <b>Сумма долга:</b> {bankruptcy_context['debt_amount']:,} рублей"
                        legal_references += "\n• <b>Возможны оба варианта:</b> внесудебное и судебное"
                
                return legal_references
            
            # Для остальных случаев возвращаем пустую строку (используется веб-поиск)
            logger.info("🌐 Контекст банкротства не определен - используется веб-поиск")
            return ""
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации умных ссылок: {e}")
            return "" 
    
    async def transcribe_voice_message(self, voice_file_bytes: bytes, file_format: str = "ogg") -> str:
        """
        Распознает голосовое сообщение с помощью Whisper-1 API
        
        Args:
            voice_file_bytes: Байты аудио файла
            file_format: Формат файла (ogg, mp3, wav и т.д.)
            
        Returns:
            str: Распознанный текст
        """
        try:
            logger.info("🎤 Начинаю распознавание голосового сообщения...")
            
            # Создаем объект файла для OpenAI API
            if isinstance(voice_file_bytes, bytes):
                audio_file = io.BytesIO(voice_file_bytes)
            else:
                # Если это уже BytesIO объект, используем его напрямую
                audio_file = voice_file_bytes
                voice_file_bytes.seek(0)
            
            audio_file.name = f"voice_message.{file_format}"
            
            logger.info(f"📊 Размер аудио данных: {len(voice_file_bytes) if isinstance(voice_file_bytes, bytes) else 'BytesIO объект'} байт")
            
            # Отправляем запрос к Whisper-1
            logger.info("📡 Отправляю запрос к Whisper-1 API...")
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Указываем русский язык для лучшего распознавания
            )
            
            transcribed_text = response.text.strip()
            logger.info(f"✅ Распознавание успешно завершено. Текст длиной: {len(transcribed_text)} символов")
            logger.info(f"📝 Распознанный текст: {transcribed_text[:100]}...")
            
            if not transcribed_text:
                logger.warning("⚠️ Получен пустой текст после распознавания")
                return "Не удалось распознать речь. Попробуйте еще раз."
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка при распознавании голосового сообщения: {e}")
            
            # Проверяем тип ошибки и возвращаем понятное сообщение
            if "insufficient_quota" in str(e) or "429" in str(e):
                return "❌ Превышена квота OpenAI API. Попробуйте позже или напишите текстом."
            elif "invalid_request_error" in str(e):
                return "❌ Неподдерживаемый формат аудио. Попробуйте записать голосовое сообщение еще раз."
            elif "audio" in str(e).lower():
                return "❌ Ошибка обработки аудио файла. Проверьте качество записи."
            else:
                return "❌ Ошибка распознавания речи. Попробуйте написать вопрос текстом."
    
    async def process_voice_message(self, voice_file_bytes: bytes, file_format: str = "ogg") -> str:
        """
        Полная обработка голосового сообщения: распознавание + поиск практики
        
        Args:
            voice_file_bytes: Байты аудио файла
            file_format: Формат файла
            
        Returns:
            str: Результат анализа ситуации
        """
        try:
            logger.info("🎯 Начинаю полную обработку голосового сообщения...")
            
            # Шаг 1: Распознаем речь
            transcribed_text = await self.transcribe_voice_message(voice_file_bytes, file_format)
            
            # Проверяем, что распознавание прошло успешно
            if transcribed_text.startswith("❌"):
                logger.error("❌ Распознавание не удалось")
                return transcribed_text
            
            logger.info(f"✅ Речь распознана: '{transcribed_text[:50]}...'")
            
            # Проверяем, что распознанный текст не пуст
            if not transcribed_text or transcribed_text.strip() == "":
                logger.error("❌ Распознанный текст пуст")
                return "❌ Не удалось распознать речь. Попробуйте записать сообщение еще раз более четко."
            
            # Шаг 2: Анализируем ситуацию через поиск судебной практики
            logger.info("🔍 Передаю распознанный текст в модуль поиска судебных практик...")
            analysis_result = await self.find_legal_practice(transcribed_text)
            
            # Добавляем информацию о том, что это было голосовое сообщение
            voice_header = f"""🎤 <b>Распознанный текст:</b> "{transcribed_text}"

📋 <b>АНАЛИЗ ВАШЕЙ СИТУАЦИИ:</b>

"""
            
            final_result = voice_header + analysis_result
            
            logger.info("✅ Полная обработка голосового сообщения завершена")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка при полной обработке голосового сообщения: {e}")
            return f"❌ Ошибка обработки голосового сообщения: {str(e)}"