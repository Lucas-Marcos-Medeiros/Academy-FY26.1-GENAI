"""
Módulo para análises temporais entre os dois semestres de 2019
"""
import pandas as pd
import streamlit as st
from typing import Dict, List, Optional
from src.app.data_manager import get_data_manager


class TemporalAnalyzer:
    """Analisa tendências temporais entre os semestres"""
    
    def __init__(self):
        self.data_manager = get_data_manager()
        
    def get_price_evolution(self, modelo: Optional[str] = None) -> Dict:
        """
        Analisa a evolução de preços entre semestres
        
        Args:
            modelo: Se fornecido, analisa apenas este modelo
            
        Returns:
            Dicionário com estatísticas de evolução
        """
        df_sem1 = self.data_manager.get_table("casco_sem1")
        df_sem2 = self.data_manager.get_table("casco_sem2")
        
        if modelo:
            df_sem1 = df_sem1[df_sem1["modelo"] == modelo]
            df_sem2 = df_sem2[df_sem2["modelo"] == modelo]
        
        stats = {
            "modelo": modelo if modelo else "Todos",
            "premio_medio_sem1": df_sem1["premio1"].mean() if not df_sem1.empty else 0,
            "premio_medio_sem2": df_sem2["premio1"].mean() if not df_sem2.empty else 0,
            "registros_sem1": len(df_sem1),
            "registros_sem2": len(df_sem2),
        }
        
        if stats["premio_medio_sem1"] > 0:
            stats["variacao_percentual"] = (
                (stats["premio_medio_sem2"] - stats["premio_medio_sem1"]) / 
                stats["premio_medio_sem1"] * 100
            )
        else:
            stats["variacao_percentual"] = None
            
        return stats
    
    def get_top_growing_models(self, top_n: int = 10) -> pd.DataFrame:
        """
        Retorna os modelos com maior crescimento de prêmio
        
        Args:
            top_n: Número de modelos a retornar
            
        Returns:
            DataFrame com modelos ordenados por crescimento
        """
        df_sem1 = self.data_manager.get_table("casco_sem1")
        df_sem2 = self.data_manager.get_table("casco_sem2")
        
        # Agrupa por modelo
        agg_sem1 = df_sem1.groupby("modelo")["premio1"].mean().reset_index()
        agg_sem1.columns = ["modelo", "premio_sem1"]
        
        agg_sem2 = df_sem2.groupby("modelo")["premio1"].mean().reset_index()
        agg_sem2.columns = ["modelo", "premio_sem2"]
        
        # Merge
        comparison = pd.merge(agg_sem1, agg_sem2, on="modelo")
        
        # Calcula variação
        comparison["variacao_abs"] = comparison["premio_sem2"] - comparison["premio_sem1"]
        comparison["variacao_pct"] = (
            comparison["variacao_abs"] / comparison["premio_sem1"] * 100
        )
        
        # Ordena por maior crescimento
        return comparison.nlargest(top_n, "variacao_pct")
    
    def get_top_declining_models(self, top_n: int = 10) -> pd.DataFrame:
        """
        Retorna os modelos com maior queda de prêmio
        """
        df_sem1 = self.data_manager.get_table("casco_sem1")
        df_sem2 = self.data_manager.get_table("casco_sem2")
        
        agg_sem1 = df_sem1.groupby("modelo")["premio1"].mean().reset_index()
        agg_sem1.columns = ["modelo", "premio_sem1"]
        
        agg_sem2 = df_sem2.groupby("modelo")["premio1"].mean().reset_index()
        agg_sem2.columns = ["modelo", "premio_sem2"]
        
        comparison = pd.merge(agg_sem1, agg_sem2, on="modelo")
        comparison["variacao_abs"] = comparison["premio_sem2"] - comparison["premio_sem1"]
        comparison["variacao_pct"] = (
            comparison["variacao_abs"] / comparison["premio_sem1"] * 100
        )
        
        return comparison.nsmallest(top_n, "variacao_pct")
    
    def compare_regions(self) -> pd.DataFrame:
        """
        Compara a evolução de prêmios por região
        """
        return self.data_manager.compare_periods(
            metric="premio1",
            group_by=["regiao_desc"]
        )
    
    def get_claims_trend(self, modelo: Optional[str] = None) -> Dict:
        """
        Analisa tendência de sinistralidade
        """
        df_sem1 = self.data_manager.get_table("casco_sem1")
        df_sem2 = self.data_manager.get_table("casco_sem2")
        
        if modelo:
            df_sem1 = df_sem1[df_sem1["modelo"] == modelo]
            df_sem2 = df_sem2[df_sem2["modelo"] == modelo]
        
        # Busca colunas de sinistros
        freq_cols = [c for c in df_sem1.columns if "freq_sin" in c]
        
        stats = {
            "modelo": modelo if modelo else "Todos",
            "sinistralidade_sem1": 0,
            "sinistralidade_sem2": 0,
        }
        
        if freq_cols:
            stats["sinistralidade_sem1"] = df_sem1[freq_cols].mean().mean()
            stats["sinistralidade_sem2"] = df_sem2[freq_cols].mean().mean()
            
            if stats["sinistralidade_sem1"] > 0:
                stats["variacao_sinistros"] = (
                    (stats["sinistralidade_sem2"] - stats["sinistralidade_sem1"]) / 
                    stats["sinistralidade_sem1"] * 100
                )
            else:
                stats["variacao_sinistros"] = None
                
        return stats


