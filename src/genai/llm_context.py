"""
Módulo para enriquecer o contexto da LLM com dados de múltiplas tabelas
"""
import pandas as pd
from typing import Dict, List, Optional
from src.data.data_manager import get_data_manager


class LLMContextEnricher:
    """Enriquece prompts da LLM com contexto de múltiplas tabelas"""
    
    def __init__(self):
        self.data_manager = get_data_manager()
        
    def extract_intent(self, user_message: str) -> Dict:
        """
        Extrai a intenção do usuário e entidades mencionadas
        (versão simples - pode ser melhorada com NLP)
        """
        message_lower = user_message.lower()
        
        intent = {
            "needs_data": False,
            "tables_needed": [],
            "entities": {},
            "query_type": "general"
        }
        
        # Detecta menções a modelos de carros
        modelos = self.data_manager.get_unique_values("casco0", "modelo")
        for modelo in modelos:
            if modelo.lower() in message_lower:
                intent["entities"]["modelo"] = modelo
                intent["needs_data"] = True
                intent["tables_needed"].append("casco0")
                
        # Detecta menções a regiões
        if any(word in message_lower for word in ["região", "regiao", "sp", "rj", "mg"]):
            intent["needs_data"] = True
            intent["tables_needed"].append("casco0")
            
        # Detecta perguntas sobre prêmios
        if any(word in message_lower for word in ["prêmio", "premio", "preço", "preco", "valor", "custo"]):
            intent["query_type"] = "pricing"
            intent["needs_data"] = True
            intent["tables_needed"].append("casco0")
            
        # Detecta perguntas sobre sinistros
        if any(word in message_lower for word in ["sinistro", "acidente", "colisão", "roubo"]):
            intent["query_type"] = "claims"
            intent["needs_data"] = True
            
        return intent
    
    def get_relevant_data(self, intent: Dict) -> Dict[str, pd.DataFrame]:
        """Busca dados relevantes baseado na intenção"""
        data = {}
        
        if not intent["needs_data"]:
            return data
            
        # Busca dados da tabela casco0 se necessário
        if "casco0" in intent["tables_needed"]:
            df_casco0 = self.data_manager.get_table("casco0")
            
            # Filtra por modelo se mencionado
            if "modelo" in intent["entities"]:
                modelo = intent["entities"]["modelo"]
                df_filtered = df_casco0[df_casco0["modelo"] == modelo]
                data["casco0_filtered"] = df_filtered
            else:
                # Retorna amostra se não houver filtro específico
                data["casco0_sample"] = df_casco0.sample(min(10, len(df_casco0)))
                
        return data
    
    def format_data_for_llm(self, data: Dict[str, pd.DataFrame]) -> str:
        """Formata os dados para incluir no prompt da LLM"""
        if not data:
            return ""
            
        context = "\n\n📊 **DADOS RELEVANTES:**\n\n"
        
        for table_name, df in data.items():
            if df.empty:
                continue
                
            context += f"**{table_name}** ({len(df)} registros):\n"
            
            # Colunas mais relevantes
            relevant_cols = [
                "modelo", "ano", "sexo", "regiao_desc", "faixa_desc",
                "premio1", "freq_sin1", "indeniz1"
            ]
            
            display_cols = [col for col in relevant_cols if col in df.columns]
            
            if len(df) <= 5:
                # Mostra todos os registros se forem poucos
                context += df[display_cols].to_string(index=False)
            else:
                # Mostra estatísticas agregadas
                context += "Estatísticas:\n"
                numeric_cols = df[display_cols].select_dtypes(include='number').columns
                
                for col in numeric_cols:
                    context += f"  - {col}: média={df[col].mean():.2f}, "
                    context += f"min={df[col].min():.2f}, max={df[col].max():.2f}\n"
                    
            context += "\n"
            
        return context
    
    def enrich_prompt(self, user_message: str, chat_history: List = None) -> str:
        """
        Enriquece o prompt do usuário com contexto relevante
        """
        # Extrai intenção
        intent = self.extract_intent(user_message)
        
        # Busca dados relevantes
        relevant_data = self.get_relevant_data(intent)
        
        # Formata dados
        data_context = self.format_data_for_llm(relevant_data)
        
        # Monta prompt enriquecido
        enriched_prompt = f"""Você é um assistente especializado em seguros automotivos.

{data_context}

**Instruções:**
- Use os dados fornecidos acima para responder de forma precisa
- Se não houver dados suficientes, seja honesto sobre as limitações
- Forneça respostas claras e objetivas
- Quando relevante, mencione tendências nos dados

**Histórico da conversa:**
{self._format_history(chat_history) if chat_history else "Nenhum histórico anterior."}

**Pergunta do usuário:**
{user_message}

**Sua resposta:**"""
        
        return enriched_prompt
    
    def _format_history(self, history: List) -> str:
        """Formata o histórico de mensagens"""
        if not history:
            return ""
            
        formatted = []
        for role, content in history[-5:]:  # Últimas 5 mensagens
            formatted.append(f"{role.upper()}: {content}")
            
        return "\n".join(formatted)
    
    def get_calculator_context(self, 
                               modelo: str, 
                               ano: int, 
                               sexo: str,
                               regiao_desc: str, 
                               faixa_desc: str) -> Dict:
        """
        Busca contexto adicional para a calculadora
        """
        context = {
            "tabelas_usadas": ["casco0"],
            "dados_complementares": {}
        }
        
        # Dados principais
        df_casco0 = self.data_manager.get_table("casco0")
        
        # Estatísticas do modelo
        df_modelo = df_casco0[df_casco0["modelo"] == modelo]
        if not df_modelo.empty:
            context["dados_complementares"]["estatisticas_modelo"] = {
                "total_registros": len(df_modelo),
                "premio_medio": df_modelo["premio1"].mean(),
                "premio_min": df_modelo["premio1"].min(),
                "premio_max": df_modelo["premio1"].max(),
            }
        
        # Estatísticas da região
        df_regiao = df_casco0[df_casco0["regiao_desc"] == regiao_desc]
        if not df_regiao.empty:
            context["dados_complementares"]["estatisticas_regiao"] = {
                "total_registros": len(df_regiao),
                "premio_medio": df_regiao["premio1"].mean(),
                "modelos_populares": df_regiao["modelo"].value_counts().head(3).to_dict()
            }
            
        return context


# Instância global
_enricher = None


def get_context_enricher() -> LLMContextEnricher:
    """Retorna a instância global do enriquecedor"""
    global _enricher
    if _enricher is None:
        _enricher = LLMContextEnricher()
    return _enricher