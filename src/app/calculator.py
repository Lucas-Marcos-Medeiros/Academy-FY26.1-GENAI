import streamlit as st
import pandas as pd
import os
import sys

# Adiciona o caminho raiz ao Python
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

# Importações
from src.genai.llm_client import llm
from src.data.data_manager import get_data_manager
from src.genai.llm_context import get_context_enricher


# ============================================================
# FUNÇÃO DE CÁLCULO (ATUARIAL) - VERSÃO MULTI-TABELA
# ============================================================
def calcular_premio_atuarial(modelo, ano, sexo, regiao_desc, faixa_desc):
    """
    Calcula um prêmio estimado de seguro com base em médias históricas
    e fatores empíricos de múltiplas fontes de dados.
    """
    
    # Obtém o gerenciador de dados
    data_manager = get_data_manager()
    enricher = get_context_enricher()
    
    # Carrega tabela principal
    df = data_manager.get_table("casco0")
    
    # --- 1. Filtrar por modelo ---
    df_modelo = df[df["modelo"] == modelo]
    if df_modelo.empty:
        return {"erro": True, "mensagem": f"Modelo '{modelo}' não encontrado."}

    # --- 2. Faixa ---
    df_faixa = df_modelo[df_modelo["faixa_desc"] == faixa_desc]
    if df_faixa.empty:
        df_faixa = df_modelo  # fallback

    # --- 3. Região ---
    df_regiao = df_faixa[df_faixa["regiao_desc"] == regiao_desc]
    if df_regiao.empty:
        df_regiao = df_faixa  # fallback

    registro = df_regiao.iloc[0].to_dict()

    premio_hist = registro.get("premio1", 0)

    # Frequências e severidades
    freq_cols = [c for c in df.columns if "freq_sin" in c]
    inden_cols = [c for c in df.columns if "indeniz" in c]

    freq_total = sum(registro.get(c, 0) for c in freq_cols)
    inden_total = sum(registro.get(c, 0) for c in inden_cols)

    frequencia_media = freq_total / len(freq_cols) if freq_cols else 0
    severidade_media = inden_total / len(inden_cols) if inden_cols else 0

    premio_estimado = premio_hist

    # Ajuste por sinistros
    if frequencia_media > 0 and severidade_media > 0:
        premio_estimado = frequencia_media * severidade_media

    # Ajuste por idade
    fator_idade = max(0.7, min(1.2, (2025 - ano) * 0.01 + 0.9))
    premio_estimado *= fator_idade

    # Ajuste por sexo
    if sexo == "M":
        premio_estimado *= 1.10
    elif sexo == "F":
        premio_estimado *= 0.97

    # Ajuste por região
    if "SP" in regiao_desc:
        premio_estimado *= 1.15
    elif "RJ" in regiao_desc:
        premio_estimado *= 1.22

    # Busca contexto adicional de outras tabelas
    contexto_adicional = enricher.get_calculator_context(
        modelo, ano, sexo, regiao_desc, faixa_desc
    )

    return {
        "erro": False,
        "modelo": modelo,
        "ano": ano,
        "sexo": sexo,
        "regiao": regiao_desc,
        "faixa": faixa_desc,
        "premio_estimado": round(premio_estimado, 2),
        "premio_historico": round(premio_hist, 2),
        "frequencia": round(frequencia_media, 6),
        "severidade": round(severidade_media, 2),
        "registro_utilizado": df_regiao,
        "contexto_adicional": contexto_adicional,
    }


