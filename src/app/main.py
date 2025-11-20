import streamlit as st
import sys
import os

# -------------------------------------------------------
# 1. Ajusta o sys.path ANTES de importar qualquer coisa
# -------------------------------------------------------
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

# Importações
from src.genai.llm_client import llm
from src.app.calculator import calcular_premio
from src.app.data_manager import get_data_manager
from src.genai.llm_context import get_context_enricher

# ------------------------------
# CONFIGURAÇÃO DA APLICAÇÃO
# ------------------------------
st.set_page_config(
    page_title="SeguraBOT", 
    page_icon="🚗",
    layout="wide"
)

# Inicializa sessão
if "page" not in st.session_state:
    st.session_state["page"] = "chat"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Inicializa gerenciador de dados
@st.cache_resource
def init_data_manager():
    """Inicializa o gerenciador de dados (cached)"""
    data_manager = get_data_manager()
    # Pré-carrega todas as tabelas
    data_manager.load_all_tables()
    return data_manager

# Carrega dados na inicialização
data_manager = init_data_manager()

# ------------------------------
# FUNÇÃO PARA TELA DE CHAT
# ------------------------------
def chat_page():
    st.title("💬 Chatbot Assistente de Seguros")
    
    # Sidebar com informações
    with st.sidebar:
        st.markdown("### 📊 Sistema")
        
        # Botão para calculadora
        if st.button("🧮 Ir para Calculadora", use_container_width=True):
            st.session_state["page"] = "calculadora"
            st.rerun()
        
        st.markdown("---")
        
        # Informações sobre dados
        st.markdown("### 📚 Fontes de Dados")
        enricher = get_context_enricher()
        data_summary = data_manager.get_all_tables_summary()
        st.markdown(data_summary)
        
        st.markdown("---")
        
        # Botão para limpar conversa
        if st.button("🗑️ Limpar Conversa", use_container_width=True):
            st.session_state["messages"] = []
            st.rerun()

    st.markdown("### Converse com o assistente:")
    
    # Container para mensagens
    chat_container = st.container()
    
    with chat_container:
        # Mostrar mensagens anteriores
        for role, content in st.session_state["messages"]:
            with st.chat_message(role):
                st.markdown(content)

    # Input do usuário (sempre no fundo)
    prompt = st.chat_input("Digite sua mensagem aqui...")
    
    if prompt:
        # Salva a mensagem do usuário
        st.session_state["messages"].append(("user", prompt))
        
        with st.chat_message("user"):
            st.markdown(prompt)

        # Processa a mensagem com contexto enriquecido
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                # Obtém enriquecedor de contexto
                enricher = get_context_enricher()
                
                # Enriquece o prompt com dados relevantes
                prompt_enriquecido = enricher.enrich_prompt(
                    prompt, 
                    st.session_state["messages"]
                )
                
                # Chama a LLM com contexto enriquecido
                resposta = llm.invoke(prompt_enriquecido)
                resposta_texto = resposta.content if hasattr(resposta, "content") else str(resposta)
                
                st.markdown(resposta_texto)

        # Salva a resposta
        st.session_state["messages"].append(("assistant", resposta_texto))
        
        # Force rerun para atualizar a interface
        st.rerun()


# ------------------------------
# PÁGINA DE BOAS-VINDAS
# ------------------------------
def welcome_page():
    """Página de boas-vindas (opcional)"""
    st.title("🚗 Sistema de Seguros Automotivos")
    
    st.markdown("""
    ## Bem-vindo ao seu Assistente Inteligente de Seguros!
    
    Este sistema utiliza múltiplas fontes de dados e inteligência artificial para:
    
    - 💬 **Responder perguntas** sobre seguros automotivos
    - 🧮 **Calcular prêmios** personalizados
    - 📊 **Analisar tendências** de mercado
    - 🔍 **Fornecer insights** baseados em dados históricos
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💬 Iniciar Chat", use_container_width=True, type="primary"):
            st.session_state["page"] = "chat"
            st.rerun()
    
    with col2:
        if st.button("🧮 Ir para Calculadora", use_container_width=True):
            st.session_state["page"] = "calculadora"
            st.rerun()
    
    # Mostra resumo dos dados
    st.markdown("---")
    st.markdown("### 📊 Dados Disponíveis")
    st.info(data_manager.get_all_tables_summary())


# ------------------------------
# ROTAS (controla as telas)
# ------------------------------
if st.session_state["page"] == "welcome":
    welcome_page()

elif st.session_state["page"] == "chat":
    chat_page()

elif st.session_state["page"] == "calculadora":
    calcular_premio()