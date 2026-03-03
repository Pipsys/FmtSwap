# PDF → DOCX Converter

Безопасное веб-приложение для конвертации PDF в редактируемый формат Word (DOCX).  
Стек: **FastAPI** + **React** + **pdf2docx** + **JWT / httpOnly cookies**.

---

## Возможности

- 📄 Конвертация PDF → DOCX с сохранением текста, шрифтов, таблиц, списков
- 🔒 Аутентификация через JWT в httpOnly cookies (защита от XSS)
- 🛡️ CSRF-защита (Double-Submit Cookie pattern)
- 📦 Ограничение размера файла (50 МБ)
- ✅ Валидация MIME-типа через libmagic
- 📜 История конвертаций с повторным скачиванием
- 🔄 Drag-and-drop загрузка с прогресс-баром
- 🐳 Docker Compose для быстрого развёртывания

---

## Структура проекта

```
pdf2docx-app/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic Settings (env vars)
│   │   │   ├── database.py     # SQLAlchemy engine + session
│   │   │   └── security.py     # JWT, bcrypt, get_current_user_id
│   │   ├── models/
│   │   │   └── models.py       # User, ConversionTask ORM
│   │   ├── schemas/
│   │   │   └── schemas.py      # Pydantic request/response schemas
│   │   ├── services/
│   │   │   └── converter.py    # pdf2docx conversion logic
│   │   ├── routers/
│   │   │   ├── auth.py         # /auth/* endpoints
│   │   │   └── convert.py      # /convert, /download endpoints
│   │   └── main.py             # FastAPI app, CORS, CSRF middleware
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js       # Axios + CSRF + auto-refresh
│   │   ├── context/AuthContext.jsx
│   │   ├── components/
│   │   │   ├── Layout.jsx      # App shell with nav
│   │   │   ├── DropZone.jsx    # Drag-and-drop upload
│   │   │   ├── ConversionStatus.jsx  # Polling + download link
│   │   │   └── HistoryList.jsx # Past conversions table
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   └── HomePage.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

---

## API эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/auth/register` | Регистрация |
| `POST` | `/auth/login` | Вход (устанавливает cookies) |
| `POST` | `/auth/logout` | Выход (очищает cookies) |
| `GET` | `/auth/me` | Текущий пользователь |
| `POST` | `/auth/refresh` | Обновление access token |
| `POST` | `/convert` | Загрузить PDF (возвращает task_id) |
| `GET` | `/convert/{task_id}` | Статус конвертации |
| `GET` | `/convert/history` | История конвертаций |
| `GET` | `/download/{filename}` | Скачать DOCX |
| `GET` | `/csrf-token` | Получить CSRF token |
| `GET` | `/health` | Health check |

---

## Запуск через Docker Compose

```bash
# 1. Клонируйте / распакуйте проект
cd pdf2docx-app

# 2. Установите переменные окружения (или отредактируйте docker-compose.yml)
export JWT_SECRET="ваш-супер-секретный-ключ"
export CSRF_SECRET="ваш-csrf-секрет"

# 3. Запустите
docker-compose up --build

# Приложение доступно на http://localhost:80
# API документация: http://localhost:8000/docs
```

---

## Локальный запуск (без Docker)

### Backend

```bash
cd backend

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt

# Также нужна системная libmagic:
# Ubuntu/Debian: sudo apt-get install libmagic1
# macOS:         brew install libmagic

# Скопируйте и настройте .env
cp .env.example .env
# Отредактируйте .env — задайте JWT_SECRET, CSRF_SECRET и т.д.

# Запустите сервер
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

> Vite автоматически проксирует `/api/*` на `http://localhost:8000`.

---

## Безопасность

| Механизм | Реализация |
|----------|-----------|
| Хеширование паролей | bcrypt через passlib |
| JWT access token | httpOnly cookie, 30 мин |
| JWT refresh token | httpOnly cookie, 7 дней |
| CSRF защита | Double-Submit Cookie (`X-CSRF-Token` header) |
| CORS | Только FRONTEND_URL |
| Размер файла | Ограничение 50 МБ |
| MIME валидация | python-magic (libmagic) |
| Изоляция файлов | Пользователь видит только свои задачи |

---

## Переменные окружения (backend)

| Переменная | По умолчанию | Описание |
|-----------|-------------|---------|
| `JWT_SECRET` | `dev-secret-...` | 🔴 Сменить в production! |
| `CSRF_SECRET` | `dev-csrf-...` | 🔴 Сменить в production! |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Время жизни access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Время жизни refresh token |
| `DATABASE_URL` | SQLite | Строка подключения к БД |
| `FRONTEND_URL` | `http://localhost:5173` | CORS origin |
| `MAX_FILE_SIZE_MB` | `50` | Макс. размер загружаемого файла |

---

## Требования к системе

- Python 3.10+
- Node.js 18+
- `libmagic` (системная библиотека)
- Docker + Docker Compose (для контейнерного запуска)
