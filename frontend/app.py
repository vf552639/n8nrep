import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.environ.get("API_URL", "http://web:8000/api")

st.set_page_config(page_title="SEO Content Generator", layout="wide")

st.markdown("""
<style>
    /* ===== GLOBAL ===== */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 4px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    
    /* ===== FORMS ===== */
    .stButton > button[kind="primary"] {
        background-color: #4F46E5;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #4338CA;
    }
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    .stButton > button[kind="primary"][data-testid*="delete"] {
        background-color: #DC2626;
    }
    
    /* ===== METRICS ===== */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* ===== DATAFRAMES ===== */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* ===== TEXT AREAS ===== */
    textarea {
        font-size: 14px !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    }
    
    /* ===== STATUS BADGES ===== */
    .status-pending { color: #6B7280; background: #F3F4F6; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .status-processing { color: #2563EB; background: #DBEAFE; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .status-completed { color: #059669; background: #D1FAE5; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    .status-failed { color: #DC2626; background: #FEE2E2; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
    
    /* ===== TASK1.md FIXES ===== */
    div[data-testid="stTextInput"], 
    div[data-testid="stSelectbox"], 
    div[data-testid="stTextArea"], 
    div[data-testid="stNumberInput"] {
        margin-bottom: 24px !important;
    }
    div[data-testid="column"] {
        padding-right: 12px !important;
        padding-left: 4px !important;
    }
    div[data-testid="stForm"] div[data-testid="column"]:first-child {
        border-right: 1px solid rgba(0,0,0,0.06) !important;
    }
    div[data-testid="column"] h3 {
        border-bottom: 2px solid rgba(0,0,0,0.06) !important;
        padding-bottom: 8px !important;
    }
    label {
        margin-top: 8px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stFormSubmitButton"] > button {
        margin-top: 16px;
    }
    div[data-testid="metric-container"] {
        background-color: #f8f9fb;
        border: 1px solid #e8eaed;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

def fetch_data(endpoint: str):
    with st.spinner("⏳ Загрузка..."):
        try:
            r = requests.get(f"{API_URL}/{endpoint}")
            if r.status_code == 200:
                return r.json()
            st.error(f"Error fetching {endpoint}: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
    return None

def post_data(endpoint: str, data: dict):
    with st.spinner("⚙️ Сохранение..."):
        try:
            r = requests.post(f"{API_URL}/{endpoint}", json=data)
            if r.status_code in (200, 201):
                return r.json()
            st.error(f"Error posting to {endpoint}: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
    return None

def delete_data(endpoint: str):
    with st.spinner("🗑️ Удаление..."):
        try:
            r = requests.delete(f"{API_URL}/{endpoint}")
            if r.status_code == 200:
                return True
            st.error(f"Error deleting {endpoint}: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")
    return False

@st.cache_data(ttl=3600)
def get_openrouter_models():
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if r.status_code == 200:
            data = r.json()
            models = sorted([m["id"] for m in data.get("data", [])])
            return models
    except Exception:
        pass
    # Fallback list if API fails
    return [
        "openai/gpt-4o-mini",
        "openai/gpt-4o",
        "anthropic/claude-3-5-sonnet",
        "anthropic/claude-3-haiku",
        "google/gemini-flash-1.5",
        "meta-llama/llama-3-8b-instruct"
    ]

# ----- TAB: DASHBOARD -----
def render_dashboard():
    st.header("📊 Дашборд")
    stats = fetch_data("dashboard/stats")
    if stats:
        t_stats = stats.get("tasks", {})
        
        cols = st.columns(5, gap="medium")
        metrics = [
            ("Всего", t_stats.get("total", 0), None),
            ("В работе", t_stats.get("processing", 0), "🔵"),
            ("Завершено", t_stats.get("completed", 0), "🟢"),
            ("Ошибки", t_stats.get("failed", 0), "🔴"),
            ("Ожидают", t_stats.get("pending", 0), "⚪"),
        ]
        for i, (label, val, icon) in enumerate(metrics):
            with cols[i]:
                prefix = f"{icon} " if icon else ""
                st.metric(f"{prefix}{label}", val)
        
        st.markdown("")
        col_site, col_celery = st.columns(2)
        with col_site:
            st.metric("🌐 Сайтов", stats.get("sites", 0))
        with col_celery:
            q_stats = fetch_data("dashboard/queue")
            if q_stats:
                online = q_stats.get("celery_workers_online")
                st.metric("Celery Workers", "🟢 Online" if online else "🔴 Offline")

# ----- TAB: TASKS -----
def render_tasks():
    st.header("Задачи на генерацию")
    
    with st.expander("Создать новую задачу"):
        authors = fetch_data("authors/") or []
        
        # Build unique lists for country and language
        countries = list(set([a.get("country") for a in authors if a.get("country")]))
        languages = list(set([a.get("language") for a in authors if a.get("language")]))
        
        countries.sort()
        languages.sort()
        
        kw = st.text_input("Ключевое слово (Keyword)*")
        
        col_geo, col_lang = st.columns(2, gap="medium")
        geo = col_geo.selectbox("Страна (Code, e.g. US, DE)*", options=[""] + countries)
        lang = col_lang.selectbox("Язык (e.g. en, de)*", options=[""] + languages)
        
        site_str = st.text_input("Целевой сайт (домен)*")
        page_type = st.selectbox("Тип страницы*", options=["article", "homepage", "category"])
        
        # Author selection: blocked if geo/lang not selected
        author_options = {"Авто (по ГЕО/Языку)": None}
        if geo and lang:
            filtered_authors = [a for a in authors if a["country"] == geo and a["language"] == lang]
            for a in filtered_authors:
                author_options[a["author"]] = a["id"]
            author_sel = st.selectbox("Автор", options=list(author_options.keys()))
        else:
            st.selectbox("Автор", options=["Авто (по ГЕО/Языку)"], disabled=True, help="Сначала выберите Страну и Язык")
            author_sel = "Авто (по ГЕО/Языку)"
            
        add_kw = st.text_area("Дополнительные ключевые слова (LSI, контекст)", height=100)
        
        if st.button("Создать задачу"):
            if kw and site_str and geo and lang:
                post_data("tasks/", {
                    "main_keyword": kw,
                    "country": geo,
                    "language": lang,
                    "target_site": site_str,
                    "page_type": page_type,
                    "author_id": author_options.get(author_sel),
                    "additional_keywords": add_kw
                })
                st.success("Задача добавлена в очередь!")
                st.rerun()
            else:
                st.error("Пожалуйста, заполните Ключевое слово, Сайт, Страну и Язык.")

    with st.expander("Массовый импорт CSV"):
        uploaded_file = st.file_uploader("Выберите CSV файл (столбцы: keyword, country, language, site_name, page_type)", type="csv")
        if uploaded_file is not None:
            if st.button("Импортировать"):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    r = requests.post(f"{API_URL}/tasks/bulk", files=files)
                    if r.status_code == 200:
                        res = r.json()
                        st.success(f"Создано задач: {res.get('tasks_created')}")
                        if res.get('errors'):
                            st.warning("Ошибки при импорте:")
                            st.write(res['errors'])
                    else:
                        st.error(f"Ошибка: {r.text}")
                except Exception as e:
                    st.error(f"Ошибка загрузки: {e}")

    tasks = fetch_data("tasks/?limit=50")
    if tasks:
        # Add status emojis
        status_icons = {"pending": "⚪", "processing": "🔵", "completed": "🟢", "failed": "🔴"}
        for t in tasks:
            t["status_display"] = f"{status_icons.get(t['status'], '')} {t['status']}"
        
        df = pd.DataFrame(tasks)
        st.dataframe(
            df[["id", "main_keyword", "status_display", "page_type", "country", "language", "created_at"]],
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "main_keyword": st.column_config.TextColumn("Keyword", width="medium"),
                "status_display": st.column_config.TextColumn("Статус", width="small"),
                "page_type": st.column_config.TextColumn("Тип", width="small"),
                "country": st.column_config.TextColumn("Страна", width="small"),
                "language": st.column_config.TextColumn("Язык", width="small"),
                "created_at": st.column_config.TextColumn("Создано", width="medium"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Мониторинг задачи и действия")
        selected_task_id = st.selectbox("ID задачи", [t["id"] for t in tasks])
        selected_task = next((t for t in tasks if t["id"] == selected_task_id), None)
        
        if selected_task:
            # === Progress Bar & Intermediate Results ===
            if selected_task["status"] in ("processing", "completed", "failed"):
                steps_data = fetch_data(f"tasks/{selected_task_id}/steps")
                if steps_data:
                    progress = steps_data.get("progress", 0)
                    current = steps_data.get("current_step", "")
                    
                    if selected_task["status"] == "processing":
                        st.progress(progress / 100, text=f"{progress}% — {current or 'выполнение...'}")
                        import time
                        time.sleep(5)
                        st.rerun()
                    
                    st.markdown("#### 📋 Промежуточные результаты")
                    steps = steps_data.get("step_results") or {}
                    
                    step_order = [
                        ("serp_research", "🔍 SERP Research"),
                        ("competitor_scraping", "🕷️ Парсинг конкурентов"),
                        ("ai_structure_analysis", "🧠 AI анализ структуры"),
                        ("chunk_cluster_analysis", "📊 Анализ кластера"),
                        ("competitor_structure_analysis", "🏗️ Анализ конкурентов"),
                        ("final_structure_analysis", "📐 Финальная структура"),
                        ("primary_generation", "✍️ Первичная генерация"),
                        ("competitor_comparison", "⚖️ Сравнение с конкурентами"),
                        ("reader_opinion", "👤 Мнение читателя"),
                        ("interlinking_citations", "🔗 Перелинковка (Interlink)"),
                        ("improver", "💎 Улучшайзер"),
                        ("final_editing", "✅ Финальная редактура"),
                        ("html_structure", "🏷️ Структура HTML"),
                        ("meta_generation", "🏷️ Мета-теги"),
                    ]
                    
                    for step_key, step_label in step_order:
                        step = steps.get(step_key)
                        if not step:
                            st.write(f"⬜ **{step_label}** — ожидание")
                            continue
                        
                        s_status = step.get("status", "pending")
                        icon = "✅" if s_status == "completed" else "🔄"
                        
                        with st.expander(f"{icon} {step_label}", expanded=(s_status == "running")):
                            if step.get("result"):
                                st.text_area("Результат", value=step["result"][:10000], height=200, disabled=True, key=f"res_{step_key}_{selected_task_id}")
                            if step.get("timestamp"):
                                st.caption(f"Время: {step['timestamp']}")
                            if step.get("model"):
                                st.caption(f"Модель: {step['model']}")
            
            # === Actions ===
            st.write("---")
            col_actions, _, _ = st.columns([1, 1, 2])
            with col_actions:
                if selected_task["status"] == "failed":
                    st.error(selected_task.get("error_log", "Unknown error"))
                    if st.button("Перезапустить (Retry)"):
                        post_data(f"tasks/{selected_task_id}/retry", {})
                        st.success("Задача отправлена на перезапуск")
                        st.rerun()
                
                if st.button("Удалить задачу", type="primary"):
                    if delete_data(f"tasks/{selected_task_id}"):
                        st.success("Удалено")
                        st.rerun()

# ----- TAB: ARTICLES -----
def render_articles():
    st.header("Сгенерированные статьи")
    articles = fetch_data("articles/?limit=50")
    if articles:
        df = pd.DataFrame(articles)
        st.dataframe(df[["id", "title", "word_count", "created_at"]], use_container_width=True)
        
        st.subheader("Просмотр статьи")
        selected_id = st.selectbox("Выберите статью для предпросмотра", [a["id"] for a in articles])
        if selected_id:
            art = fetch_data(f"articles/{selected_id}")
            if art:
                col1, col2 = st.columns(2, gap="medium")
                col1.text_area("Meta Title", value=art.get("title", ""), disabled=True)
                col2.text_area("Meta Description", value=art.get("description", ""), disabled=True)
                
                with st.expander("Исходный код HTML"):
                    st.code(art.get("html_content", ""), language="html")
                    
                st.markdown(f'<a href="{API_URL}/articles/{selected_id}/download" target="_blank"><button style="background-color:#4CAF50;color:white;padding:10px 24px;border:none;border-radius:4px;cursor:pointer;">Скачать .html</button></a>', unsafe_allow_html=True)
                
                st.components.v1.iframe(f"{API_URL}/articles/{selected_id}/preview", height=600, scrolling=True)

# ----- TAB: AUTHORS -----
def render_authors():
    st.header("Управление Авторами")
    
    with st.expander("Создать нового Автора"):
        with st.form("new_author_form"):
            col1, col2 = st.columns(2, gap="medium")
            a_name = col1.text_input("Имя Автора*")
            a_country = col2.text_input("Страна (Код, e.g. US)*")
            a_lang = col1.text_input("Язык (Код, e.g. en)*")
            a_city = col2.text_input("Город")
            a_co_short = col1.text_input("Сокращение страны (co_short)")
            
            st.markdown("### Промпт параметры (Настройки стилистики)")
            
            a_text_block = st.text_area("Текстовый блок (Author Style/Text Block)", help="Основной текст/описание стиля автора", height=100)
            a_imitation = st.text_input("Imitation (Mimicry)", help="Кого или что пародировать/подражать")
            
            col3, col4 = st.columns(2, gap="medium")
            a_year = col3.text_input("Year", help="Год или эпоха стиля (e.g. 2024, 1990s)")
            a_face = col4.text_input("Face", help="Лицо/подача (e.g. Friendly, Informative, Expert)")
            
            a_target_audience = st.text_input("Target Audience", help="Целевая аудитория (e.g. Beginners, Crypto Enthusiasts)")
            a_rhythms_style = st.text_input("Rhythms & Style", help="Ритм и стиль повествования (e.g. Short punchy sentences, academic)")
            
            submit = st.form_submit_button("Добавить Автора")
            if submit and a_name and a_country and a_lang:
                res = post_data("authors/", {
                    "author": a_name,
                    "country": a_country,
                    "language": a_lang,
                    "style_prompt": a_text_block,
                    "city": a_city,
                    "co_short": a_co_short,
                    "imitation": a_imitation,
                    "year": a_year,
                    "face": a_face,
                    "target_audience": a_target_audience,
                    "rhythms_style": a_rhythms_style
                })
                if res:
                    st.success("Автор добавлен!")
                    st.rerun()
            elif submit:
                st.error("Заполните обязательные поля: Имя, Страна, Язык.")
                
    authors = fetch_data("authors/")
    if authors:
        df = pd.DataFrame(authors)
        st.dataframe(df[["id", "author", "country", "language", "city"]], use_container_width=True)
        
        st.subheader("Удалить автора")
        del_sel = st.selectbox("Выберите автора для удаления", options=[f"{a['id']} - {a['author']}" for a in authors])
        if st.button("Удалить", type="primary"):
            a_id = del_sel.split(" - ")[0]
            if delete_data(f"authors/{a_id}"):
                st.success("Автор удален!")
                st.rerun()

# ----- TAB: PROMPTS -----
def render_prompts():
    st.header("Управление Промптами (LLM Агенты)")
    
    # 12 agents: key → display name
    agents_map = {
        "ai_structure_analysis": "AI анализ структуры",
        "chunk_cluster_analysis": "Анализ кластера (Чанки)",
        "competitor_structure_analysis": "Анализ конкурентов",
        "final_structure_analysis": "Финальный анализ структуры",
        "primary_generation": "Первичная генерация",
        "competitor_comparison": "Сравнение с конкурентами",
        "reader_opinion": "Мнение читателя",
        "interlinking_citations": "Перелинковка и цитаты",
        "improver": "Улучшайзер",
        "final_editing": "Финальная редактура",
        "html_structure": "Структура HTML",
        "meta_generation": "Генерация мета-тегов",
    }
    agents = list(agents_map.keys())
    
    prompts_data = fetch_data("prompts/") or []
    active_prompts = {p["agent_name"]: p for p in prompts_data if p.get("is_active")}
    
    agent_tabs = st.tabs([f"⏸ {agents_map[a]}" if active_prompts.get(a, {}).get("skip_in_pipeline") else agents_map[a] for a in agents])
    
    or_models = get_openrouter_models()
    
    for i, agent in enumerate(agents):
        with agent_tabs[i]:
            current = active_prompts.get(agent, {})
            full_prompt = {}
            if current:
                 full_prompt = fetch_data(f"prompts/{current['id']}") or {}
            
            # Variable reference guide
            with st.expander("📋 Доступные переменные (скопируй переменную → вставь в текст)"):
                
                st.markdown("""
<style>
/* Уменьшаем отступы между колонками, чтобы они выглядели как таблица */
div[data-testid="stHorizontalBlock"] {
    gap: 0px;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)
                
                st.markdown("**Данные задачи и автора:**")
                
                task_vars = [
                    ("keyword", "Главное ключевое слово"),
                    ("additional_keywords", "Доп. ключевые слова (LSI)"),
                    ("country", "Страна"),
                    ("language", "Язык"),
                    ("page_type", "Тип страницы (homepage, category, article)"),
                    ("competitors_headers", "Структура h1-h6 конкурентов (JSON)"),
                    ("merged_markdown", "Объединённый текст конкурентов (внимание: большой объём!)"),
                    ("avg_word_count", "Среднее кол-во слов у конкурентов"),
                    ("author", "Имя автора"),
                    ("author_style", "Текстовый блок / стиль автора"),
                    ("imitation", "Подражание (Mimicry)"),
                    ("target_audience", "Целевая аудитория"),
                    ("face", "Лицо повествования (POV)"),
                    ("year", "Год"),
                    ("rhythms_style", "Ритм и стиль"),
                    ("exclude_words", "Слова-исключения (глобальные)"),
                    ("site_name", "Название целевого сайта"),
                ]
                
                col1, col2 = st.columns([1, 2])
                with col1: st.write("**Переменная (нажми иконку чтобы скопировать)**")
                with col2: st.write("**Описание**")
                
                for v, d in task_vars:
                    c1, c2 = st.columns([1, 2])
                    with c1: st.code(f"{{{{{v}}}}}", language=None)
                    with c2: st.markdown(f"<div style='padding-top:14px'>{d}</div>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("**Результаты предыдущих этапов:**")
                
                result_vars = [
                    ("result_ai_structure_analysis", "AI анализ структуры"),
                    ("intent", "└ Поисковый интент (из AI анализа)"),
                    ("Taxonomy", "└ Таксономия запроса (из AI анализа)"),
                    ("Attention", "└ На что обратить внимание (из AI анализа)"),
                    ("structura", "└ Рекомендованная структура (из AI анализа)"),
                    ("result_chunk_cluster_analysis", "Анализ кластера (Чанки)"),
                    ("result_competitor_structure_analysis", "Анализ конкурентов"),
                    ("result_final_structure_analysis", "Финальный анализ структуры (JSON)"),
                    ("result_primary_generation", "Первичная генерация (HTML)"),
                    ("result_competitor_comparison", "Сравнение с конкурентами"),
                    ("result_reader_opinion", "Мнение читателя"),
                    ("result_interlinking_citations", "Перелинковка и цитаты"),
                    ("result_improver", "Улучшайзер"),
                    ("result_final_editing", "Финальная редактура"),
                    ("result_html_structure", "Структура HTML"),
                ]
                
                col1, col2 = st.columns([1, 2])
                with col1: st.write("**Переменная (нажми иконку чтобы скопировать)**")
                with col2: st.write("**Описание**")
                
                for v, d in result_vars:
                    c1, c2 = st.columns([1, 2])
                    with c1: st.code(f"{{{{{v}}}}}", language=None)
                    with c2: st.markdown(f"<div style='padding-top:14px'>{d}</div>", unsafe_allow_html=True)
            
            skip = st.toggle(
                "Пропускать этот этап в pipeline",
                value=full_prompt.get("skip_in_pipeline", False),
                key=f"skip_{agent}"
            )
            if skip:
                st.warning("Этот агент будет пропущен при генерации")
                
            with st.form(f"prompt_form_{agent}"):
                st.subheader(f"Промпты для {agents_map[agent]}")
                p_text = st.text_area("System Message", value=full_prompt.get("system_prompt", ""), height=400, help="Системные инструкции по роли и поведению агента. Поддерживает {{переменные}}.")
                u_text = st.text_area("User Message", value=full_prompt.get("user_prompt", ""), height=250, help="Ваш шаблон запроса. Контекст задачи добавляется в конец автоматически. Поддерживает {{переменные}}.")
                
                st.markdown("---")
                st.markdown("**Настройки модели**")
                
                current_model = full_prompt.get("model", "openai/gpt-4o-mini")
                model_index = or_models.index(current_model) if current_model in or_models else 0
                
                model = st.selectbox("Модель OpenRouter", options=or_models, index=model_index, key=f"model_{agent}")
                
                # Optional params with toggles
                col_t1, col_t2, col_t3, col_t4 = st.columns(4, gap="small")
                
                use_temp = col_t1.checkbox("Temperature", value=full_prompt.get("temperature", 0.7) != 0.7 or True, key=f"use_temp_{agent}")
                use_freq = col_t2.checkbox("Freq. Penalty", value=full_prompt.get("frequency_penalty", 0.0) != 0.0, key=f"use_freq_{agent}")
                use_pres = col_t3.checkbox("Pres. Penalty", value=full_prompt.get("presence_penalty", 0.0) != 0.0, key=f"use_pres_{agent}")
                use_topp = col_t4.checkbox("Top P", value=full_prompt.get("top_p", 1.0) != 1.0, key=f"use_topp_{agent}")
                
                col_v1, col_v2, col_v3, col_v4 = st.columns(4, gap="small")
                
                temp = col_v1.number_input("Temperature", value=float(full_prompt.get("temperature", 0.7)), step=0.1, format="%.2f", key=f"temp_{agent}", disabled=not use_temp)
                freq_pen = col_v2.number_input("Frequency Penalty", value=float(full_prompt.get("frequency_penalty", 0.0)), step=0.1, format="%.2f", key=f"freq_{agent}", disabled=not use_freq)
                pres_pen = col_v3.number_input("Presence Penalty", value=float(full_prompt.get("presence_penalty", 0.0)), step=0.1, format="%.2f", key=f"pres_{agent}", disabled=not use_pres)
                top_p = col_v4.number_input("Top P", value=float(full_prompt.get("top_p", 1.0)), step=0.1, format="%.2f", key=f"topp_{agent}", disabled=not use_topp)
                
                submitted = st.form_submit_button("💾 Сохранить изменения", use_container_width=True)
                if submitted:
                    res = post_data("prompts/", {
                        "agent_name": agent,
                        "system_prompt": p_text,
                        "user_prompt": u_text,
                        "model": model,
                        "skip_in_pipeline": skip,
                        "temperature": temp if use_temp else 0.7,
                        "frequency_penalty": freq_pen if use_freq else 0.0,
                        "presence_penalty": pres_pen if use_pres else 0.0,
                        "top_p": top_p if use_topp else 1.0
                    })
                    if res:
                        st.success(f"Промпт для {agents_map[agent]} обновлен! Версия: {res.get('version')}")
                        st.rerun()

# ----- TAB: LOGS -----
def render_logs():
    st.header("📜 Логи выполнения")
    
    tasks = fetch_data("tasks/?limit=50")
    if not tasks:
        st.info("Нет задач для отображения")
        return
        
    selected_task_id = st.selectbox("🌍 Выберите задачу для просмотра логов", [t["id"] for t in tasks])
    
    if selected_task_id:
        task_data = fetch_data(f"tasks/{selected_task_id}")
        if task_data:
            logs = task_data.get("logs", [])
            if not logs:
                st.info("Логи пока пусты...")
                return
                
            # Filter
            level_filter = st.radio("Фильтр", ["Все", "Только ошибки (error)"], horizontal=True)
            
            log_container = st.container(height=600)
            
            for log in logs:
                lvl = log.get("level", "info")
                if level_filter == "Только ошибки (error)" and lvl != "error":
                    continue
                    
                ts = log.get("ts", "")
                msg = log.get("msg", "")
                step = log.get("step", "")
                
                step_badge = f"[{step}] " if step else ""
                color = "red" if lvl == "error" else "gray"
                icon = "❌" if lvl == "error" else "ℹ️"
                
                log_container.markdown(f"**<span style='color:{color}'>{ts} {icon} {step_badge}</span>** {msg}", unsafe_allow_html=True)
            
            if st.button("🔄 Обновить логи"):
                st.rerun()

# ----- TAB: SETTINGS -----
def render_settings():
    st.header("⚙️ Настройки системы")
    st.caption("API ключи и параметры. Оставьте поле пустым, чтобы не менять значение.")
    
    settings = fetch_data("settings/") or {}
    
    with st.container(border=True):
        with st.form("settings_form"):
            col1, col2 = st.columns(2, gap="large")
            
            with col1:
                st.markdown("### 🔑 LLM & SEO APIs")
                openrouter_key = st.text_input("OpenRouter API Key", placeholder=settings.get("OPENROUTER_API_KEY", "Без изменений"), type="password")
                dataforseo_login = st.text_input("DataForSEO Login", placeholder=settings.get("DATAFORSEO_LOGIN", "Без изменений"))
                dataforseo_pwd = st.text_input("DataForSEO Password", placeholder=settings.get("DATAFORSEO_PASSWORD", "Без изменений"), type="password")
                serpapi_key = st.text_input("SerpAPI Key (Fallback)", placeholder=settings.get("SERPAPI_KEY", "Без изменений"), type="password")
                serper_key = st.text_input("Serper.dev API Key", placeholder=settings.get("SERPER_API_KEY", "Без изменений"), type="password")
                
            with col2:
                st.markdown("### 🛠️ Системные и Остальные")
                tg_token = st.text_input("Telegram Bot Token", placeholder=settings.get("TELEGRAM_BOT_TOKEN", "Без изменений"), type="password")
                tg_chat = st.text_input("Telegram Chat ID", placeholder=settings.get("TELEGRAM_CHAT_ID", "Без изменений"))
                concurrency = st.text_input("Celery Concurrency", placeholder=settings.get("CELERY_CONCURRENCY", "Без изменений"))
                exclude_words = st.text_area("Слова-исключения (глобально)", value=settings.get("EXCLUDE_WORDS", ""), help="Слова через запятую. Применяются ко всем генерируемым текстам автоматически.", height=100)
                
            st.write("---")
            submit = st.form_submit_button("💾 Сохранить настройки", type="primary", use_container_width=True)
            
            if submit:
                payload = {}
                if openrouter_key: payload["OPENROUTER_API_KEY"] = openrouter_key
                if dataforseo_login: payload["DATAFORSEO_LOGIN"] = dataforseo_login
                if dataforseo_pwd: payload["DATAFORSEO_PASSWORD"] = dataforseo_pwd
                if serpapi_key: payload["SERPAPI_KEY"] = serpapi_key
                if serper_key: payload["SERPER_API_KEY"] = serper_key
                if tg_token: payload["TELEGRAM_BOT_TOKEN"] = tg_token
                if tg_chat: payload["TELEGRAM_CHAT_ID"] = tg_chat
                if concurrency: payload["CELERY_CONCURRENCY"] = concurrency
                if exclude_words is not None: payload["EXCLUDE_WORDS"] = exclude_words
                
                if payload:
                    try:
                        r = requests.put(f"{API_URL}/settings/", json=payload)
                        if r.status_code == 200:
                            st.success("✅ Настройки успешно сохранены в .env!")
                            st.warning("Требуется вручную перезапустить backend/celery контейнеры для применения новых ключей.")
                        else:
                            st.error(f"Ошибка сохранения: {r.text}")
                    except Exception as e:
                        st.error(f"Ошибка соединения: {e}")
                else:
                    st.info("Нет изменений для сохранения.")

# ----- TAB: BLUEPRINTS -----
def render_blueprints():
    st.header("🏗️ Блупринты")
    
    blueprints = fetch_data("blueprints/") or []
    if blueprints:
        df = pd.DataFrame(blueprints)
        st.dataframe(df[["id", "name", "slug", "is_active"]], use_container_width=True)
    
    with st.expander("Создать новый блупринт"):
        with st.form("new_blueprint_form"):
            bp_name = st.text_input("Название (e.g. Brand Site)")
            bp_slug = st.text_input("Слаг (e.g. brand-site)")
            bp_desc = st.text_area("Описание")
            if st.form_submit_button("Добавить"):
                if bp_name and bp_slug:
                    post_data("blueprints/", {"name": bp_name, "slug": bp_slug, "description": bp_desc})
                    st.success("Блупринт создан!")
                    st.rerun()
                else:
                    st.error("Заполните название и слаг")
                    
    if blueprints:
        st.subheader("Страницы блупринта")
        selected_bp_id = st.selectbox("Выберите блупринт", options=[bp["id"] for bp in blueprints], format_func=lambda x: next(b["name"] for b in blueprints if b["id"] == x))
        
        pages = fetch_data(f"blueprints/{selected_bp_id}/pages") or []
        if pages:
            df_p = pd.DataFrame(pages)
            df_p = df_p.sort_values(by="sort_order")
            st.dataframe(df_p[["page_slug", "page_title", "page_type", "keyword_template", "filename", "sort_order", "use_serp"]], use_container_width=True)
            
            st.markdown("**Удалить страницу**")
            del_page_id = st.selectbox("ID страницы для удаления", options=[""] + [p["id"] for p in pages])
            if st.button("Удалить страницу") and del_page_id:
                delete_data(f"blueprints/{selected_bp_id}/pages/{del_page_id}")
                st.rerun()
                
        with st.expander("Добавить страницу"):
            with st.form("new_page_form"):
                col1, col2 = st.columns(2)
                p_slug = col1.text_input("Слаг страницы (e.g. home)")
                p_title = col2.text_input("Название (e.g. Home Page)")
                p_type = col1.selectbox("Тип страницы", ["homepage", "category", "article", "info", "legal"])
                p_kw = col2.text_input("Шаблон ключа (e.g. {seed} online casino)")
                p_file = col1.text_input("Имя файла (e.g. index.html)")
                p_sort = col2.number_input("Порядок сортировки (sort_order)", value=len(pages)+1, step=1)
                
                p_nav_label = col1.text_input("Название в меню")
                p_nav = col2.checkbox("Показывать в меню", value=True)
                p_footer = col1.checkbox("Показывать в футере", value=True)
                p_serp = col2.checkbox("Использовать SERP (use_serp)", value=True, help="Отключите для Privacy, Terms и т.д.")
                
                if st.form_submit_button("Добавить страницу"):
                    if p_slug and p_title and p_kw and p_file:
                        post_data(f"blueprints/{selected_bp_id}/pages", {
                            "page_slug": p_slug,
                            "page_title": p_title,
                            "page_type": p_type,
                            "keyword_template": p_kw,
                            "filename": p_file,
                            "sort_order": p_sort,
                            "nav_label": p_nav_label,
                            "show_in_nav": p_nav,
                            "show_in_footer": p_footer,
                            "use_serp": p_serp
                        })
                        st.success("Страница добавлена!")
                        st.rerun()

# ----- TAB: PROJECTS -----
def render_projects():
    st.header("📁 Проекты (Сайты)")
    
    blueprints = fetch_data("blueprints/") or []
    authors = fetch_data("authors/") or []
    sites = fetch_data("sites/") or []
    projects = fetch_data("projects/") or []
    
    if projects:
        df = pd.DataFrame(projects)
        st.dataframe(df[["id", "name", "seed_keyword", "status", "created_at"]], use_container_width=True)
        
    with st.expander("Создать новый проект"):
        with st.form("new_project_form"):
            pr_name = st.text_input("Название проекта (e.g. CasinoX DE)")
            bp_opts = {b["name"]: b["id"] for b in blueprints}
            pr_bp = st.selectbox("Блупринт", options=list(bp_opts.keys())) if bp_opts else None
            pr_seed = st.text_input("Seed Keyword (e.g. casinox)")
            pr_site = st.text_input("Сайт (домен)")
            
            countries = list(set([a.get("country") for a in authors if a.get("country")]))
            languages = list(set([a.get("language") for a in authors if a.get("language")]))
            
            col1, col2 = st.columns(2)
            pr_country = col1.selectbox("Страна", [""] + countries)
            pr_lang = col2.selectbox("Язык", [""] + languages)
            
            pr_author = None
            pr_author_name = "Авто (по ГЕО/Языку)"
            if pr_country and pr_lang:
                filtered_authors = {a["author"]: a["id"] for a in authors if a["country"] == pr_country and a["language"] == pr_lang}
                pr_author_name = st.selectbox("Автор", ["Авто (по ГЕО/Языку)"] + list(filtered_authors.keys()))
                if pr_author_name != "Авто (по ГЕО/Языку)":
                    pr_author = filtered_authors[pr_author_name]
            else:
                st.selectbox("Автор", ["Авто (по ГЕО/Языку)"], disabled=True)
                    
            if st.form_submit_button("Создать и Запустить"):
                if pr_name and pr_bp and pr_seed and pr_site and pr_country and pr_lang:
                    post_data("projects/", {
                        "name": pr_name,
                        "blueprint_id": bp_opts[pr_bp],
                        "seed_keyword": pr_seed,
                        "target_site": pr_site,
                        "country": pr_country,
                        "language": pr_lang,
                        "author_id": pr_author
                    })
                    st.success("Проект запущен!")
                    st.rerun()
                else:
                    st.error("Заполните все обязательные поля")
                    
    if projects:
        st.subheader("Просмотр проекта")
        selected_pr_id = st.selectbox("Выберите проект", [p["id"] for p in projects], format_func=lambda x: next(p["name"] for p in projects if p["id"] == x))
        
        details = fetch_data(f"projects/{selected_pr_id}")
        if details:
            tasks = details.get("tasks", [])
            total_pages = len(tasks)
            completed = sum(1 for t in tasks if t["status"] == "completed")
            
            st.progress(completed / total_pages if total_pages > 0 else 0, text=f"Прогресс: {completed} / {total_pages} страниц")
            
            st.write(f"**Статус проекта:** {details['status']}")
            if details['status'] == 'completed' and details.get('build_zip_url'):
                st.markdown(f'<a href="{API_URL}/projects/{selected_pr_id}/download" target="_blank"><button style="background-color:#4F46E5;color:white;padding:10px 24px;border:none;border-radius:8px;font-weight:600;cursor:pointer;">Скачать готовый сайт (.zip)</button></a>', unsafe_allow_html=True)
                
            if tasks:
                st.markdown("### Задачи проекта")
                df_t = pd.DataFrame(tasks)
                st.dataframe(df_t[["main_keyword", "page_type", "status"]], use_container_width=True)

# ----- MAIN UI ROUTING -----
tabs = st.tabs(["📊 Дашборд", "📁 Проекты", "🏗️ Блупринты", "✅ Задачи", "📝 Статьи", "🌐 Сайты", "👥 Авторы", "🤖 Промпты", "📜 Логи", "⚙️ Настройки"])

with tabs[0]: render_dashboard()
with tabs[1]: render_projects()
with tabs[2]: render_blueprints()
with tabs[3]: render_tasks()
with tabs[4]: render_articles()
with tabs[5]: st.info("Раздел 'Сайты' в разработке.")
with tabs[6]: render_authors()
with tabs[7]: render_prompts()
with tabs[8]: render_logs()
with tabs[9]: render_settings()

