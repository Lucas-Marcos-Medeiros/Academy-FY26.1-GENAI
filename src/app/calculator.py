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
from src.app.data_manager import get_data_manager
from src.genai.llm_context import get_context_enricher
from src.analises.auxiliary_data_analyzer import get_auxiliary_analyzer


# ============================================================
# FUNÇÃO DE CÁLCULO (ATUARIAL) - VERSÃO MULTI-TABELA
# ============================================================
def calcular_premio_atuarial(modelo, ano, sexo, regiao_desc, faixa_desc):
    """
    Calcula um prêmio estimado de seguro com base em médias históricas
    de ambos os semestres de 2019 e fatores empíricos.
    """
    
    # Obtém gerenciadores
    data_manager = get_data_manager()
    enricher = get_context_enricher()
    aux_analyzer = get_auxiliary_analyzer()
    
    # Carrega dados combinados dos dois semestres
    df = data_manager.get_combined_casco_data()
    
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
    
    # Busca análise de risco integrada com dados auxiliares
    # Mapeia regiao_desc para UF
    uf_map = {
        "São Paulo": "SP", "Rio de Janeiro": "RJ", "Minas Gerais": "MG",
        "Paraná": "PR", "Santa Catarina": "SC", "Rio Grande do Sul": "RS"
    }
    
    uf = None
    for estado, sigla in uf_map.items():
        if estado in regiao_desc:
            uf = sigla
            break
    
    # Análise de risco integrada
    perfil_risco = None
    if uf:
        perfil_risco = aux_analyzer.get_integrated_risk_profile(modelo, uf)
    
    # Análise de evolução entre semestres
    df_sem1 = df[df['semestre'] == 1]
    df_sem2 = df[df['semestre'] == 2]
    
    evolucao_semestral = {
        "tem_dados_sem1": False,
        "tem_dados_sem2": False,
        "variacao_premio": None,
        "variacao_sinistralidade": None
    }
    
    # Busca dados do modelo em cada semestre
    filtro_modelo = (df['modelo'] == modelo)
    dados_sem1 = df_sem1[filtro_modelo]
    dados_sem2 = df_sem2[filtro_modelo]
    
    if not dados_sem1.empty:
        evolucao_semestral["tem_dados_sem1"] = True
        evolucao_semestral["premio_medio_sem1"] = dados_sem1['premio1'].mean()
        
    if not dados_sem2.empty:
        evolucao_semestral["tem_dados_sem2"] = True
        evolucao_semestral["premio_medio_sem2"] = dados_sem2['premio1'].mean()
        
    # Calcula variação se houver dados de ambos períodos
    if evolucao_semestral["tem_dados_sem1"] and evolucao_semestral["tem_dados_sem2"]:
        p1 = evolucao_semestral["premio_medio_sem1"]
        p2 = evolucao_semestral["premio_medio_sem2"]
        evolucao_semestral["variacao_premio"] = ((p2 - p1) / p1 * 100) if p1 > 0 else None

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
        "evolucao_semestral": evolucao_semestral,
        "periodo_dados": registro.get("periodo", "Não especificado"),
        "perfil_risco": perfil_risco
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
        st.markdown("""
        **Dados de 2019 - Análise Semestral:**
        - 📅 **1º Semestre 2019:** casco_tratadoA.csv
        - 📅 **2º Semestre 2019:** casco_tratadoB.csv
        - 📊 **Base Combinada:** Permite análise temporal e comparação de tendências
        """)
        st.info(f"Total de registros: {len(data_manager.get_combined_casco_data()):,}")

    df = data_manager.get_combined_casco_data()

    st.markdown("### Preencha os dados:")

    # ===========================
    # FORMULÁRIO MELHORADO
    # ===========================
    with st.form("form_calculo"):
        
        # Linha 1: Modelo e Ano
        col1, col2 = st.columns(2)
        
        with col1:
            modelos = sorted(
                df["modelo"].dropna().unique(), 
                key=lambda s: str(s).strip().lower()
            )
            modelo = st.selectbox(
                "🚗 Modelo do Veículo",
                modelos,
                help="Selecione o modelo do veículo"
            )
        
        with col2:
            anos = sorted(df["ano"].dropna().astype(int).unique(), reverse=True)
            ano = st.selectbox(
                "📆 Ano de Fabricação",
                anos,
                help="Ano de fabricação do veículo"
            )
        
        # Linha 2: Sexo e Faixa Etária
        col3, col4 = st.columns(2)
        
        with col3:
            sexos = sorted(df["sexo"].dropna().unique(), key=lambda s: str(s).lower())
            sexo_map = {"M": "Masculino", "F": "Feminino"}
            sexo_display = [sexo_map.get(s, s) for s in sexos]
            sexo_selecionado = st.selectbox(
                "👤 Sexo do Condutor",
                sexo_display,
                help="Sexo do condutor principal"
            )
            # Converte de volta para M/F
            sexo_reverse_map = {v: k for k, v in sexo_map.items()}
            sexo = sexo_reverse_map.get(sexo_selecionado, sexos[0])
        
        with col4:
            faixas = sorted(df["faixa_desc"].dropna().unique(), key=lambda s: str(s).lower())
            faixa_desc = st.selectbox(
                "📅 Faixa Etária",
                faixas,
                help="Faixa etária do condutor principal"
            )
        
        # Linha 3: Região (coluna única para destaque)
        regiao_col = st.container()
        with regiao_col:
            regioes = sorted(df["regiao_desc"].dropna().unique(), key=lambda s: str(s).lower())
            regiao_desc = st.selectbox(
                "📍 Região",
                regioes,
                help="Estado ou região onde o veículo será segurado"
            )
        
        # Botão de submit centralizado e destacado
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            submitted = st.form_submit_button(
                "Calcular Prêmio",
                use_container_width=True,
            )

    # Só executa o cálculo quando clicar no botão do formulário
    if not submitted:
        return

    # =============================
    # EXECUÇÃO DO CÁLCULO
    # =============================
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

    # =========================================
    # Detalhes técnicos do cálculo
    # =========================================
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

    # =========================================
    # Contexto adicional de outras tabelas
    # =========================================
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
    # Evolução temporal
    # =========================================
    if "evolucao_semestral" in resultado:
        evolucao = resultado["evolucao_semestral"]
        
        if evolucao["tem_dados_sem1"] and evolucao["tem_dados_sem2"]:
            with st.expander("📈 Evolução Temporal - Análise Semestral 2019"):
                st.markdown("**Comparação entre 1º e 2º Semestre de 2019:**")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("1º Semestre", f"R$ {evolucao['premio_medio_sem1']:,.2f}")
                
                with col2:
                    st.metric("2º Semestre", f"R$ {evolucao['premio_medio_sem2']:,.2f}")
                
                with col3:
                    if evolucao["variacao_premio"] is not None:
                        variacao = evolucao["variacao_premio"]
                        st.metric("Variação", f"{abs(variacao):.2f}%", delta=f"{variacao:.2f}%")

    # =========================================
    # Análise de risco integrada
    # =========================================
    if "perfil_risco" in resultado and resultado["perfil_risco"]:
        perfil = resultado["perfil_risco"]
        
        with st.expander("🎯 Análise de Risco Integrada"):
            st.markdown(f"**Modelo:** {perfil['modelo']}")
            st.markdown(f"**Estado:** {perfil['estado']}")

            col1, col2 = st.columns(2)
            
            with col1:
                nivel_cor = {"Alto": "🔴", "Médio": "🟡", "Baixo": "🟢"}
                st.metric(
                    "Nível de Risco",
                    f"{nivel_cor.get(perfil['nivel_risco'], '')} {perfil['nivel_risco']}",
                    delta=f"Score: {perfil['risk_score']}/100"
                )

            with col2:
                st.info(perfil['recomendacao'])

    # =========================================
    # Explicação da IA
    # =========================================
    st.markdown("---")
    
    with st.spinner("Gerando explicação personalizada..."):
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

    st.subheader("Explicação da IA:")
    st.info(explicacao.content)

    # =========================================
    # Download CSV
    # =========================================
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