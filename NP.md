





ТЕХНИЧЕСКОЕ ЗАДАНИЕ
на разработку веб-приложения
Система автогенерации SEO-контента

Версия 1.0  |  Март 2026
Ниша: iGaming
Замена n8n workflow на standalone Python-приложение
 
1. Общее описание проекта
Необходимо разработать веб-приложение на Python, которое полностью заменяет существующий n8n-воркфлоу для автоматической генерации SEO-оптимизированных статей в нише iGaming.

Почему отказ от n8n
•	Частые сбои при длинных пайплайнах (10+ LLM-вызовов последовательно)
•	Невозможность нормальной отладки: ошибки в промежуточных нодах сложно диагностировать
•	Лимиты по памяти и таймаутам при работе с большими текстами конкурентов
•	Сложность масштабирования: 10 сайтов с разными шаблонами трудно обслуживать визуально
•	Зависимость от облачного сервиса n8n cloud (стоимость, uptime)

Что должна делать система
Принимать ключевое слово + ГЕО + язык, автоматически проходить полный цикл: сбор SERP, парсинг конкурентов, анализ структуры, генерация контента через LLM-агентов, редактура, генерация HTML-страницы по шаблону сайта, сохранение результата.
 
2. Технологический стек
Компонент	Технология	Зачем
Backend & API	FastAPI (Python 3.11+)	Асинхронный, быстрый, авто-документация через Swagger
Админ-панель (UI)	React (Vite) или Streamlit	Кастомный интерфейс управления задачами
База данных	Supabase (PostgreSQL)	Уже используется в текущем n8n-проекте
ORM	SQLAlchemy + Alembic	Модели, миграции
Фоновые задачи	Celery + Redis	Генерация занимает 2–10 мин, нельзя блокировать HTTP
LLM-провайдер	OpenRouter API (GPT-5, Claude Sonnet 4.5)	Через единый API к разным моделям
SERP-данные	DataForSEO API + SerpAPI (fallback)	DataForSEO — основной. SerpAPI — автоматический fallback
Парсинг HTML	Serper Webcrawler или HTTP + BeautifulSoup4	Извлечение контента конкурентов
Векторная БД	Supabase pgvector (уже есть)	Хранение экспертных знаний для RAG
Контейнеризация	Docker + docker-compose	Деплой на VPS одной командой
 
3. Архитектура базы данных (Supabase)
В Supabase необходимо создать следующие таблицы. Миграции через Alembic.

3.1. Таблица tasks
Главная таблица заданий на генерацию контента.
Поле	Тип	Описание
id	UUID, PK	Уникальный идентификатор задачи
main_keyword	VARCHAR(500)	Главное ключевое слово
country	VARCHAR(10)	Код страны (DE, BR, IN...)
language	VARCHAR(10)	Код языка (de, pt, en...)
target_site_id	UUID, FK → sites.id	Для какого сайта генерируется статья
author_id	UUID, FK → authors.id, nullable	Привязка к автору (стиль, промпт)
status	ENUM	pending | processing | completed | failed
error_log	TEXT, nullable	Лог ошибки если status=failed
serp_data	JSONB, nullable	Сырые данные SERP (DataForSEO response)
competitors_text	TEXT, nullable	Объединённый текст конкурентов
outline	JSONB, nullable	Структура статьи (план от аналитика)
priority	INTEGER, default 0	Приоритет в очереди (0=обычный, 1=высокий)
retry_count	INTEGER, default 0	Сколько раз задача перезапускалась
created_at	TIMESTAMP	Время создания
updated_at	TIMESTAMP	Время последнего обновления

3.2. Таблица generated_articles
Поле	Тип	Описание
id	UUID, PK	
task_id	UUID, FK → tasks.id	Привязка к заданию
title	VARCHAR(300)	Meta Title
description	TEXT	Meta Description
html_content	TEXT	Готовая статья (чистый HTML-контент без шаблона)
full_page_html	TEXT, nullable	Полная HTML-страница с шаблоном сайта
word_count	INTEGER	Количество слов в статье
created_at	TIMESTAMP	Время завершения генерации

3.3. Таблица sites
Реестр сайтов (10 сайтов), для которых генерируется контент.
Поле	Тип	Описание
id	UUID, PK	
name	VARCHAR(200)	Название сайта
domain	VARCHAR(200)	Домен (example.com)
country	VARCHAR(10)	Основная страна
language	VARCHAR(10)	Основной язык
is_active	BOOLEAN, default true	Активен ли сайт

