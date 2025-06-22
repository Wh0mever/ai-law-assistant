#!/bin/bash

# 🚀 Автоматический деплой бота "Практика.Суд"
# Этот скрипт нужно запустить на сервере

echo "🚀 Начинаем деплой бота Практика.Суд..."

# Обновление системы
echo "📦 Обновляем систему..."
apt update && apt upgrade -y

# Установка Python и зависимостей
echo "🐍 Устанавливаем Python..."
apt install python3 python3-pip python3-venv nano htop -y

# Переход в нужную директорию
echo "📁 Создаем директорию проекта..."
cd /home
mkdir -p praktika-sud-bot
cd praktika-sud-bot

# Создание виртуального окружения
echo "🌐 Создаем виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Создание requirements.txt если его нет
echo "📋 Создаем requirements.txt..."
cat > requirements.txt << EOF
aiogram==3.4.1
openai==1.51.2
PyMuPDF==1.24.12
python-docx==0.8.11
requests==2.32.3
aiofiles==23.2.1
python-multipart==0.0.9
httpx==0.27.2
EOF

# Установка зависимостей
echo "📦 Устанавливаем зависимости..."
pip install -r requirements.txt

# Создание systemd сервиса
echo "⚙️ Создаем systemd сервис..."
cat > /etc/systemd/system/praktika-sud-bot.service << EOF
[Unit]
Description=Praktika Sud Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/praktika-sud-bot
Environment=PATH=/home/praktika-sud-bot/venv/bin
ExecStart=/home/praktika-sud-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
echo "🔄 Перезагружаем systemd..."
systemctl daemon-reload

# Включение автозапуска
echo "✅ Включаем автозапуск..."
systemctl enable praktika-sud-bot.service

echo ""
echo "🎉 Базовая настройка завершена!"
echo ""
echo "📝 Что нужно сделать дальше:"
echo "1. Загрузить файлы бота в /home/praktika-sud-bot/"
echo "2. Проверить config.py с правильными ключами"
echo "3. Запустить: systemctl start praktika-sud-bot"
echo "4. Проверить: systemctl status praktika-sud-bot"
echo ""
echo "🔧 Полезные команды:"
echo "systemctl status praktika-sud-bot    # Статус"
echo "systemctl restart praktika-sud-bot   # Перезапуск"
echo "journalctl -u praktika-sud-bot -f    # Логи"
echo ""
echo "📁 Текущая директория: $(pwd)"
echo "🎯 Готово к загрузке файлов бота!" 