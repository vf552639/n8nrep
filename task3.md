
ТЕХНИЧЕСКОЕ ЗАДАНИЕ
5 доработок пайплайна и фронтенда
SEO Content Generator
Март 2026  |  v1.1


#	Задача	Затрагивает
1	Тип страницы (homepage / category)	DB, API, Pipeline, Frontend
2	Переменная {{competitors_headers}} в промпты	Pipeline, Frontend
3	Подпеременные intent/Taxonomy/Attention/structura	Pipeline, Frontend
4	Переменная {{merged_markdown}} + {{avg_word_count}}	Pipeline, Frontend
5	Тумблер вкл/выкл агентов в pipeline	DB, API, Pipeline, Frontend
 
1. Тип страницы (page_type)
Нужно добавить новое поле «page_type» ко всем задачам. Тип страницы влияет на то, какую структуру должна иметь статья — главная страница vs категория vs обычная статья.

1.1. База данных
Миграция Supabase:
ALTER TABLE tasks ADD COLUMN page_type VARCHAR(50) NOT NULL DEFAULT 'article';

Допустимые значения:
•	homepage — главная страница сайта
•	category — страница категории
•	article — обычная статья (по умолчанию)
⚠️ В будущем могут добавиться другие типы, поэтому не делать жёсткий ENUM в PostgreSQL — использовать VARCHAR(50).

1.2. Модель SQLAlchemy
Файл: app/models/task.py
Добавить поле после language:
page_type = Column(String(50), nullable=False, default='article')

1.3. API
Файл: app/api/tasks.py
В класс TaskCreate добавить:
page_type: str = 'article'
В create_task() передавать page_type в модель Task.
В get_tasks() и get_task() добавить page_type в response dict.

1.4. Pipeline
Файл: app/services/pipeline.py
Добавить в analysis_vars и template_vars:
"page_type": task.page_type
Теперь в любом промпте можно использовать {{page_type}}.

1.5. Frontend
Файл: frontend/app.py
В форме «Создать новую задачу» (функция render_tasks), после поля «Ключевое слово» добавить selectbox:
page_type = st.selectbox("Тип страницы*", options=["article", "homepage", "category"])
Передавать в post_data("tasks/", {..., "page_type": page_type}).
В таблице задач добавить колонку page_type.
В разделе «Доступные переменные» (в промптах) добавить строку: {{page_type}} — Тип страницы (homepage, category, article).
В CSV-импорте (массовый импорт): добавить опциональный столбец page_type (default article).
 
2. Переменная {{competitors_headers}}
Сейчас структура h1-h6 конкурентов хранится в task.outline['scrape_info']['headers'] и передаётся в context как часть base_context строкой. Но не доступна как отдельная переменная {{competitors_headers}} для промптов.

2.1. Pipeline
Файл: app/services/pipeline.py

Сейчас в analysis_vars нет этой переменной. Нужно добавить в analysis_vars (после строки "site_name"):
"competitors_headers": json.dumps(headers_info, ensure_ascii=False)

И также добавить в template_vars (после строки "site_name"):
"competitors_headers": json.dumps(task.outline.get('scrape_info', {}).get('headers', []), ensure_ascii=False)

2.2. Frontend
Файл: frontend/app.py
В разделе «Доступные переменные» (task_vars в render_prompts) добавить строку:
("competitors_headers", "Структура h1-h6 конкурентов (JSON)")

2.3. Пример использования
Теперь в промпте «Анализ конкурентов» можно написать:
Проанализируй структуру заголовков конкурентов: {{competitors_headers}}
 
3. Подпеременные intent / Taxonomy / Attention / structura
Сейчас результат агента «AI анализ структуры» сохраняется как цельная строка в {{result_ai_structure_analysis}}. Нужно заставить его отдавать JSON и разбирать на 4 отдельные переменные.

3.1. Требуемый JSON-формат ответа агента
Агент ai_structure_analysis должен возвращать строго JSON:
{
  "intent": "строка — поисковый интент",
  "Taxonomy": "строка — таксономия запроса",
  "Attention": "строка — на что обратить внимание",
  "structura": "строка — рекомендованная структура"
}

3.2. Pipeline — изменения
Файл: app/services/pipeline.py

Этап 3a («AI анализ структуры») — сейчас вызывается без response_format. Нужно:

