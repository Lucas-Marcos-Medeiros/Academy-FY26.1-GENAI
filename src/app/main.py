import streamlit as st
import pandas as pd
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.genai.llm_client import llm
from src.insurance.calculator import calcular_premio

st.set_page_config(page_title="Seguro Auto Inteligente", layout="centered")

st.title(" Calculadora Inteligente de Prêmio de Seguro")

# Carrega a base completa
df = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', 'data', 'casco_tratadoA.csv'))

st.markdown("###  Informações do veículo e do segurado")

modelo = st.selectbox("Modelo do carro", sorted(df["modelo"].unique()))
ano = st.number_input("Ano do veículo", 1990, 2025, 2016)
sexo = st.selectbox("Sexo do condutor", ["M", "F", "Jurídica", "Não definido"])
regiao_desc = st.selectbox("Região", sorted(df["regiao_desc"].unique()))
faixa_desc = st.selectbox("Faixa etária", sorted(df["faixa_desc"].unique()))

if st.button("Calcular prêmio"):
    resultado = calcular_premio(df, modelo, ano, sexo, regiao_desc, faixa_desc)

    if resultado["erro"]:
        st.error(resultado["mensagem"])
    else:
        st.subheader("JSON - Resultado do Cálculo")
        st.write(resultado)

        # Envia para a LLM explicar
        explicacao = llm.invoke(
            f"""
            Explique esse cálculo de seguro de forma simples:

            {resultado}
            """
        )

        st.subheader("Explicação da IA")
        st.write(explicacao.content)