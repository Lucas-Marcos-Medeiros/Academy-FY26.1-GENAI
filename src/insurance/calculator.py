import pandas as pd

def calcular_premio(df, modelo, ano, sexo, regiao_desc, faixa_desc):
    """
    Calcula um prêmio estimado de seguro com base em médias históricas
    e fatores empíricos determinados pela base fornecida.
    """

    # --- 1. Filtrar por veículo ---
    df_modelo = df[df["modelo"] == modelo]

    if df_modelo.empty:
        return {
            "erro": True,
            "mensagem": f"Não encontrei registros para o modelo '{modelo}'."
        }

    # --- 2. Filtrar por faixa etária ---
    df_faixa = df_modelo[df_modelo["faixa_desc"] == faixa_desc]
    if df_faixa.empty:
        df_faixa = df_modelo  # fallback

    # --- 3. Filtrar por região ---
    df_regiao = df_faixa[df_faixa["regiao_desc"] == regiao_desc]
    if df_regiao.empty:
        df_regiao = df_faixa  # fallback

    registro = df_regiao.iloc[0].to_dict()

    # --- 4. Cálculo básico do prêmio puro ---
    exposicao = registro.get("exposicao1", 1)
    premio_hist = registro.get("premio1", 0)

    # Frequências e severidades (se existirem)
    freq_cols = [c for c in df.columns if "freq_sin" in c]
    inden_cols = [c for c in df.columns if "indeniz" in c]

    freq_total = sum(registro.get(c, 0) for c in freq_cols)
    inden_total = sum(registro.get(c, 0) for c in inden_cols)

    # Fórmulas atuariais simples
    frequencia_media = freq_total / len(freq_cols) if freq_cols else 0
    severidade_media = inden_total / len(inden_cols) if inden_cols else 0

    premio_estimado = premio_hist

    # Ajuste por frequência e severidade, se existirem dados
    if frequencia_media > 0 and severidade_media > 0:
        premio_estimado = frequencia_media * severidade_media

    # Ajuste por ano do veículo
    fator_idade = max(0.7, min(1.2, (2025 - ano) * 0.01 + 0.9))
    premio_estimado *= fator_idade

    # Ajuste por sexo
    if sexo == "M":
        premio_estimado *= 1.10
    elif sexo == "F":
        premio_estimado *= 0.97

    # Ajuste por região (exemplo)
    if "SP" in regiao_desc:
        premio_estimado *= 1.15
    elif "RJ" in regiao_desc:
        premio_estimado *= 1.22

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
    }