3.4. Таблица site_templates
HTML-шаблоны страниц для каждого сайта. При генерации выбирается рандомный шаблон с минимальным count.
Поле	Тип	Описание
id	UUID, PK	
site_id	UUID, FK → sites.id	К какому сайту относится
template_name	VARCHAR(200)	Название шаблона
html_template	TEXT	HTML-код шаблона (с плейсхолдерами)
pages_config	JSONB	Конфиг навигации (страницы, URL’ы)
usage_count	INTEGER, default 0	Сколько раз использован
is_active	BOOLEAN, default true	

3.5. Таблица authors
Виртуальные авторы со стилями написания (перенос из текущего Supabase).
Поле	Тип	Описание
id	UUID, PK	
name	VARCHAR(200)	Имя автора
country	VARCHAR(10)	Страна автора
language	VARCHAR(10)	Язык автора
style_prompt	TEXT	Промпт стиля написания
bio	TEXT, nullable	Биография для подстановки в шаблон

3.6. Таблица prompts
Все промпты для LLM-агентов хранятся в БД, а не в коде. Это позволяет редактировать их из админки без деплоя.
Поле	Тип	Описание
id	UUID, PK	
agent_name	VARCHAR(100)	Имя агента: analyst, writer, editor, meta_generator, html_generator
version	INTEGER, default 1	Версия промпта
is_active	BOOLEAN, default true	Только один активный промпт на агента
prompt_text	TEXT	Текст промпта с плейсхолдерами {keyword}, {language} и т.д.
model	VARCHAR(100)	Какую модель использовать (openai/gpt-5, anthropic/claude-sonnet-4.5)
max_tokens	INTEGER	Лимит токенов для этого агента
temperature	FLOAT, default 0.7	
updated_at	TIMESTAMP	
 
4. Пайплайн генерации контента
Это ядро системы. Каждый этап соответствует группе нод из текущего n8n-воркфлоу. Celery Worker выполняет эти этапы последовательно.

4.1. Этап 1: Сбор SERP-данных (Research)
Аналог в n8n: ноды «Get Google SERPs» + «Get Bing SERPs» (DataForSEO)

1.	Основной провайдер: POST-запрос к DataForSEO API /v3/serp/google/organic/live/advanced
2.	Параметры: keyword, location_code (по country), language_code, depth: 10
3.	Fallback: если DataForSEO вернул ошибку или пустой результат — автоматически переключиться на SerpAPI (/search, engine=google, тот же keyword + location)
4.	Сохранить сырой JSON-ответ в tasks.serp_data (с пометкой source: dataforseo или serpapi)
5.	Извлечь: URLs конкурентов (ТОП-10), People Also Ask, Related Searches

Обработка ошибок: DataForSEO: retry 3 раза (30s, 2m, 5m). Если после 3 попыток ошибка — fallback на SerpAPI. Если SerpAPI тоже упал — status=failed, error_log=«Both SERP providers failed».

4.2. Этап 2: Парсинг конкурентов (Scraping)
Аналог в n8n: ноды «Serper.Webcrawler» + «HTML» (Extract h1-h6 + body)

1.	Из SERP-данных взять URLs ТОП-10 (максимум 10, минимум 5)
2.	Для каждого URL: HTTP GET запрос (timeout 15s, User-Agent: Googlebot)
3.	Из HTML извлечь: заголовки h1-h6 (структура), body text (основной контент)
4.	Подсчитать среднее количество слов по всем конкурентам (ems)
5.	Объединить все тексты в merged_markdown
6.	Сохранить competitors_text в таблицу tasks

Важно: если URL возвращает 403/Cloudflare — пропустить, не падать. Минимум 3 успешных парсинга для продолжения.

4.3. Этап 3: Анализ и проектирование структуры
Аналог в n8n: 4 последовательных LLM-вызова (Gemini 2.5 Pro)

Вызов 1: Анализ интентов и таксономии
LLM получает: keyword, PAA, related searches, country, language. Возвращает: поисковый интент, таксономию запроса, ключевые сущности.