# ============================================================
# INTERFACE STREAMLIT
# ============================================================
def calcular_premio():

    st.title("🧮 Calculadora de Prêmio")

    if st.button("← Voltar"):
        st.session_state["page"] = "chat"
        st.rerun()

    # Obtém gerenciador de dados
    data_manager = get_data_manager()
    
    # Exibe informações sobre tabelas disponíveis
    with st.expander("📊 Fontes de Dados Utilizadas"):
        st.markdown(data_manager.get_all_tables_summary())

    df = data_manager.get_table("casco0")

    st.markdown("### Preencha os dados:")

    # Cria duas colunas para layout mais compacto
    col1, col2 = st.columns(2)

    # Ordenação dos dropdowns usando data_manager
    with col1:
        modelos = data_manager.get_unique_values("casco0", "modelo")
        modelo = st.selectbox("🚗 Modelo", modelos)
        
        sexos = data_manager.get_unique_values("casco0", "sexo")
        sexo = st.selectbox("👤 Sexo", sexos)
        
        faixas = data_manager.get_unique_values("casco0", "faixa_desc")
        faixa_desc = st.selectbox("📅 Faixa Etária", faixas)

    with col2:
        anos = sorted(
            pd.Series(df["ano"].dropna().unique()).astype(int).unique(), 
            reverse=True
        )
        ano = st.selectbox("📆 Ano", anos)
        
        regioes = data_manager.get_unique_values("casco0", "regiao_desc")
        regiao_desc = st.selectbox("📍 Região", regioes)

    st.markdown("---")

    if st.button("💰 Calcular Prêmio", type="primary", use_container_width=True):

        with st.spinner("Calculando..."):
            resultado = calcular_premio_atuarial(
                modelo, int(ano), sexo, regiao_desc, faixa_desc
            )

        if resultado["erro"]:
            st.error(resultado["mensagem"])
            return

        # Exibe resultado principal
        st.success("✅ Cálculo realizado com sucesso!")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Prêmio Estimado",
                value=f"R$ {resultado['premio_estimado']:,.2f}"
            )
        
        with col2:
            st.metric(
                label="Prêmio Histórico",
                value=f"R$ {resultado['premio_historico']:,.2f}"
            )
            
        with col3:
            diferenca = resultado['premio_estimado'] - resultado['premio_historico']
            st.metric(
                label="Diferença",
                value=f"R$ {abs(diferenca):,.2f}",
                delta=f"{(diferenca/resultado['premio_historico']*100):.1f}%" if resultado['premio_historico'] > 0 else "N/A"
            )

        # Detalhes técnicos
        with st.expander("📊 Detalhes Técnicos do Cálculo"):
            st.json({
                "modelo": resultado["modelo"],
                "ano": resultado["ano"],
                "sexo": resultado["sexo"],
                "regiao": resultado["regiao"],
                "faixa_etaria": resultado["faixa"],
                "frequencia_sinistros": resultado["frequencia"],
                "severidade_media": resultado["severidade"]
            })

        # Contexto adicional de outras tabelas
        if "contexto_adicional" in resultado and resultado["contexto_adicional"].get("dados_complementares"):
            with st.expander("🔍 Análise Comparativa (Multi-Tabelas)"):
                contexto = resultado["contexto_adicional"]["dados_complementares"]
                
                if "estatisticas_modelo" in contexto:
                    st.markdown("**📈 Estatísticas do Modelo:**")
                    stats = contexto["estatisticas_modelo"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Prêmio Médio", f"R$ {stats.get('premio_medio', 0):,.2f}")
                    with col2:
                        st.metric("Prêmio Mínimo", f"R$ {stats.get('premio_min', 0):,.2f}")
                    with col3:
                        st.metric("Prêmio Máximo", f"R$ {stats.get('premio_max', 0):,.2f}")
                
                if "estatisticas_regiao" in contexto:
                    st.markdown("**📍 Estatísticas da Região:**")
                    stats = contexto["estatisticas_regiao"]
                    st.metric("Prêmio Médio da Região", f"R$ {stats.get('premio_medio', 0):,.2f}")
                    
                    if "modelos_populares" in stats:
                        st.markdown("**Modelos mais segurados nesta região:**")
                        for modelo, qtd in list(stats["modelos_populares"].items())[:3]:
                            st.write(f"- {modelo}: {qtd} apólices")

        # =========================================
        # EXPLICAÇÃO PELA LLM COM CONTEXTO ENRIQUECIDO
        # =========================================
        st.markdown("---")
        
        with st.spinner("Gerando explicação personalizada..."):
            
            # Monta prompt enriquecido com dados de múltiplas tabelas
            prompt_explicacao = f"""
            Você é um especialista em seguros automotivos. Explique este cálculo de forma clara e objetiva.
            
            **Dados do Cálculo:**
            {resultado}
            
            **Instruções:**
            1. Explique o valor do prêmio calculado
            2. Destaque os principais fatores que influenciaram o valor
            3. Compare com as médias históricas quando relevante
            4. Seja objetivo e use linguagem acessível
            5. Limite sua resposta a 3-4 parágrafos
            """
            
            explicacao = llm.invoke(prompt_explicacao)

        st.subheader("🤖 Explicação da IA")
        st.info(explicacao.content)

        # Botão de download
        st.markdown("---")
        df_export = resultado["registro_utilizado"]
        csv = df_export.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="📥 Baixar Dados do Cálculo (CSV)",
            data=csv,
            file_name=f"calculo_premio_{modelo}_{ano}.csv",
            mime="text/csv",
            use_container_width=True
        )