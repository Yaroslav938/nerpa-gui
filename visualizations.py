"""
Визуализация результатов Nerpa
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Optional, List
import streamlit as st

from config import PLOT_COLORS
from utils import logger


def plot_score_distribution(df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Гистограмма распределения scores
    
    Args:
        df: DataFrame с результатами
        
    Returns:
        Plotly Figure или None
    """
    if df is None or df.empty or 'score' not in df.columns:
        return None
    
    try:
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=df['score'],
            nbinsx=30,
            marker_color=PLOT_COLORS['primary'],
            opacity=0.75,
            name='Score'
        ))
        
        fig.update_layout(
            title='Распределение Score совпадений',
            xaxis_title='Score',
            yaxis_title='Количество',
            template='plotly_white',
            height=400,
            showlegend=False
        )
        
        # Средняя линия
        mean_score = df['score'].mean()
        fig.add_vline(
            x=mean_score,
            line_dash="dash",
            line_color=PLOT_COLORS['warning'],
            annotation_text=f"Среднее: {mean_score:.2f}",
            annotation_position="top"
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Ошибка создания графика распределения: {e}")
        return None


def plot_top_matches(df: pd.DataFrame, top_n: int = 10) -> Optional[go.Figure]:
    """
    Horizontal bar chart с топ-N совпадениями
    
    Args:
        df: DataFrame с результатами
        top_n: Количество топ результатов
        
    Returns:
        Plotly Figure или None
    """
    if df is None or df.empty or 'score' not in df.columns:
        return None
    
    try:
        # Получаем топ-N
        top_df = df.nlargest(top_n, 'score').copy()
        
        # Создаем метку для оси Y (обычно это BGC ID из первой колонки)
        if len(top_df.columns) > 0:
            top_df['label'] = top_df.iloc[:, 0].astype(str)
        else:
            top_df['label'] = [f"Match {i+1}" for i in range(len(top_df))]
        
        # Сортируем для отображения снизу вверх
        top_df = top_df.sort_values('score')
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=top_df['score'],
            y=top_df['label'],
            orientation='h',
            marker_color=PLOT_COLORS['secondary'],
            text=top_df['score'].round(2),
            textposition='outside'
        ))
        
        fig.update_layout(
            title=f'Топ-{top_n} совпадений по Score',
            xaxis_title='Score',
            yaxis_title='BGC',
            template='plotly_white',
            height=max(400, top_n * 40),
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Ошибка создания графика топ совпадений: {e}")
        return None


def plot_bgc_coverage(df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Визуализация покрытия BGC (если есть соответствующие данные)
    
    Args:
        df: DataFrame с результатами
        
    Returns:
        Plotly Figure или None
    """
    if df is None or df.empty:
        return None
    
    # Проверяем наличие колонок с покрытием
    coverage_cols = [col for col in df.columns if 'coverage' in col.lower() or 'identity' in col.lower()]
    
    if not coverage_cols:
        return None
    
    try:
        coverage_col = coverage_cols[0]
        
        fig = go.Figure()
        
        fig.add_trace(go.Box(
            y=df[coverage_col],
            name='Покрытие',
            marker_color=PLOT_COLORS['success'],
            boxmean='sd'
        ))
        
        fig.update_layout(
            title=f'Распределение {coverage_col}',
            yaxis_title=coverage_col,
            template='plotly_white',
            height=400,
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Ошибка создания графика покрытия: {e}")
        return None


def create_summary_metrics(df: pd.DataFrame) -> None:
    """
    Создание метрик-карточек с основной статистикой
    
    Args:
        df: DataFrame с результатами
    """
    if df is None or df.empty:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_matches = len(df)
        st.metric(
            label="Всего совпадений",
            value=total_matches,
            delta=None
        )
    
    with col2:
        if 'score' in df.columns:
            max_score = df['score'].max()
            mean_score = df['score'].mean()
            delta = max_score - mean_score
            st.metric(
                label="Максимальный Score",
                value=f"{max_score:.2f}",
                delta=f"+{delta:.2f} от среднего"
            )
    
    with col3:
        if 'score' in df.columns:
            high_quality = len(df[df['score'] > df['score'].quantile(0.75)])
            st.metric(
                label="Высококачественных",
                value=high_quality,
                delta=f"{(high_quality/len(df)*100):.1f}%"
            )
    
    with col4:
        unique_bgcs = df.iloc[:, 0].nunique() if len(df.columns) > 0 else 0
        st.metric(
            label="Уникальных BGC",
            value=unique_bgcs
        )


def plot_comparison(dfs: List[pd.DataFrame], labels: List[str]) -> Optional[go.Figure]:
    """
    Сравнение результатов нескольких запусков
    
    Args:
        dfs: Список DataFrame с результатами
        labels: Метки для каждого DataFrame
        
    Returns:
        Plotly Figure или None
    """
    if not dfs or not labels or len(dfs) != len(labels):
        return None
    
    try:
        fig = go.Figure()
        
        for df, label in zip(dfs, labels):
            if 'score' in df.columns:
                fig.add_trace(go.Box(
                    y=df['score'],
                    name=label,
                    boxmean='sd'
                ))
        
        fig.update_layout(
            title='Сравнение распределения Score',
            yaxis_title='Score',
            xaxis_title='Анализ',
            template='plotly_white',
            height=400
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Ошибка создания графика сравнения: {e}")
        return None


def display_visualizations(df: pd.DataFrame) -> None:
    """
    Отображение всех визуализаций
    
    Args:
        df: DataFrame с результатами
    """
    if df is None or df.empty:
        st.warning("Нет данных для визуализации")
        return
    
    st.subheader("📈 Визуализация результатов")
    
    # Метрики
    create_summary_metrics(df)
    
    st.divider()
    
    # Графики в колонках
    col1, col2 = st.columns(2)
    
    with col1:
        # Распределение scores
        fig_dist = plot_score_distribution(df)
        if fig_dist:
            st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        # Топ совпадений
        top_n = st.slider("Количество топ результатов:", 5, 20, 10, key='top_n_slider')
        fig_top = plot_top_matches(df, top_n)
        if fig_top:
            st.plotly_chart(fig_top, use_container_width=True)
    
    # Покрытие (если есть)
    fig_coverage = plot_bgc_coverage(df)
    if fig_coverage:
        st.plotly_chart(fig_coverage, use_container_width=True)
