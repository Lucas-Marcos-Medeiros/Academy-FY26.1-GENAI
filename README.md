# Chat Simples em Streamlit

Este é um chat simples para o Academy

## Como executar

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Execute a aplicação:
```bash
streamlit run chat_streamlit.py
```

# 📚 Guia de Configuração - Sistema Multi-Tabelas

## 🎯 Visão Geral

Este sistema permite integrar múltiplas tabelas CSV para enriquecer as respostas do chatbot e os cálculos da calculadora.

## 📁 Estrutura de Arquivos

```
projeto/
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── data_manager.py      # Gerenciador de tabelas
│   │   └── llm_context.py       # Enriquecedor de contexto
│   ├── app/
│   │   ├── main.py               # Aplicação principal
│   │   └── calculator.py         # Calculadora
│   └── genai/
│       └── llm_client.py         # Cliente LLM
└── data/
    ├── casco_tratadoA.csv        # Tabela principal
    ├── sinistros.csv             # Exemplo: tabela adicional
    ├── regioes.csv               # Exemplo: tabela adicional
    └── modelos.csv               # Exemplo: tabela adicional
```

## 🔧 Como Adicionar Uma Nova Tabela

### Passo 1: Adicione o arquivo CSV

Coloque seu arquivo CSV na pasta `data/`:

```
data/
└── minha_nova_tabela.csv
```

### Passo 2: Registre a tabela no data_manager.py

Edite a função `_initialize_tables()` em `src/data/data_manager.py`:

```python
def _initialize_tables(manager: DataManager):
    """Inicializa as configurações das tabelas"""
    
    # Tabela existente
    manager.register_table(TableConfig(
        name="casco",
        file_path="casco_tratadoA.csv",
        description="Dados de seguros de casco automotivo",
        key_columns=["modelo", "ano", "sexo", "regiao_desc", "faixa_desc"]
    ))
    
    # NOVA TABELA - Adicione aqui
    manager.register_table(TableConfig(
        name="sinistros",                              # Nome interno
        file_path="sinistros.csv",                     # Nome do arquivo
        description="Histórico de sinistros",          # Descrição
        key_columns=["modelo", "tipo", "data", "valor"] # Colunas principais
    ))
```

### Passo 3: Use a tabela no código

#### No Chatbot (llm_context.py):

```python
def extract_intent(self, user_message: str) -> Dict:
    message_lower = user_message.lower()
    
    # Detecta menção a sinistros
    if "sinistro" in message_lower or "acidente" in message_lower:
        intent["tables_needed"].append("sinistros")
        
    return intent
```

#### Na Calculadora (calculator.py):

```python
def calcular_premio_atuarial(modelo, ano, sexo, regiao_desc, faixa_desc):
    # Carrega tabelas
    data_manager = get_data_manager()
    df_casco = data_manager.get_table("casco")
    df_sinistros = data_manager.get_table("sinistros")  # Nova tabela
    
    # Faz merge se necessário
    df_completo = data_manager.merge_tables(
        "casco", 
        "sinistros", 
        on="modelo", 
        how="left"
    )
    
    # Continue com o cálculo...
```

## 📊 Exemplos de Tabelas Úteis

### 1. Tabela de Sinistros
```csv
modelo,tipo_sinistro,data,valor,regiao
CIVIC,COLISAO,2024-01-15,15000.00,SP
COROLLA,ROUBO,2024-02-20,45000.00,RJ
```

**Uso:** Enriquecer análise de risco por modelo

### 2. Tabela de Regiões
```csv
regiao_desc,estado,indice_risco,populacao,frota
São Paulo,SP,1.15,12000000,8500000
Rio de Janeiro,RJ,1.22,6500000,3200000
```

**Uso:** Ajustar prêmios por características regionais

### 3. Tabela de Modelos
```csv
modelo,marca,categoria,valor_fipe,ano_lancamento
CIVIC,HONDA,SEDAN,120000,2020
COROLLA,TOYOTA,SEDAN,135000,2021
```

**Uso:** Adicionar informações sobre veículos