1.	Добавить response_format={"type": "json_object"} в вызов call_agent для ai_structure_analysis (аналогично тому, как сделано для final_structure_analysis)
2.	После получения ответа — распарсить JSON и добавить 4 подпеременные в analysis_vars и позже в template_vars:
ai_struct_data = json.loads(ai_structure)
analysis_vars["intent"] = ai_struct_data.get("intent", "")
analysis_vars["Taxonomy"] = ai_struct_data.get("Taxonomy", "")
analysis_vars["Attention"] = ai_struct_data.get("Attention", "")
analysis_vars["structura"] = ai_struct_data.get("structura", "")
3.	То же самое дублировать в template_vars (ниже по коду, где template_vars конструируется):
"intent": task.outline.get("ai_structure_parsed", {}).get("intent", ""),
"Taxonomy": task.outline.get("ai_structure_parsed", {}).get("Taxonomy", ""),
"Attention": task.outline.get("ai_structure_parsed", {}).get("Attention", ""),
"structura": task.outline.get("ai_structure_parsed", {}).get("structura", ""),
4.	Сохранять распарсенный дикт в outline_data для персистентности:
outline_data["ai_structure_parsed"] = ai_struct_data

⚠️ Обработка ошибок: если json.loads() падает (агент вернул не JSON) — логировать warning, использовать весь ответ как result_ai_structure_analysis целиком, а подпеременные оставить пустыми строками. Не падать.

3.3. Frontend — добавить в список переменных
Файл: frontend/app.py, функция render_prompts, список result_vars
Добавить 4 новые строки СРАЗУ ПОСЛЕ строки result_ai_structure_analysis:
("intent", "Поисковый интент (из AI анализа)"),
("Taxonomy", "Таксономия запроса (из AI анализа)"),
("Attention", "На что обратить внимание (из AI анализа)"),
("structura", "Рекомендованная структура (из AI анализа)"),
Эти переменные должны отображаться в UI как подпункты к {{result_ai_structure_analysis}} — с отступом или индикатором «└ подпеременная».
 
4. Переменные {{merged_markdown}} и {{avg_word_count}}
Сейчас объединённый текст конкурентов хранится в task.competitors_text и среднее кол-во слов в task.outline['scrape_info']['avg_words']. Но эти данные недоступны как {{...}} переменные в промптах.

4.1. Pipeline
Файл: app/services/pipeline.py
Добавить в analysis_vars:
"merged_markdown": task.competitors_text or ""
"avg_word_count": str(avg_words)

Добавить в template_vars:
"merged_markdown": task.competitors_text or ""
"avg_word_count": str(task.outline.get('scrape_info', {}).get('avg_words', 800))

⚠️ Объём может быть большим (50-200KB текста). merged_markdown уже хранится в БД в поле competitors_text — ничего дополнительно сохранять не надо. Но когда пользователь вставляет {{merged_markdown}} в промпт, это может съесть огромный контекст. Это нормально — это ответственность автора промпта.

4.2. Frontend
Файл: frontend/app.py, функция render_prompts
Добавить в task_vars:
("merged_markdown", "Объединённый текст конкурентов (внимание: большой объём!)"),
("avg_word_count", "Среднее кол-во слов у конкурентов"),
 
5. Тумблер вкл/выкл агентов в pipeline
Нужна возможность отключить любой агент из пайплайна без удаления промпта. Например, отключить «Мнение читателя», если он не нужен.

5.1. База данных
Миграция Supabase:
ALTER TABLE prompts ADD COLUMN skip_in_pipeline BOOLEAN NOT NULL DEFAULT false;

Логика:
•	skip_in_pipeline = false — агент работает как обычно (по умолчанию)
•	skip_in_pipeline = true — агент пропускается, его результат = пустая строка

⚠️ is_active уже есть в модели Prompt, но оно отвечает за версионирование (active = какая версия промпта используется). skip_in_pipeline — это другое: вкл/выкл всего этапа. Не путать!

5.2. Модель SQLAlchemy
Файл: app/models/prompt.py
Добавить поле:
skip_in_pipeline = Column(Boolean, default=False, nullable=False)