def render_temporal_dashboard():
    """
    Renderiza dashboard de análise temporal no Streamlit
    """
    st.title("📈 Análise Temporal - 2019")
    
    analyzer = TemporalAnalyzer()
    
    # Overview geral
    st.markdown("### 📊 Visão Geral")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**1º Semestre 2019**")
        df_sem1 = analyzer.data_manager.get_table("casco_sem1")
        st.metric("Total de Registros", f"{len(df_sem1):,}")
        st.metric("Prêmio Médio", f"R$ {df_sem1['premio1'].mean():,.2f}")
        
    with col2:
        st.markdown("**2º Semestre 2019**")
        df_sem2 = analyzer.data_manager.get_table("casco_sem2")
        st.metric("Total de Registros", f"{len(df_sem2):,}")
        st.metric("Prêmio Médio", f"R$ {df_sem2['premio1'].mean():,.2f}")
    
    st.markdown("---")
    
    # Top modelos com crescimento
    st.markdown("### 📈 Top 10 - Maior Crescimento de Prêmio")
    df_growing = analyzer.get_top_growing_models(10)
    
    if not df_growing.empty:
        for idx, row in df_growing.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.write(f"**{row['modelo']}**")
            with col2:
                st.write(f"R$ {row['premio_sem1']:,.2f}")
            with col3:
                st.write(f"R$ {row['premio_sem2']:,.2f}")
            with col4:
                st.write(f"🔺 {row['variacao_pct']:+.2f}%")
    
    st.markdown("---")
    
    # Top modelos com queda
    st.markdown("### 📉 Top 10 - Maior Redução de Prêmio")
    df_declining = analyzer.get_top_declining_models(10)
    
    if not df_declining.empty:
        for idx, row in df_declining.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.write(f"**{row['modelo']}**")
            with col2:
                st.write(f"R$ {row['premio_sem1']:,.2f}")
            with col3:
                st.write(f"R$ {row['premio_sem2']:,.2f}")
            with col4:
                st.write(f"🔻 {row['variacao_pct']:+.2f}%")
    
    st.markdown("---")
    
    # Análise por região
    st.markdown("### 🗺️ Evolução por Região")
    df_regions = analyzer.compare_regions()
    
    if not df_regions.empty:
        st.dataframe(
            df_regions.style.format({
                "premio1_sem1": "R$ {:,.2f}",
                "premio1_sem2": "R$ {:,.2f}",
                "variacao_absoluta": "R$ {:,.2f}",
                "variacao_percentual": "{:+.2f}%"
            }),
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Análise personalizada
    st.markdown("### 🔍 Análise Personalizada")
    
    # Obtém modelos da tabela combinada
    df_combined = analyzer.data_manager.get_combined_casco_data()
    modelos = sorted(df_combined["modelo"].dropna().unique(), key=lambda s: str(s).strip().lower())
    modelo_selecionado = st.selectbox("Selecione um modelo:", ["Todos"] + list(modelos))
    
    if st.button("Analisar", type="primary"):
        modelo = None if modelo_selecionado == "Todos" else modelo_selecionado
        
        # Evolução de preços
        stats_preco = analyzer.get_price_evolution(modelo)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Prêmio 1º Sem",
                f"R$ {stats_preco['premio_medio_sem1']:,.2f}"
            )
        
        with col2:
            st.metric(
                "Prêmio 2º Sem",
                f"R$ {stats_preco['premio_medio_sem2']:,.2f}"
            )
        
        with col3:
            if stats_preco["variacao_percentual"] is not None:
                st.metric(
                    "Variação",
                    f"{abs(stats_preco['variacao_percentual']):.2f}%",
                    delta=f"{stats_preco['variacao_percentual']:+.2f}%"
                )
        
        # Tendência de sinistros
        stats_sinistros = analyzer.get_claims_trend(modelo)
        
        st.markdown("**Sinistralidade:**")
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "1º Semestre",
                f"{stats_sinistros['sinistralidade_sem1']:.6f}"
            )
        
        with col2:
            st.metric(
                "2º Semestre",
                f"{stats_sinistros['sinistralidade_sem2']:.6f}"
            )


# Instância global
_analyzer = None


def get_temporal_analyzer() -> TemporalAnalyzer:
    """Retorna instância global do analisador"""
    global _analyzer
    if _analyzer is None:
        _analyzer = TemporalAnalyzer()
    return _analyzer