Вызов 2: Анализ структуры конкурентов
LLM получает: заголовки h1-h6 всех конкурентов. Возвращает: общие паттерны структуры, уникальные секции, рекомендации.

Вызов 3: Анализ кластера запросов
LLM получает: keyword + related keywords + PAA. Возвращает: LSI-ключи, семантические кластеры, обязательные топики.

Вызов 4: Финальный синтез (Outline)
LLM получает: результаты вызовов 1–3 + среднее кол-во слов. Возвращает: готовый план статьи (JSON) с заголовками, подзаголовками, указаниями по контенту для каждой секции. Сохраняется в tasks.outline.

4.4. Этап 4: Генерация контента
Аналог в n8n: «Первичная генерация» (Agent + GPT-5 + Supabase Vector Store)

1.	LLM (Writer Agent) получает: outline, стиль автора, язык, ems (целевой объём слов)
2.	Если подключён RAG: из Supabase Vector Store подтягиваются экспертные знания по теме
3.	Генерация идёт блоками (по секциям outline), чтобы не превышать контекст
4.	Результат: полный HTML-текст статьи с тегами h2, h3, ul, ol, strong, p

4.5. Этап 5: Аудит и улучшение
Аналог в n8n: ноды «Лучше ли наша статья» + «Отзыв читателя» + «Внедрение улучшений»

1.	LLM (Reviewer) сравнивает сгенерированный текст с текстами конкурентов: чего не хватает?
2.	LLM (Reader) оценивает с позиции пользователя: понятно ли, есть ли вода, покрыты ли боли
3.	LLM (Improver) получает оба отзыва и дорабатывает текст: добавляет внутренние ссылки, цитаты, кейсы

4.6. Этап 6: Финальная редактура
Аналог в n8n: «Финальная редактура и сверка»

1.	LLM (Editor) проверяет: HTML-валидность тегов, SEO-спам (переоптимизация), LSI-покрытие
2.	Корректирует: убирает повторы, чистит разметку, проверяет логическую связность
3.	Результат сохраняется в generated_articles.html_content

4.7. Этап 7: Мета-теги
1.	Отдельный LLM-вызов: генерация Meta Title (до 60 символов) и Meta Description (до 160 символов)
2.	Сохранение в generated_articles.title и generated_articles.description

4.8. Этап 8: Генерация полной HTML-страницы
Аналог в n8n: «Basic LLM Chain (генерация HTML)» + Supabase site_templates

Берётся рандомный шаблон из site_templates (с минимальным usage_count). LLM вставляет сгенерированный контент в шаблон, адаптирует навигацию, стили. Результат — full_page_html.
 
5. Административная панель (Вкладки UI)
Основной интерфейс для управления системой. Каждая вкладка — отдельная страница.

5.1. Вкладка «Дашборд» (Dashboard)
•	Общая статистика: всего задач, в работе, завершено, с ошибками
•	График генерации по дням (за последние 30 дней)
•	Текущая очередь Celery: сколько задач ждёт, сколько выполняется
•	Последние 10 завершённых задач с быстрым доступом к результату
•	Статус Redis, Celery workers (online/offline)

5.2. Вкладка «Задачи» (Tasks)
•	Таблица всех задач с фильтрами: по статусу, сайту, стране, дате
•	Создание задачи: форма (keyword, country, language, target_site) + кнопка «Добавить»
•	Массовый импорт: загрузка CSV (keyword, country, language, site_name — по столбцам)
•	Действия над задачей: Перезапустить (если failed), Удалить, Посмотреть лог ошибки
•	Цветовая индикация статусов: серый=pending, синий=processing, зелёный=completed, красный=failed

5.3. Вкладка «Статьи» (Articles)
•	Список всех сгенерированных статей с поиском и фильтрацией
•	Просмотр статьи: рендеринг HTML прямо в браузере (iframe или sanitized HTML)
•	Просмотр исходного кода HTML (с подсветкой синтаксиса)
•	Мета-теги (Title, Description) отображаются рядом со статьёй
•	Кнопки: Копировать HTML, Скачать .html файл, Открыть превью в новой вкладке
•	Показывать word_count и к какому сайту/шаблону привязана

5.4. Вкладка «Сайты» (Sites)
•	CRUD для таблицы sites: добавить/редактировать/удалить сайт
•	Для каждого сайта: список привязанных шаблонов с usage_count
•	Загрузка нового шаблона: текстовое поле для HTML + поле для pages_config (JSON)
•	Превью шаблона (iframe)

