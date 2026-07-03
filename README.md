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

_________


🌐 SSH-ТУННЕЛЬ К БАЗЕ
────────────────────────
(в новом терминале)

ssh -N -L 5433:localhost:5432 daria@82.202.197.94



🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
🦆 DUCKDB: СОЗДАНИЕ БАЗЫ И ЗАЛИВКА ДАННЫХ
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦

📦 СОЗДАНИЕ И ЗАГРУЗКА В DUCKDB
────────────────────────
(с нуля, полный прогон)
python manage.py cards_etl
python manage.py duck_etl


🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
📊 ЗАГРУЗКА ПРОДАЖ (PARQUET)
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦

📥 СКАЧИВАЕМ НОВЫЕ ПРОДАЖИ
────────────────────────
(с перезаписью файлов)
1) python manage.py fin_report_range 2026-06-30 2026-07-02 --overwrite
2) python manage.py duck_etl
3) python manage.py duck_etl --update (если на сервере)



📥 СКАЧИВАЕМ ОСТАТКИ
────────────────────────
1) Заходим на сервер ssh daria@82.202.197.94
2) cd ts/data
3) cd realization
4) cd stocks
5) python3 -m http.server 8000
6) 82.202.197.94:8000 (скачиваем остатки в браузере)
7) python manage.py stocks_etl (Распарсиваем остатки по складам) 
8) python manage.py inventories


📥 ОБНОВЛЯТЬ КАРТЫ
────────────────────────
python manage.py wb_cards_to_parquet --overwrite
python manage.py cards_etl



Поставки 
python manage.py delivery_etl


Наши блокнотики
python manage.py wb_notebooks




## Манажемент коммандс
________
### Получить продажи - пока так. WB мутит что то нужно руками
```
python manage.py fin_report_range 2026-04-27 2026-04-28 --overwrite
```
### Обновить карточки - долго. Я таймер настрою на автомат что бы не ждать
```
python manage.py wb_cards_to_parquet
```
### Снять склады. Нужно один раз в день в опеределнное время - настрою таймер
```
python manage.py daily_stocks
```
### Обновляем аналитику и утку - тяжелый скрипт нужно автоматом делать но я очкую пока
```
python manage.py duck_etl
```
________

## Запуст утки не сервере 
```
# В терминале
cd ts
source .venv/bin/activate
./duckdb
# после того как открылась утка териминал memory D
FORCE INSTALL ui;
LOAD ui;
CALL start_ui_server();
```

появилос 
                 result                    │
│                   varchar                   │
├─────────────────────────────────────────────┤
│ UI server started at http://localhost:4213/ │

открываем в отдельный териминал и пробрасываем тунель (не на сервере)
```
ssh -f -N -L 4213:localhost:4213 daria@82.202.197.94
# в браузере
http://localhost:4213
```







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


rsync -avP daria@82.202.197.94:/home/daria/ts/data/realization ~/Downloads/


🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
🛠️  ПЕРЕНОС duckdb для локальной разработки
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦

1) brew install zstd -- устанавливаем архиватор пропускаем далее
2) открываем новый терминал в проекте
3) cd data
4) rsync -avP daria@82.202.197.94:~/ts/data/analytics.duckdb.zst .  --скачиваем архив с сервера
5) zstd -d -k analytics.duckdb.zst   -- разархивируем (y нажимае)

-- если нужно создать архив 
6) заходим на сервер
7) cd ts
8) cd data
9) zstd -T0 -19 -k analytics.duckdb 
10) повторяем шаги 2-5  


