"""
Парсинг и отображение результатов Nerpa
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import streamlit as st
import json

from config import ERROR_MESSAGES
from utils import logger, format_file_size


def load_results(output_dir: Path) -> Optional[pd.DataFrame]:
    """
    Загрузка report.csv и преобразование в DataFrame
    
    Args:
        output_dir: Директория с результатами Nerpa
        
    Returns:
        DataFrame с результатами или None
    """
    report_path = output_dir / "report.csv"
    
    if not report_path.exists():
        logger.error(f"Файл report.csv не найден в {output_dir}")
        return None
    
    try:
        df = pd.read_csv(report_path)
        logger.info(f"Загружено {len(df)} результатов из {report_path}")
        return df
        
    except Exception as e:
        logger.error(f"Ошибка загрузки результатов: {e}")
        st.error(f"Не удалось загрузить результаты: {e}")
        return None


def display_summary(df: pd.DataFrame) -> None:
    """
    Отображение сводной информации о результатах
    
    Args:
        df: DataFrame с результатами
    """
    if df is None or df.empty:
        st.warning("Нет результатов для отображения")
        return
    
    st.subheader("📊 Сводная информация")
    
    # Умный поиск колонки со Score (защита от регистра букв)
    score_col = 'Score' if 'Score' in df.columns else ('score' if 'score' in df.columns else None)
    
    # Метрики в колонках
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего совпадений", len(df))
    
    with col2:
        if score_col:
            max_score = df[score_col].max()
            st.metric("Макс. score", f"{max_score:.2f}")
        else:
            st.metric("Макс. score", "N/A")
    
    with col3:
        if score_col:
            avg_score = df[score_col].mean()
            st.metric("Средний score", f"{avg_score:.2f}")
        else:
            st.metric("Средний score", "N/A")
    
    with col4:
        unique_bgcs = df.iloc[:, 0].nunique() if len(df.columns) > 0 else 0
        st.metric("Уникальных BGC", unique_bgcs)
    
    # Топ-5 совпадений
    st.subheader("🏆 Топ-5 совпадений")
    
    if score_col:
        top_5 = df.nlargest(5, score_col)
    else:
        top_5 = df.head(5)
    
    # Форматированная таблица
    display_df = top_5.copy()
    
    # Округление числовых колонок
    numeric_cols = display_df.select_dtypes(include=['float64', 'float32']).columns
    for col in numeric_cols:
        display_df[col] = display_df[col].round(3)
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def display_detailed_table(df: pd.DataFrame) -> None:
    """
    Интерактивная таблица с фильтрацией и сортировкой
    
    Args:
        df: DataFrame с результатами
    """
    if df is None or df.empty:
        st.warning("Нет данных для отображения")
        return
    
    st.subheader("🔍 Детальная таблица результатов")
    
    # Умный поиск колонки Score
    score_col = 'Score' if 'Score' in df.columns else ('score' if 'score' in df.columns else None)
    
    # Фильтры в expander
    with st.expander("⚙️ Настройки фильтрации и отображения"):
        col1, col2 = st.columns(2)
        
        with col1:
            score_threshold = None
            if score_col:
                min_score = float(df[score_col].min())
                max_score = float(df[score_col].max())
                
                # --- ИСПРАВЛЕНИЕ: Если найдено 1 совпадение, раздвигаем границы ползунка ---
                if min_score == max_score:
                    min_score = max(0.0, min_score - 1.0)
                    max_score = max_score + 1.0
                # --------------------------------------------------------------------------
                
                score_threshold = st.slider(
                    "Минимальный Score", 
                    min_value=float(min_score), 
                    max_value=float(max_score), 
                    value=float(min_score)
                )
            else:
                st.info("Колонка Score отсутствует в результатах")
        
        with col2:
            # Количество строк
            rows_to_show = st.selectbox(
                "Показать строк:",
                options=[10, 25, 50, 100, "Все"],
                index=1
            )
        
        # Выбор колонок для отображения
        available_columns = df.columns.tolist()
        selected_columns = st.multiselect(
            "Выбрать колонки для отображения:",
            options=available_columns,
            default=available_columns[:min(5, len(available_columns))]
        )
    
    # Применение фильтров
    filtered_df = df.copy()
    
    if score_threshold is not None and score_col is not None:
        filtered_df = filtered_df[filtered_df[score_col] >= score_threshold]
    
    if selected_columns:
        filtered_df = filtered_df[selected_columns]
    
    # Ограничение количества строк
    if rows_to_show != "Все":
        filtered_df = filtered_df.head(rows_to_show)
    
    # Информация о фильтрации
    st.info(f"Показано {len(filtered_df)} из {len(df)} результатов")
    
    # Отображение таблицы
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


def load_alignment_details(output_dir: Path) -> Dict[str, str]:
    """
    Загрузка детальных файлов выравнивания
    
    Args:
        output_dir: Директория с результатами
        
    Returns:
        Словарь {имя_файла: содержимое}
    """
    details_dir = output_dir / "details"
    alignments = {}
    
    if not details_dir.exists():
        logger.warning(f"Папка details не найдена в {output_dir}")
        return alignments
    
    try:
        detail_files = sorted(details_dir.glob("*.txt"))
        
        for file_path in detail_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                alignments[file_path.name] = content
        
        logger.info(f"Загружено {len(alignments)} файлов выравниваний")
        
    except Exception as e:
        logger.error(f"Ошибка загрузки выравниваний: {e}")
    
    return alignments


def format_alignment(alignment_text: str) -> str:
    """
    Форматирование выравнивания для читаемого отображения
    
    Args:
        alignment_text: Текст выравнивания
        
    Returns:
        Отформатированный текст
    """
    # Базовое форматирование - можно расширить
    lines = alignment_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Выделение заголовков
        if line.startswith('>') or line.startswith('BGC:') or line.startswith('NRP:'):
            formatted_lines.append(f"**{line}**")
        # Выделение score строк
        elif 'score' in line.lower() or 'match' in line.lower():
            formatted_lines.append(f"*{line}*")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


def display_alignments(output_dir: Path) -> None:
    """
    Отображение детальных выравниваний
    
    Args:
        output_dir: Директория с результатами
    """
    st.subheader("🧬 Детальные выравнивания")
    
    alignments = load_alignment_details(output_dir)
    
    if not alignments:
        st.info("Детальные выравнивания не найдены или не были созданы")
        return
    
    # Выбор файла для просмотра
    selected_file = st.selectbox(
        "Выберите совпадение для просмотра деталей:",
        options=list(alignments.keys()),
        format_func=lambda x: x.replace('.txt', '').replace('_', ' ')
    )
    
    if selected_file:
        alignment_content = alignments[selected_file]
        
        # Tabs для разных представлений
        tab1, tab2 = st.tabs(["📄 Форматированный", "📝 Исходный текст"])
        
        with tab1:
            formatted = format_alignment(alignment_content)
            st.markdown(formatted)
        
        with tab2:
            st.text(alignment_content)
        
        # Кнопка скачивания
        st.download_button(
            label="💾 Скачать выравнивание",
            data=alignment_content,
            file_name=selected_file,
            mime="text/plain"
        )


def export_results(df: pd.DataFrame, format: str = 'csv') -> bytes:
    """
    Подготовка результатов для экспорта
    
    Args:
        df: DataFrame с результатами
        format: Формат экспорта ('csv' или 'json')
        
    Returns:
        Данные для скачивания в байтах
    """
    if format == 'csv':
        return df.to_csv(index=False).encode('utf-8')
    elif format == 'json':
        return df.to_json(orient='records', indent=2).encode('utf-8')
    else:
        raise ValueError(f"Неподдерживаемый формат: {format}")


def create_export_buttons(df: pd.DataFrame) -> None:
    """
    Создание кнопок экспорта результатов
    
    Args:
        df: DataFrame с результатами
    """
    st.subheader("💾 Экспорт результатов")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_data = export_results(df, 'csv')
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_data,
            file_name="nerpa_results.csv",
            mime="text/csv"
        )
    
    with col2:
        json_data = export_results(df, 'json')
        st.download_button(
            label="📥 Скачать JSON",
            data=json_data,
            file_name="nerpa_results.json",
            mime="application/json"
        )


def display_results_page(output_dir: Path) -> None:
    """
    Полная страница отображения результатов
    
    Args:
        output_dir: Директория с результатами
    """
    # Загрузка результатов
    df = load_results(output_dir)
    
    if df is None or df.empty:
        st.error(ERROR_MESSAGES['no_results'])
        return
    
    # Сводка
    display_summary(df)
    
    st.divider()
    
    # Детальная таблица
    display_detailed_table(df)
    
    st.divider()
    
    # Выравнивания
    display_alignments(output_dir)
    
    st.divider()
    
    # Экспорт
    create_export_buttons(df)