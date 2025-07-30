#!/usr/bin/env python3
"""
Продвинутый парсер для извлечения структуры юридических документов
Извлекает статьи, главы, разделы с точными ссылками для AI-ассистента
"""
import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LegalArticle:
    """Структура статьи закона"""
    article_number: str
    title: str
    content: str
    source_file: str
    chapter: Optional[str] = None
    section: Optional[str] = None
    part: Optional[str] = None
    paragraph_number: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    unique_id: str = ""
    
    def __post_init__(self):
        if not self.unique_id:
            # Создаем уникальный ID на основе содержимого
            content_hash = hashlib.md5(
                f"{self.source_file}_{self.article_number}_{self.title}".encode()
            ).hexdigest()[:8]
            self.unique_id = f"{Path(self.source_file).stem}_{self.article_number}_{content_hash}"

@dataclass 
class LegalDocument:
    """Структура юридического документа"""
    title: str
    source_file: str
    document_type: str
    articles: List[LegalArticle]
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class LegalStructureParser:
    """Парсер структуры юридических документов"""
    
    def __init__(self, txt_documents_dir: str = "txt_documents"):
        self.txt_dir = txt_documents_dir
        self.documents: List[LegalDocument] = []
        self.articles_index: Dict[str, LegalArticle] = {}
        
        # Паттерны для распознавания структуры
        self.patterns = {
            # Статьи
            'article': [
                r'Статья\s+(\d+(?:\.\d+)*)\.\s*([^\n]+)',
                r'Статья\s+(\d+(?:\.\d+)*)\s*\.\s*([^\n]+)',
                r'Статья\s+(\d+(?:\.\d+)*)\s+([^\n]+)',
                r'ст\.\s*(\d+(?:\.\d+)*)\s*\.?\s*([^\n]+)',
                r'(?:^|\n)(\d+(?:\.\d+)*)\.\s*([^\n]+?)(?=\n|$)'
            ],
            
            # Главы
            'chapter': [
                r'Глава\s+(\d+(?:\.\d+)*)\.\s*([^\n]+)',
                r'ГЛАВА\s+(\d+(?:\.\d+)*)\.\s*([^\n]+)',
                r'Глава\s+([IVXLC]+)\.\s*([^\n]+)',
                r'ГЛАВА\s+([IVXLC]+)\.\s*([^\n]+)'
            ],
            
            # Разделы
            'section': [
                r'Раздел\s+([IVXLC]+)\.\s*([^\n]+)',
                r'РАЗДЕЛ\s+([IVXLC]+)\.\s*([^\n]+)',
                r'Раздел\s+(\d+)\.\s*([^\n]+)',
                r'РАЗДЕЛ\s+(\d+)\.\s*([^\n]+)'
            ],
            
            # Части
            'part': [
                r'Часть\s+(\d+)\.\s*([^\n]+)',
                r'ЧАСТЬ\s+(\d+)\.\s*([^\n]+)',
                r'часть\s+(\d+)\s*([^\n]*)'
            ],
            
            # Пункты
            'paragraph': [
                r'^(\d+)\.\s*([^\n]+)',
                r'пункт\s+(\d+)\s*\.?\s*([^\n]*)',
                r'п\.\s*(\d+)\s*\.?\s*([^\n]*)'
            ]
        }
    
    def detect_document_type(self, content: str, filename: str) -> str:
        """Определяем тип документа"""
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        # Проверяем путь к файлу - если файл из директории ФЗ, это Федеральный закон
        if 'фз' in filename_lower or '/фз/' in filename_lower.replace('\\', '/'):
            return "Федеральный закон"
        
        if any(word in content_lower for word in ['гражданский кодекс', 'гк рф']):
            return "Гражданский кодекс РФ"
        elif any(word in content_lower for word in ['уголовный кодекс', 'ук рф']):
            return "Уголовный кодекс РФ"
        elif any(word in content_lower for word in ['трудовой кодекс', 'тк рф']):
            return "Трудовой кодекс РФ"
        elif any(word in content_lower for word in ['арбитражный процессуальный', 'апк рф']):
            return "Арбитражный процессуальный кодекс РФ"
        elif any(word in content_lower for word in ['гражданский процессуальный', 'гпк рф']):
            return "Гражданский процессуальный кодекс РФ"
        elif any(word in content_lower for word in ['уголовный процессуальный', 'упк рф']):
            return "Уголовный процессуальный кодекс РФ"
        elif any(word in content_lower for word in ['административный процессуальный', 'кап рф']):
            return "Административный процессуальный кодекс РФ"
        elif any(word in content_lower for word in ['кодекс об административных правонарушениях', 'коап рф']):
            return "Кодекс об административных правонарушениях РФ"
        elif any(word in content_lower for word in ['федеральный закон', 'фз']):
            return "Федеральный закон"
        elif any(word in content_lower for word in ['постановление', 'определение']):
            return "Судебная практика"
        elif 'консультантплюс' in filename_lower:
            return "КонсультантПлюс документ"
        else:
            return "Федеральный закон"  # По умолчанию для неопознанных документов
    
    def extract_document_title(self, content: str, filename: str) -> str:
        """Извлекаем название документа"""
        lines = content.split('\n')[:20]  # Первые 20 строк
        
        # Ищем заголовок в первых строках
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:
                # Проверяем на характерные признаки заголовка
                if any(word in line.upper() for word in [
                    'КОДЕКС', 'ЗАКОН', 'ПОСТАНОВЛЕНИЕ', 
                    'ОПРЕДЕЛЕНИЕ', 'РОССИЙСКОЙ ФЕДЕРАЦИИ'
                ]):
                    return line
        
        # Если не нашли, используем имя файла
        return Path(filename).stem.replace('_', ' ')
    
    def find_article_content(self, lines: List[str], start_idx: int, 
                           next_article_idx: Optional[int] = None) -> Tuple[str, int]:
        """Извлекаем содержимое статьи"""
        content_lines = []
        end_idx = next_article_idx if next_article_idx else len(lines)
        
        # Пропускаем строку с номером статьи
        for i in range(start_idx + 1, end_idx):
            line = lines[i].strip()
            
            # Прерываем на следующей структурной единице
            if self.is_structural_element(line):
                end_idx = i
                break
                
            if line:  # Добавляем только непустые строки
                content_lines.append(line)
        
        return '\n'.join(content_lines), end_idx
    
    def is_structural_element(self, line: str) -> bool:
        """Проверяем, является ли строка структурным элементом"""
        for pattern_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    return True
        return False
    
    def parse_document_structure(self, content: str, filename: str) -> LegalDocument:
        """Парсим структуру документа"""
        lines = content.split('\n')
        articles = []
        
        # Текущий контекст
        current_section = None
        current_chapter = None
        current_part = None
        
        # Находим все статьи
        article_positions = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Обновляем контекст
            for pattern in self.patterns['section']:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    current_section = f"Раздел {match.group(1)}. {match.group(2)}"
                    break
            
            for pattern in self.patterns['chapter']:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    current_chapter = f"Глава {match.group(1)}. {match.group(2)}"
                    break
            
            for pattern in self.patterns['part']:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    current_part = f"Часть {match.group(1)}. {match.group(2)}"
                    break
            
            # Ищем статьи
            for pattern in self.patterns['article']:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    article_number = match.group(1)
                    article_title = match.group(2).strip()
                    
                    article_positions.append({
                        'number': article_number,
                        'title': article_title,
                        'line_start': i,
                        'section': current_section,
                        'chapter': current_chapter,
                        'part': current_part
                    })
                    break
        
        # Извлекаем содержимое статей
        for i, article_info in enumerate(article_positions):
            next_article_line = (article_positions[i + 1]['line_start'] 
                               if i + 1 < len(article_positions) else None)
            
            content, end_line = self.find_article_content(
                lines, article_info['line_start'], next_article_line
            )
            
            if content.strip():  # Только если есть содержимое
                article = LegalArticle(
                    article_number=article_info['number'],
                    title=article_info['title'],
                    content=content.strip(),
                    source_file=filename,
                    section=article_info['section'],
                    chapter=article_info['chapter'],
                    part=article_info['part'],
                    line_start=article_info['line_start'],
                    line_end=end_line
                )
                articles.append(article)
        
        # Создаем документ
        doc_title = self.extract_document_title(content, filename)
        doc_type = self.detect_document_type(content, filename)
        
        document = LegalDocument(
            title=doc_title,
            source_file=filename,
            document_type=doc_type,
            articles=articles,
            metadata={
                'total_articles': len(articles),
                'parsed_at': 'unknown',
                'file_size': len(content)
            }
        )
        
        return document
    
    def parse_all_documents(self) -> Dict:
        """Парсим все документы в директории"""
        txt_files = []
        
        if os.path.exists(self.txt_dir):
            txt_files = [f for f in os.listdir(self.txt_dir) 
                        if f.endswith('.txt') and not f.startswith('document_')]
        
        if not txt_files:
            logger.warning(f"Не найдено TXT файлов в {self.txt_dir}")
            return {}
        
        logger.info(f"Найдено {len(txt_files)} документов для парсинга")
        
        for txt_file in txt_files:
            file_path = os.path.join(self.txt_dir, txt_file)
            
            try:
                logger.info(f"Парсим: {txt_file}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Пропускаем метаданные в начале
                if content.startswith('# Документ:'):
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if not line.startswith('#') and line.strip():
                            content = '\n'.join(lines[i:])
                            break
                
                document = self.parse_document_structure(content, txt_file)
                self.documents.append(document)
                
                # Добавляем статьи в индекс
                for article in document.articles:
                    self.articles_index[article.unique_id] = article
                
                logger.info(f"✅ {txt_file}: найдено {len(document.articles)} статей")
                
            except Exception as e:
                logger.error(f"❌ Ошибка при парсинге {txt_file}: {e}")
        
        return self.generate_parsing_report()
    
    def generate_parsing_report(self) -> Dict:
        """Генерируем отчет о парсинге"""
        total_articles = sum(len(doc.articles) for doc in self.documents)
        
        doc_types = {}
        for doc in self.documents:
            doc_type = doc.document_type
            if doc_type not in doc_types:
                doc_types[doc_type] = []
            doc_types[doc_type].append(doc.title)
        
        report = {
            'total_documents': len(self.documents),
            'total_articles': total_articles,
            'document_types': doc_types,
            'articles_by_document': {
                doc.title: len(doc.articles) for doc in self.documents
            }
        }
        
        return report
    
    def save_parsed_data(self, output_file: str = "legal_structure.json"):
        """Сохраняем распарсенные данные"""
        output_path = os.path.join(self.txt_dir, output_file)
        
        # Конвертируем в сериализуемый формат
        data = {
            'documents': [asdict(doc) for doc in self.documents],
            'articles_index': {k: asdict(v) for k, v in self.articles_index.items()},
            'metadata': {
                'total_documents': len(self.documents),
                'total_articles': len(self.articles_index),
                'parsing_date': 'unknown'
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Структура сохранена в {output_path}")
        return output_path
    
    def search_articles(self, query: str, max_results: int = 5) -> List[LegalArticle]:
        """Простой текстовый поиск по статьям"""
        query_lower = query.lower()
        results = []
        
        for article in self.articles_index.values():
            score = 0
            
            # Поиск в номере статьи
            if query_lower in article.article_number.lower():
                score += 10
                
            # Поиск в заголовке
            if query_lower in article.title.lower():
                score += 8
                
            # Поиск в содержимом
            if query_lower in article.content.lower():
                score += 5
                
            # Поиск в контексте
            if article.chapter and query_lower in article.chapter.lower():
                score += 3
                
            if score > 0:
                results.append((article, score))
        
        # Сортируем по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        
        return [article for article, score in results[:max_results]]
    
    def get_article_reference(self, article: LegalArticle) -> str:
        """Генерируем ссылку на статью"""
        ref_parts = []
        
        if article.section:
            ref_parts.append(article.section)
        if article.chapter:
            ref_parts.append(article.chapter)
        
        ref_parts.append(f"Статья {article.article_number}")
        
        if article.title:
            ref_parts.append(f'"{article.title}"')
        
        ref_text = " → ".join(ref_parts)
        ref_text += f"\n📎 Источник: {article.source_file}#{article.unique_id}"
        
        return ref_text


def main():
    """Основная функция"""
    print("🏛️ Парсер структуры юридических документов")
    print("=" * 50)
    
    parser = LegalStructureParser()
    
    # Парсим все документы
    report = parser.parse_all_documents()
    
    # Выводим отчет
    print(f"\n📊 ОТЧЕТ О ПАРСИНГЕ:")
    print(f"📄 Обработано документов: {report['total_documents']}")
    print(f"⚖️ Извлечено статей: {report['total_articles']}")
    
    print(f"\n📋 Типы документов:")
    for doc_type, titles in report['document_types'].items():
        print(f"  • {doc_type}: {len(titles)} шт.")
    
    print(f"\n📈 Статей по документам:")
    for title, count in report['articles_by_document'].items():
        print(f"  • {title}: {count} статей")
    
    # Сохраняем результат
    output_file = parser.save_parsed_data()
    
    # Демонстрация поиска
    print(f"\n🔍 Демонстрация поиска:")
    test_queries = ["наследование", "договор", "суд", "право"]
    
    for query in test_queries:
        results = parser.search_articles(query, max_results=2)
        if results:
            print(f"\n🔎 '{query}':")
            for article in results:
                print(f"  📄 Статья {article.article_number}: {article.title}")
                print(f"     📁 {article.source_file}")
    
    print(f"\n✅ Парсинг завершен! Результат сохранен в {output_file}")


if __name__ == "__main__":
    main() 