5.5. Вкладка «Авторы» (Authors)
•	CRUD для таблицы authors
•	Редактирование style_prompt с превью (как будет выглядеть в промпте)
•	Привязка автора к стране/языку

5.6. Вкладка «Промпты» (Prompts)
•	Список всех промптов по агентам (analyst, writer, editor, reviewer, reader, improver, meta_generator, html_generator)
•	Редактор промпта с подсветкой плейсхолдеров ({keyword}, {language}, {outline} и т.д.)
•	Версионирование: при сохранении создаётся новая версия, старая деактивируется
•	Привязка модели и параметров (model, max_tokens, temperature) к каждому промпту
•	Кнопка «Тест»: отправить промпт с тестовыми данными и увидеть ответ прямо в админке

5.7. Вкладка «Настройки» (Settings)
•	API-ключи: OpenRouter, DataForSEO, SerpAPI (fallback), Serper/Firecrawl (редактируемые, зашифрованные)
•	Настройки Celery: concurrency, retry policy, таймауты
•	Настройки парсинга: max URLs to scrape, timeout, min successful parses
•	Логи: последние 100 записей из Celery с фильтрацией по task_id
 
6. API-эндпоинты (FastAPI)
REST API для взаимодействия фронтенда с бэкендом. Swagger-документация генерируется автоматически.

Метод	Эндпоинт	Описание
POST	/api/tasks	Создать новую задачу (single)
POST	/api/tasks/bulk	Массовое создание задач из CSV
GET	/api/tasks	Список задач (с пагинацией, фильтрами)
GET	/api/tasks/{id}	Детали задачи + промежуточные данные
POST	/api/tasks/{id}/retry	Перезапустить failed-задачу
DELETE	/api/tasks/{id}	Удалить задачу
GET	/api/articles	Список статей
GET	/api/articles/{id}	Статья с HTML-контентом
GET	/api/articles/{id}/download	Скачать .html файл
CRUD	/api/sites	Управление сайтами
CRUD	/api/sites/{id}/templates	Управление шаблонами сайта
CRUD	/api/authors	Управление авторами
CRUD	/api/prompts	Управление промптами
POST	/api/prompts/{id}/test	Тестовый запуск промпта
GET	/api/dashboard/stats	Статистика для дашборда
GET	/api/dashboard/queue	Состояние очереди Celery
GET	/api/settings	Текущие настройки
PUT	/api/settings	Обновить настройки
 
7. Обработка ошибок и Retry Policy

7.1. Retry-стратегия для Celery-тасок
Тип ошибки	Retry	Задержка	Действие после max retries
LLM timeout (502, 504)	3 раза	30s → 2m → 5m	status=failed, error_log
LLM rate limit (429)	5 раз	60s → 120s → 300s	status=failed, «Rate limit exceeded»
DataForSEO ошибка	3 раза	30s → 2m → 5m	Fallback на SerpAPI. Если SerpAPI тоже — failed
Парсинг: все URLs 403	0	—	status=failed, «All competitors blocked»
Парсинг: <3 успешных	1 раз	60s (другие URLs)	Продолжить с тем что есть (если ≥1)
Неизвестная ошибка	1 раз	30s	status=failed, полный traceback в error_log

7.2. Уведомления об ошибках
•	Telegram-бот: при status=failed отправлять уведомление в Telegram-группу (chat_id уже настроен)
•	В дашборде: красный бейдж с количеством failed-задач
•	Email (опционально, Phase 2)
 
8. Конфигурация и ENV

Все секреты и настройки хранятся в .env файле. Пример:

# Database
SUPABASE_DB_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0

# LLM
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=openai/gpt-5
ANALYST_MODEL=google/gemini-2.5-pro

# SERP & Scraping
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
SERPER_API_KEY=...
SERPAPI_KEY=...                     # Fallback для DataForSEO

# Telegram notifications
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-1003841650237

# Celery
CELERY_CONCURRENCY=2
CELERY_TASK_TIME_LIMIT=900  # 15 min max per task
 
9. Этапы разработки (Roadmap)

