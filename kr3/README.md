# FastAPI Homework 3

Этот проект содержит выполненные задания 6.1 - 8.2 (Контрольная работа №3). 
Все задания собраны в единое приложение.

## Как запустить

1. Создайте виртуальное окружение и активируйте его:
   ```bash
   python -m venv venv
   source venv/bin/activate  # для Linux/Mac
   venv\Scripts\activate     # для Windows
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создайте файл `.env` на основе `.env.example` (или используйте уже созданный).
4. Запустите приложение:
   ```bash
   uvicorn main:app --reload
   ```

## Как тестировать

### Задание 6.1, 6.2 (Basic Auth / In-memory)
```bash
curl -u user1:correctpass http://localhost:8000/login
```

### Задание 6.3 (Docs Auth)
Перейдите в браузере на `http://localhost:8000/docs`. Потребуется логин и пароль (admin:admin). Если в `.env` выставить `MODE=PROD`, документация вернет 404 Not Found.

### Задание 6.4, 6.5, 8.1 (Регистрация, SQLite, JWT, Rate Limiting)
Регистрация (запись в SQLite):
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"123\"}" http://localhost:8000/register
```

Логин (получение JWT токена):
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"123\"}" http://localhost:8000/login
```

### Задание 7.1 (RBAC с JWT)
Используйте токен, полученный при логине (замените `<ВАШ_ТОКЕН>`):
```bash
curl -H "Authorization: Bearer <ВАШ_ТОКЕН>" http://localhost:8000/protected_resource
curl -H "Authorization: Bearer <ВАШ_ТОКЕН>" http://localhost:8000/user_resource
curl -H "Authorization: Bearer <ВАШ_ТОКЕН>" http://localhost:8000/admin_resource
```
*(Только пользователь `admin` (указанный при регистрации первым или с именем admin) имеет доступ к admin_resource, остальные получают 403)*

### Задание 8.2 (Todos CRUD с БД)
Создать Todo:
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"title\":\"Test\",\"description\":\"Desc\"}" http://localhost:8000/todos
```
Получить Todo:
```bash
curl http://localhost:8000/todos/1
```
Обновить Todo:
```bash
curl -X PUT -H "Content-Type: application/json" -d "{\"title\":\"Test Updated\",\"completed\":true}" http://localhost:8000/todos/1
```
Удалить Todo:
```bash
curl -X DELETE http://localhost:8000/todos/1
```
