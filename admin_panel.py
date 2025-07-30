"""
CRM + Админ-панель для Telegram-бота "Виртуальный юрист"
Упрощённая CRM реализована полностью в Telegram-боте — без веб-интерфейса.
"""

import sqlite3
import logging
import asyncio
import json
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import pandas as pd
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class AdminPanel:
    """CRM + Админ-панель для управления ботом через Telegram"""
    
    # Список администраторов (user_id)
    ADMIN_IDS = {1914567632, 892033994}
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    total_requests INTEGER DEFAULT 0
                )
            """)
            
            # Таблица запросов пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    request_type TEXT,
                    request_text TEXT,
                    response_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time REAL,
                    status TEXT DEFAULT 'completed',
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица событий системы
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    event_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER
                )
            """)
            
            # Таблица заметок администратора
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    note_text TEXT,
                    admin_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("✅ База данных CRM инициализирована")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
    
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id in self.ADMIN_IDS
    
    def log_user_activity(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Логирует активность пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Обновляем или создаем запись пользователя
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, last_activity, total_requests,
                 registration_date, is_active)
                VALUES (?, ?, ?, ?, ?, 
                        COALESCE((SELECT total_requests FROM users WHERE user_id = ?), 0) + 1,
                        COALESCE((SELECT registration_date FROM users WHERE user_id = ?), ?),
                        1)
            """, (user_id, username, first_name, last_name, datetime.now(), 
                  user_id, user_id, datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования активности пользователя: {e}")
    
    def log_user_request(self, user_id: int, request_type: str, request_text: str, 
                        response_text: str = "", processing_time: float = 0.0):
        """Логирует запрос пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_requests 
                (user_id, request_type, request_text, response_text, processing_time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, request_type, request_text, response_text, processing_time))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования запроса: {e}")
    
    def log_system_event(self, event_type: str, event_data: str, user_id: int = None):
        """Логирует системное событие"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_events (event_type, event_data, user_id)
                VALUES (?, ?, ?)
            """, (event_type, event_data, user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования события: {e}")
    
    def get_admin_keyboard(self) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру админ-панели"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_analytics")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="📝 Запросы", callback_data="admin_requests")],
            [InlineKeyboardButton(text="📤 Экспорт данных", callback_data="admin_export")],
            [InlineKeyboardButton(text="🔧 Настройки", callback_data="admin_settings")]
        ])
        return keyboard
    
    def get_analytics_data(self, days: int = 7) -> Dict:
        """Получает аналитические данные за период"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days)
            
            # Активные пользователи
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as active_users
                FROM user_requests 
                WHERE timestamp >= ?
            """, (start_date,))
            active_users = cursor.fetchone()[0]
            
            # Общее количество запросов
            cursor.execute("""
                SELECT COUNT(*) as total_requests
                FROM user_requests 
                WHERE timestamp >= ?
            """, (start_date,))
            total_requests = cursor.fetchone()[0]
            
            # Топ пользователь по запросам
            cursor.execute("""
                SELECT u.user_id, u.first_name, u.username, COUNT(r.id) as request_count
                FROM users u
                JOIN user_requests r ON u.user_id = r.user_id
                WHERE r.timestamp >= ?
                GROUP BY u.user_id
                ORDER BY request_count DESC
                LIMIT 1
            """, (start_date,))
            top_user = cursor.fetchone()
            
            # Статистика по типам запросов
            cursor.execute("""
                SELECT request_type, COUNT(*) as count
                FROM user_requests 
                WHERE timestamp >= ?
                GROUP BY request_type
                ORDER BY count DESC
            """, (start_date,))
            request_types = cursor.fetchall()
            
            # Активность по дням
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as requests
                FROM user_requests 
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            """, (start_date,))
            daily_activity = cursor.fetchall()
            
            conn.close()
            
            return {
                'active_users': active_users,
                'total_requests': total_requests,
                'top_user': top_user,
                'request_types': request_types,
                'daily_activity': daily_activity,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения аналитики: {e}")
            return {}
    
    def format_analytics_message(self, analytics: Dict) -> str:
        """Форматирует аналитические данные в сообщение"""
        if not analytics:
            return "❌ Ошибка получения аналитических данных"
        
        message = f"""📊 <b>АНАЛИТИКА ЗА {analytics['period_days']} ДНЕЙ</b>

👥 <b>Активные пользователи:</b> {analytics['active_users']}
📝 <b>Всего запросов:</b> {analytics['total_requests']}

🏆 <b>Топ пользователь:</b>"""
        
        if analytics['top_user']:
            user_id, first_name, username, request_count = analytics['top_user']
            user_name = first_name or username or f"ID {user_id}"
            message += f"\n• {user_name} - {request_count} запросов"
        else:
            message += "\n• Нет данных"
        
        message += "\n\n📈 <b>Популярные типы запросов:</b>"
        for request_type, count in analytics['request_types'][:5]:
            message += f"\n• {request_type}: {count}"
        
        if analytics['daily_activity']:
            message += "\n\n📅 <b>Активность по дням:</b>"
            for date, requests in analytics['daily_activity'][-7:]:
                message += f"\n• {date}: {requests} запросов"
        
        return message
    
    def get_users_list(self, page: int = 1, limit: int = 10) -> Tuple[List[Dict], int]:
        """Получает список пользователей с пагинацией"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            offset = (page - 1) * limit
            
            # Получаем пользователей
            cursor.execute("""
                SELECT user_id, username, first_name, last_name, 
                       registration_date, last_activity, total_requests
                FROM users 
                ORDER BY last_activity DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'user_id': row[0],
                    'username': row[1],
                    'first_name': row[2],
                    'last_name': row[3],
                    'registration_date': row[4],
                    'last_activity': row[5],
                    'total_requests': row[6]
                })
            
            # Получаем общее количество пользователей
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            conn.close()
            
            return users, total_users
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка пользователей: {e}")
            return [], 0
    
    def export_users_csv(self) -> io.StringIO:
        """Экспортирует пользователей в CSV"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Запрос с подробной информацией
            query = """
                SELECT 
                    u.user_id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.registration_date,
                    u.last_activity,
                    u.total_requests,
                    COUNT(r.id) as actual_requests,
                    AVG(r.processing_time) as avg_processing_time
                FROM users u
                LEFT JOIN user_requests r ON u.user_id = r.user_id
                GROUP BY u.user_id
                ORDER BY u.last_activity DESC
            """
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Создаем CSV в памяти
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта пользователей: {e}")
            return None
    
    def export_requests_csv(self, days: int = 30) -> io.StringIO:
        """Экспортирует запросы в CSV"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            start_date = datetime.now() - timedelta(days=days)
            
            query = """
                SELECT 
                    r.id,
                    r.user_id,
                    u.username,
                    u.first_name,
                    r.request_type,
                    r.request_text,
                    r.timestamp,
                    r.processing_time,
                    r.status
                FROM user_requests r
                LEFT JOIN users u ON r.user_id = u.user_id
                WHERE r.timestamp >= ?
                ORDER BY r.timestamp DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(start_date,))
            conn.close()
            
            # Создаем CSV в памяти
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            
            return output
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта запросов: {e}")
            return None

# Глобальный экземпляр админ-панели
admin_panel = AdminPanel() 