Фаза 1: Инфраструктура (1–2 дня)
•	Инициализация FastAPI проекта, структура папок
•	Подключение к Supabase через SQLAlchemy
•	Определение моделей БД, генерация миграций Alembic
•	Настройка Celery + Redis
•	Docker + docker-compose (app, celery worker, redis)

Фаза 2: Core Pipeline (3–5 дней)
•	Перенос логики SERP-запросов (DataForSEO)
•	Модуль парсинга конкурентов (HTTP + BeautifulSoup)
•	Модуль LLM-вызовов (обёртка над OpenRouter API с retry)
•	Реализация всех 8 этапов пайплайна как Celery-задачи
•	Перенос промптов из n8n в таблицу prompts

Фаза 3: Админ-панель (3–4 дня)
•	Фронтенд: React (Vite) или Streamlit
•	Все 7 вкладок из раздела 5
•	Подключение к API-эндпоинтам
•	Рендеринг HTML-статей, редактор промптов

Фаза 4: Тестирование и деплой (1–2 дня)
•	Прогон полного цикла: ввод ключа → ожидание → готовая статья
•	Тест retry policy (отключить API, проверить перезапуски)
•	Тест массового импорта (50 ключей одновременно)
•	Деплой на VPS (Ubuntu) через docker-compose up -d
•	Настройка Nginx reverse proxy + SSL

Деплой-стратегия
Локальная разработка и тесты
На этапе тестирования бэкенд поднимается локально на компьютере разработчика через docker-compose up -d. Фронтенд (React) работает на localhost:5173 (Vite dev server), бэкенд на localhost:8000. Supabase остаётся облачным — подключение через SUPABASE_DB_URL в .env.

Продакшен
•	Фронтенд (React) → Vercel: бесплатный хостинг, CDN, автодеплой из GitHub
•	Бэкенд (FastAPI + Celery + Redis) → VPS (DigitalOcean/Hetzner, Ubuntu) через docker-compose
•	Фронтенд дёргает API бэкенда по https://api.yourdomain.com (Nginx + SSL на VPS)
•	CORS: бэкенд разрешает запросы только с домена фронтенда на Vercel
 
10. Структура проекта (файлы)

seo-content-generator/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                  # FastAPI app, роутеры
│   ├── config.py                # Pydantic Settings, загрузка .env
│   ├── database.py              # SQLAlchemy engine, session
│   ├── models/
│   │   ├── task.py              # Task model
│   │   ├── article.py           # GeneratedArticle model
│   │   ├── site.py              # Site, SiteTemplate models
│   │   ├── author.py            # Author model
│   │   └── prompt.py            # Prompt model
│   ├── api/
│   │   ├── tasks.py             # POST/GET/DELETE /api/tasks
│   │   ├── articles.py          # GET /api/articles
│   │   ├── sites.py             # CRUD /api/sites
│   │   ├── authors.py           # CRUD /api/authors
│   │   ├── prompts.py           # CRUD + test /api/prompts
│   │   ├── dashboard.py         # GET /api/dashboard/*
│   │   └── settings.py          # GET/PUT /api/settings
│   ├── services/
│   │   ├── serp.py              # DataForSEO + SerpAPI fallback
│   │   ├── scraper.py           # HTTP scraping + BS4 parsing
│   │   ├── llm.py               # OpenRouter wrapper + retry
│   │   ├── pipeline.py          # Главный пайплайн (этапы 1–8)
│   │   ├── template_engine.py   # Выбор шаблона + генерация HTML
│   │   └── notifier.py          # Telegram уведомления
│   └── workers/
│       ├── celery_app.py        # Celery config
│       └── tasks.py             # @celery.task definitions
├── frontend/                        # React app (if used)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── tests/
    ├── test_pipeline.py
    └── test_api.py
 
11. Критерии приёмки

3.	Полный цикл работает: ввод ключа через UI → ожидание → готовая HTML-статья в базе и доступна в UI
4.	Retry policy работает: при 502 от LLM задача автоматически перезапускается
5.	Telegram-уведомления приходят при failed-задачах
6.	Массовый импорт CSV работает (минимум 50 ключей за раз)
7.	Промпты редактируются из UI без деплоя
8.	Шаблоны сайтов применяются корректно, usage_count инкрементируется
9.	Docker-compose поднимает всю систему одной командой на чистом Ubuntu VPS
10.	Swagger-документация API доступна по /docs


Конец документа. Версия 1.0
