import os
import logging
import shutil
from typing import List, Tuple
from pathlib import Path
from document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class DocumentManager:
    """Управление документами о Конституции РФ"""
    
    def __init__(self, documents_dir: str = "."):
        self.documents_dir = Path(documents_dir)
        self.backup_dir = self.documents_dir / "documents_backup"
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_document_stats(self) -> dict:
        """Получить статистику загруженных документов"""
        docx_files = list(self.documents_dir.glob("*.docx"))
        
        total_size = 0
        for file_path in docx_files:
            try:
                total_size += file_path.stat().st_size
            except Exception:
                continue
        
        return {
            'count': len(docx_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'files': [f.name for f in docx_files]
        }
    
    def add_document(self, file_path: str, new_name: str = None) -> Tuple[bool, str]:
        """Добавить новый документ в коллекцию"""
        try:
            source_path = Path(file_path)
            
            if not source_path.exists():
                return False, "Файл не найден"
            
            if source_path.suffix.lower() != '.docx':
                return False, "Поддерживаются только файлы .docx"
            
            # Определяем имя файла
            if new_name:
                if not new_name.endswith('.docx'):
                    new_name += '.docx'
                dest_name = new_name
            else:
                dest_name = source_path.name
            
            dest_path = self.documents_dir / dest_name
            
            # Проверяем, есть ли уже такой файл
            if dest_path.exists():
                # Создаем бэкап существующего файла
                backup_path = self.backup_dir / f"{dest_path.stem}_{Path(dest_path).stat().st_mtime:.0f}.docx"
                shutil.copy2(dest_path, backup_path)
                logger.info(f"Создан бэкап: {backup_path}")
            
            # Копируем новый файл
            shutil.copy2(source_path, dest_path)
            logger.info(f"Документ добавлен: {dest_path}")
            
            return True, f"Документ '{dest_name}' успешно добавлен"
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def remove_document(self, filename: str) -> Tuple[bool, str]:
        """Удалить документ из коллекции"""
        try:
            file_path = self.documents_dir / filename
            
            if not file_path.exists():
                return False, "Файл не найден"
            
            # Создаем бэкап перед удалением
            backup_path = self.backup_dir / f"{file_path.stem}_deleted_{file_path.stat().st_mtime:.0f}.docx"
            shutil.copy2(file_path, backup_path)
            
            # Удаляем файл
            file_path.unlink()
            logger.info(f"Документ удален: {filename}, бэкап: {backup_path}")
            
            return True, f"Документ '{filename}' удален (создан бэкап)"
            
        except Exception as e:
            logger.error(f"Ошибка удаления документа: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def validate_document(self, file_path: str) -> Tuple[bool, str, dict]:
        """Проверить документ перед добавлением"""
        try:
            doc_processor = DocumentProcessor()
            
            # Проверяем файл
            is_valid, error_msg = doc_processor.validate_file(file_path)
            if not is_valid:
                return False, error_msg, {}
            
            # Извлекаем текст для анализа
            text = doc_processor.extract_text(file_path)
            if not text:
                return False, "Не удалось извлечь текст из документа", {}
            
            # Анализируем содержимое
            text_lower = text.lower()
            constitutional_keywords = [
                'конституция', 'права', 'свобода', 'федерация', 
                'президент', 'дума', 'суд', 'закон'
            ]
            
            found_keywords = [kw for kw in constitutional_keywords if kw in text_lower]
            
            stats = {
                'length': len(text),
                'words': len(text.split()),
                'keywords_found': found_keywords,
                'relevance_score': len(found_keywords)
            }
            
            if stats['relevance_score'] < 2:
                return False, "Документ не содержит достаточно конституционно-правовой терминологии", stats
            
            return True, "Документ прошел валидацию", stats
            
        except Exception as e:
            logger.error(f"Ошибка валидации документа: {e}")
            return False, f"Ошибка валидации: {str(e)}", {}
    
    def get_document_info(self, filename: str) -> dict:
        """Получить информацию о конкретном документе"""
        try:
            file_path = self.documents_dir / filename
            
            if not file_path.exists():
                return {'error': 'Файл не найден'}
            
            stat = file_path.stat()
            
            # Пробуем извлечь базовую информацию
            try:
                doc_processor = DocumentProcessor()
                text = doc_processor.extract_text(str(file_path))
                text_length = len(text) if text else 0
                word_count = len(text.split()) if text else 0
            except Exception:
                text_length = 0
                word_count = 0
            
            return {
                'name': filename,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': stat.st_mtime,
                'text_length': text_length,
                'word_count': word_count
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о документе: {e}")
            return {'error': str(e)}
    
    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """Очистка старых бэкапов"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (keep_days * 24 * 60 * 60)
            
            removed_count = 0
            for backup_file in self.backup_dir.glob("*.docx"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    removed_count += 1
                    logger.info(f"Удален старый бэкап: {backup_file}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")
            return 0
    
    def export_document_list(self, output_file: str = "document_list.txt") -> bool:
        """Экспорт списка документов в текстовый файл"""
        try:
            stats = self.get_document_stats()
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("СПИСОК КОНСТИТУЦИОННЫХ ДОКУМЕНТОВ\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Всего документов: {stats['count']}\n")
                f.write(f"Общий размер: {stats['total_size_mb']} МБ\n\n")
                
                for i, filename in enumerate(stats['files'], 1):
                    info = self.get_document_info(filename)
                    f.write(f"{i}. {filename}\n")
                    if 'error' not in info:
                        f.write(f"   Размер: {info['size_mb']} МБ\n")
                        f.write(f"   Слов: {info['word_count']}\n")
                    f.write("\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта списка: {e}")
            return False 