# 🚀 Инструкция по деплою бота "Практика.Суд" на сервер

## 1. Подключение к серверу
```bash
ssh root@YOUR_SERVER_IP
```

## 2. Подготовка директории
```bash
cd ..
cd home
mkdir praktika-sud-bot
cd praktika-sud-bot
```

## 3. Загрузка файлов на сервер
### Вариант А: Через SCP (с вашего компьютера)
```bash
scp praktika-sud-bot.tar.gz root@YOUR_SERVER_IP:/home/praktika-sud-bot/
```

### Вариант Б: Прямо на сервере создать файлы
```bash
# Создать все файлы проекта по одному через nano или vim
```

## 4. Распаковка файлов (если используете архив)
```bash
cd /home/praktika-sud-bot
tar -xzf praktika-sud-bot.tar.gz
rm praktika-sud-bot.tar.gz
```

## 5. Установка Python и зависимостей
```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python и pip
apt install python3 python3-pip python3-venv -y

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

## 6. Тестовый запуск
```bash
python3 main.py
# Ctrl+C для остановки
```

## 7. Создание systemd сервиса для автозапуска
```bash
nano /etc/systemd/system/praktika-sud-bot.service
```

### Содержимое файла сервиса:
```ini
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
```

## 8. Активация сервиса
```bash
# Перезагрузка systemd
systemctl daemon-reload

# Включение автозапуска
systemctl enable praktika-sud-bot.service

# Запуск сервиса
systemctl start praktika-sud-bot.service

# Проверка статуса
systemctl status praktika-sud-bot.service
```

## 9. Управление ботом
```bash
# Проверить статус
systemctl status praktika-sud-bot

# Остановить бота
systemctl stop praktika-sud-bot

# Запустить бота
systemctl start praktika-sud-bot

# Перезапустить бота
systemctl restart praktika-sud-bot

# Посмотреть логи
journalctl -u praktika-sud-bot -f
```

## 10. Настройка фаервола (опционально)
```bash
# Разрешить SSH
ufw allow ssh

# Включить фаервол
ufw enable
```

## 11. Проверка работы
После всех настроек бот должен:
- ✅ Автоматически запускаться при перезагрузке сервера
- ✅ Перезапускаться при сбоях
- ✅ Логировать работу через systemd

## 12. Полезные команды для мониторинга
```bash
# Мониторинг ресурсов
htop

# Проверка сетевых подключений
netstat -tulpn

# Мониторинг логов в реальном времени
journalctl -u praktika-sud-bot -f
```

## 🚨 Важные моменты:
1. **Замените YOUR_SERVER_IP** на реальный IP сервера
2. **Проверьте, что порт 22 (SSH) открыт**
3. **Убедитесь, что OpenAI API ключ рабочий**
4. **Telegram Bot Token должен быть актуальным**

## ✅ После выполнения всех шагов:
Ваш бот будет работать 24/7 на сервере и автоматически перезапускаться при любых сбоях! 