🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
🛠️  ОБНОВЛЕНИЕ НА СЕРВЕРЕ
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦

🔐 ПОДКЛЮЧЕНИЕ
────────────────────────
ssh daria@82.202.197.94
ПАРОЛЬ

📂 ПРОЕКТ И ОКРУЖЕНИЕ
────────────────────────
cd ts
source .venv/bin/activate

🔄 ОБНОВЛЕНИЕ КОДА
────────────────────────
git pull origin daria

🎨 СБОР СТАТИКИ
────────────────────────
python manage.py collectstatic

🧪 ПРОВЕРКА (на всякий случай)
────────────────────────
python manage.py check

🚀 ПЕРЕЗАПУСК СЕРВИСА
────────────────────────
sudo systemctl restart gunicorn-ts

Манажемент коммандс
________
#Получить продажи
python manage.py fin_report_range 2026-04-27 2026-04-28 --overwrite

________


🌐 SSH-ТУННЕЛЬ К БАЗЕ
────────────────────────
(в новом терминале)

ssh -N -L 5433:localhost:5432 daria@82.202.197.94



ДОСТУП НА СКАЧИВАНИЕ ТАБЛИЦ ИЗ БАЗЫ ДАННЫХ

sudo -u postgres psql -d ts_db -c "GRANT SELECT ON public.pl_for_csv TO ts_user;"
sudo -u postgres psql -d ts_db -c "GRANT SELECT ON public.arap_to_date TO ts_user;"


ОТПРАВИЛА ФАЙЛ НА СЕРВЕР
scp "/Users/daria/Desktop/TS Сделать/Обмен.zip" daria@82.202.197.94:/home/daria/

# как скачать файл аналитики

scp daria@82.202.197.94:/home/daria/ts/data/analytics.duckdb /Users/????/ts/data/analytics.duckdb


# Начало работы

## Переходим в папку проекта и клонируем с github

```
git clone https://github.com/feb100281/ts.git
cd ts
git switch -c daria
```

## Создаем виртуальное окружение для python 3.12

```
python3.12 -m venv venv
```
Включаем
```
source venv/bin/activate
```
На всяк случай обновляем pip
```
pip install --upgrade pip
```
Устанавливаем зависимости
```
pip install -r requirements.txt
```
Обновляем `requirements.txt` если пипнула библиотеку
```
pip freeze > requirements.txt
```

## добавляем .env

```
touch .env
в файл записываем инфу из телеги
```




Вход на серверную версию
ssh daria@62.109.2.166
ПАРОЛЬ

cd ts
source venv/bin/activate

git pull origin ...


ПЕРЕЗАГРУЗКА СЕРВЕРА 
pkill -HUP -f "ts.wsgi"




вот перезагрузка
nohup gunicorn ts.wsgi:application \   --bind 0.0.0.0:8090 \   --workers 4 \   --threads 2 \   --timeout 60 \   --max-requests 2000 \   --max-requests-jitter 200 \   --access-logfile - \   --error-logfile - \   --log-level info \   > gunicorn.log 2>&1 &


python manage.py runserver 62.109.2.166:8092

СЕРВЕР
http://62.109.2.166:8090