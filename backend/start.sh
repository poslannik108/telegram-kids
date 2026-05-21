#!/bin/bash
# FamilyGuard — скрипт запуска

echo "🚀 Запуск FamilyGuard Backend..."

# Загружаем переменные окружения
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
    echo "✅ Конфигурация загружена"
else
    echo "❌ Файл .env не найден! Скопируй .env.example в .env и заполни"
    exit 1
fi

# Устанавливаем зависимости если нужно
if [ ! -d "venv" ]; then
    echo "📦 Создаём виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Запускаем API сервер в фоне
echo "🌐 Запуск API сервера на порту 8000..."
uvicorn api_server:app --host 0.0.0.0 --port 8000 &

# Запускаем основной backend
echo "🤖 Запуск бота родителя и клиента ребёнка..."
python3 main.py