### 4. Tabela de Coberturas
```csv
cobertura,descricao,custo_adicional,franquia
BASICA,Cobertura básica,0,2000
COMPLETA,Cobertura completa,500,1000
PREMIUM,Cobertura premium,1200,500
```

**Uso:** Oferecer diferentes níveis de cobertura

## 🔍 Consultando Múltiplas Tabelas

### Consulta Simples
```python
data_manager = get_data_manager()
df = data_manager.get_table("sinistros")

# Filtra sinistros por modelo
df_civic = df[df["modelo"] == "CIVIC"]
```

### Consulta com Filtros
```python
results = data_manager.query_tables({
    "casco": {"modelo": "CIVIC", "ano": 2020},
    "sinistros": {"tipo": "COLISAO"}
})

df_casco = results["casco"]
df_sinistros = results["sinistros"]
```

### Merge de Tabelas
```python
# Combina dados de casco com sinistros
df_completo = data_manager.merge_tables(
    "casco", 
    "sinistros", 
    on="modelo",
    how="inner"
)
```

### Valores Únicos
```python
# Lista todos os modelos disponíveis
modelos = data_manager.get_unique_values("casco", "modelo")

# Lista todos os tipos de sinistro
tipos = data_manager.get_unique_values("sinistros", "tipo_sinistro")
```

## 🤖 Integrando com a LLM

O sistema automaticamente enriquece os prompts da LLM com dados relevantes:

```python
# O usuário pergunta: "Qual o risco do CIVIC em SP?"

# O sistema automaticamente:
# 1. Detecta menção ao modelo "CIVIC"
# 2. Detecta menção à região "SP"
# 3. Busca dados nas tabelas relevantes
# 4. Formata os dados
# 5. Envia para a LLM com contexto completo
```

## 🎯 Boas Práticas

### ✅ Faça

- Mantenha nomes de colunas consistentes entre tabelas relacionadas
- Use colunas-chave (IDs) para fazer joins
- Documente o propósito de cada tabela
- Teste consultas com dados reais antes de colocar em produção

### ❌ Evite

- Tabelas muito grandes (> 100MB) sem indexação
- Duplicação de dados entre tabelas
- Nomes de colunas ambíguos
- Falta de validação de dados

## 🚀 Dicas de Performance

1. **Cache de Dados:** O sistema já usa `@st.cache_resource` para carregar tabelas
2. **Filtragem Precoce:** Filtre dados antes de fazer merge
3. **Seleção de Colunas:** Carregue apenas colunas necessárias
4. **Agregações:** Use pandas para agregar antes de enviar para LLM

## 📝 Exemplo Completo

```python
# 1. Registra tabela
manager.register_table(TableConfig(
    name="historico_precos",
    file_path="precos_historicos.csv",
    description="Histórico de preços de seguros",
    key_columns=["modelo", "mes", "ano"]
))

# 2. Usa na calculadora
def calcular_premio_atuarial(...):
    dm = get_data_manager()
    df_precos = dm.get_table("historico_precos")
    
    # Filtra últimos 12 meses
    df_recente = df_precos[df_precos["mes"] >= "2024-01"]
    
    # Calcula média
    preco_medio = df_recente["valor"].mean()
    
    # Ajusta cálculo com base no histórico
    premio_estimado *= (preco_medio / premio_base)

# 3. Usa no chatbot (automático via llm_context.py)
```

## 🆘 Troubleshooting

### Erro: "Tabela não encontrada"
- Verifique se registrou a tabela em `_initialize_tables()`
- Confirme que o arquivo CSV existe na pasta `data/`

### Erro: "Coluna não existe"
- Use `df.columns` para listar colunas disponíveis
- Verifique se o nome da coluna está correto (case-sensitive)

### Performance lenta
- Reduza o tamanho das tabelas com `.sample()` ou filtros
- Use agregações antes de enviar dados para LLM
- Considere criar views/tabelas pré-processadas

## 📚 Recursos Adicionais

- Documentação Pandas: https://pandas.pydata.org/docs/
- Streamlit Docs: https://docs.streamlit.io/
- LangChain: https://python.langchain.com/docs/

---

**Dúvidas?** Consulte o código-fonte ou abra uma issue no repositório.



