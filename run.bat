@echo off
echo Установка зависимостей...
pip install -r requirements.txt

echo Запуск бота мониторинга листингов...
python main.py

pause