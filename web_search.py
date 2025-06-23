import requests
import logging
from typing import List, Dict
from urllib.parse import quote_plus
import time

logger = logging.getLogger(__name__)

class WebSearchService:
    """Сервис для поиска актуальной юридической информации в интернете"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    async def search_legal_info(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Поиск юридической информации
        
        Args:
            query: Поисковый запрос
            max_results: Максимальное количество результатов
            
        Returns:
            Список словарей с найденной информацией
        """
        try:
            # Добавляем уточняющие слова для юридического поиска
            legal_query = f"{query} закон практика суд постановление РФ"
            encoded_query = quote_plus(legal_query)
            
            # Используем DuckDuckGo для поиска (не требует API ключа)
            search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}&kl=ru-ru"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            # Простой парсинг результатов (без BeautifulSoup для упрощения)
            results = []
            
            # Здесь должна быть логика парсинга результатов поиска
            # Для демонстрации возвращаем заглушку
            results.append({
                'title': 'Актуальная судебная практика',
                'snippet': 'Рекомендуем обратиться к практикующему юристу для получения актуальной информации по вашему вопросу.',
                'url': 'https://vsrf.ru/'
            })
            
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return [{
                'title': 'Ошибка поиска',
                'snippet': 'Не удалось найти актуальную информацию в интернете. Рекомендуем обратиться к практикующему юристу.',
                'url': ''
            }]
    
    def format_search_results(self, results: List[Dict[str, str]]) -> str:
        """Форматирование результатов поиска для отображения пользователю"""
        if not results:
            return "🔍 **Результаты веб-поиска не найдены**\n\nРекомендуем обратиться к практикующему юристу."
        
        formatted = "🌐 **Актуальная информация из интернета:**\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"**{i}. {result['title']}**\n"
            formatted += f"{result['snippet']}\n"
            if result['url']:
                formatted += f"🔗 {result['url']}\n"
            formatted += "\n"
        
        formatted += "⚠️ **Важно:** Вся информация из интернета требует проверки у практикующего юриста."
        
        return formatted 