5.3. API
Файл: app/api/prompts.py
В PromptCreate добавить:
skip_in_pipeline: bool = False
В GET /prompts/ добавить skip_in_pipeline в response.
В GET /prompts/{id} добавить skip_in_pipeline в response.
В POST /prompts/ передавать skip_in_pipeline в модель.

5.4. Pipeline — пропуск агента
Файл: app/services/pipeline.py

Изменить функцию call_agent — добавить проверку в самом начале:

def call_agent(db, agent_name, context, response_format=None, variables=None):
    prompt = get_prompt_obj(db, agent_name)
    if prompt.skip_in_pipeline:
        print(f"Agent {agent_name} skipped (toggle off)")
        return ""
    # ... далее как раньше

Логика простая: если skip = true, возвращаем пустую строку. Pipeline продолжает работать, просто результат этого агента будет пустым. Следующие агенты получат пустую переменную.

Какие агенты НЕЛЬЗЯ отключать:
Агент	Можно откл.	Почему
ai_structure_analysis	✅ Да	Но подпеременные будут пустыми
chunk_cluster_analysis	✅ Да	
competitor_structure_analysis	✅ Да	
final_structure_analysis	❌ Нет	Без outline pipeline упадёт
primary_generation	❌ Нет	Без генерации нет статьи
competitor_comparison	✅ Да	
reader_opinion	✅ Да	
interlinking_citations	✅ Да	
improver	✅ Да	
final_editing	✅ Да	
html_structure	✅ Да	
meta_generation	❌ Нет	Без мета статья не сохранится

⚠️ В UI можно показывать предупреждение, если пользователь пытается отключить критичный агент. Но не блокировать — пусть решает сам.

5.5. Frontend — тумблер
Файл: frontend/app.py, функция render_prompts

Внутри каждого таба агента (agent_tabs[i]), ПЕРЕД формой, добавить тумблер:
skip = st.toggle(
    "Пропускать этот этап в pipeline",
    value=full_prompt.get("skip_in_pipeline", False),
    key=f"skip_{agent}"
)

Визуальное оформление:
•	Когда тумблер включён (пропуск) — показать st.warning("Этот агент будет пропущен при генерации")
•	Когда выключен — ничего не показывать
•	В заголовке таба добавить индикатор: если агент отключён, показывать «⏸» рядом с названием

При сохранении промпта (POST /prompts/) передавать значение тумблера:
"skip_in_pipeline": skip

Тумблер должен стоять ОТДЕЛЬНО от формы (не внутри st.form), чтобы реагировать мгновенно. Но сохраняться в БД должен при нажатии кнопки «Сохранить».
 
6. Сводка по файлам
Файл	Что менять
Supabase (SQL)	ALTER TABLE tasks ADD COLUMN page_type; ALTER TABLE prompts ADD COLUMN skip_in_pipeline;
app/models/task.py	+1 поле: page_type
app/models/prompt.py	+1 поле: skip_in_pipeline
app/api/tasks.py	page_type в TaskCreate, create_task, get_tasks, get_task, bulk import
app/api/prompts.py	skip_in_pipeline в PromptCreate, GET, POST endpoints
app/services/pipeline.py	5 изменений: page_type в vars; competitors_headers в vars; парсинг JSON intent/Taxonomy/Attention/structura; merged_markdown+avg_word_count в vars; проверка skip в call_agent
frontend/app.py	selectbox page_type в задачах; новые переменные в справочнике; тумблер skip в промптах

6.1. Миграции (2 команды SQL)
ALTER TABLE tasks ADD COLUMN page_type VARCHAR(50) NOT NULL DEFAULT 'article';
ALTER TABLE prompts ADD COLUMN skip_in_pipeline BOOLEAN NOT NULL DEFAULT false;

6.2. Полный список новых переменных для промптов
Переменная	Описание
{{page_type}}	Тип страницы: homepage, category, article
{{competitors_headers}}	Структура h1-h6 конкурентов (JSON)
{{intent}}	Поисковый интент (подпеременная AI анализа)
{{Taxonomy}}	Таксономия запроса (подпеременная AI анализа)
{{Attention}}	На что обратить внимание (подпеременная AI анализа)
{{structura}}	Рекомендованная структура (подпеременная AI анализа)
{{merged_markdown}}	Объединённый текст конкурентов (большой объём!)
{{avg_word_count}}	Среднее кол-во слов у конкурентов
