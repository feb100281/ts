# Начлало работы

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

python manage.py runserver 62.109.2.166:8092