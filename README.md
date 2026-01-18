# Начлало работы

## Переходим в папку проекта и клонируем с github

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
Обновляем `requirements.txt`
```
pip freeze > requirements.txt
```

