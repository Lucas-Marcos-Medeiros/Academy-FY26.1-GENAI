import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.genai.llm_client import llm

st.set_page_config(page_title="Analisador IA de Produtos", layout="centered")

st.title("📊 Analisador Inteligente de Desempenho de Produtos")

df = pd.read_csv("src/data/produtos.csv")
st.dataframe(df)

st.markdown("### 🔍 Faça uma análise usando o modelo IA")
prompt = st.text_area("Escreva sua pergunta:", "Qual produto apresenta maior potencial de crescimento?")

if st.button("Gerar análise"):
    with st.spinner("Consultando IA..."):
        resposta = llm.invoke(
            f"Com base nos dados de produtos abaixo, responda: {prompt}\n\n{df.to_string(index=False)}"
        )
        st.success("✅ Análise gerada com sucesso!")
        st.markdown("### Resultado:")
        st.write(resposta.content)
