"""
Gerenciador centralizado para múltiplas tabelas de dados
"""
import pandas as pd
import os
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class TableConfig:
    """Configuração de uma tabela"""
    name: str
    file_path: str
    description: str
    key_columns: List[str]


class DataManager:
    """Gerencia o carregamento e acesso a múltiplas tabelas"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.tables: Dict[str, pd.DataFrame] = {}
        self.configs: Dict[str, TableConfig] = {}
        
    def register_table(self, config: TableConfig):
        """Registra uma nova tabela no sistema"""
        self.configs[config.name] = config
        
    def load_table(self, table_name: str) -> pd.DataFrame:
        """Carrega uma tabela específica"""
        if table_name in self.tables:
            return self.tables[table_name]
            
        if table_name not in self.configs:
            raise ValueError(f"Tabela '{table_name}' não registrada")
            
        config = self.configs[table_name]
        file_path = os.path.join(self.data_dir, config.file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
        self.tables[table_name] = pd.read_csv(file_path)
        return self.tables[table_name]
    
    def load_all_tables(self):
        """Carrega todas as tabelas registradas"""
        for table_name in self.configs.keys():
            self.load_table(table_name)
            
    def get_table(self, table_name: str) -> pd.DataFrame:
        """Retorna uma tabela carregada"""
        if table_name not in self.tables:
            self.load_table(table_name)
        return self.tables[table_name]
    
    def get_table_info(self, table_name: str) -> Dict:
        """Retorna informações sobre uma tabela"""
        df = self.get_table(table_name)
        config = self.configs[table_name]
        
        return {
            "name": config.name,
            "description": config.description,
            "rows": len(df),
            "columns": list(df.columns),
            "key_columns": config.key_columns,
            "sample": df.head(3).to_dict('records')
        }
    
    def get_all_tables_summary(self) -> str:
        """Retorna um resumo de todas as tabelas disponíveis"""
        summary = "📊 **Tabelas Disponíveis:**\n\n"
        
        for table_name, config in self.configs.items():
            df = self.get_table(table_name)
            summary += f"**{config.name}**\n"
            summary += f"- Descrição: {config.description}\n"
            summary += f"- Registros: {len(df):,}\n"
            summary += f"- Colunas principais: {', '.join(config.key_columns)}\n\n"
            
        return summary
    
    def query_tables(self, filters: Dict[str, Dict]) -> Dict[str, pd.DataFrame]:
        """
        Consulta múltiplas tabelas com filtros
        
        Exemplo:
        filters = {
            "casco0": {"modelo": "CIVIC", "ano": 2020},
            "sinistros": {"tipo": "COLISAO"}
        }
        """
        results = {}
        
        for table_name, filter_dict in filters.items():
            df = self.get_table(table_name)
            filtered_df = df.copy()
            
            for column, value in filter_dict.items():
                if column in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[column] == value]
                    
            results[table_name] = filtered_df
            
        return results
    
    def merge_tables(self, 
                     left_table: str, 
                     right_table: str, 
                     on: str, 
                     how: str = 'inner') -> pd.DataFrame:
        """Faz merge de duas tabelas"""
        left_df = self.get_table(left_table)
        right_df = self.get_table(right_table)
        
        return pd.merge(left_df, right_df, on=on, how=how)
    
    def get_unique_values(self, table_name: str, column: str) -> List:
        """Retorna valores únicos de uma coluna"""
        df = self.get_table(table_name)
        if column not in df.columns:
            return []
        return sorted(df[column].dropna().unique().tolist())


# Instância global (singleton)
_data_manager = None


def get_data_manager(data_dir: Optional[str] = None) -> DataManager:
    """Retorna a instância global do DataManager"""
    global _data_manager
    
    if _data_manager is None:
        if data_dir is None:
            # Caminho padrão
            data_dir = os.path.join(
                os.path.dirname(__file__), "..", "data"
            )
        _data_manager = DataManager(data_dir)
        _initialize_tables(_data_manager)
        
    return _data_manager


def _initialize_tables(manager: DataManager):
    """Inicializa as configurações das tabelas"""
    
    # Tabela principal de casco
    manager.register_table(TableConfig(
        name="casco0",
        file_path="casco_tratadoA.csv",
        description="Dados de seguros de casco0 automotivo",
        key_columns=["modelo", "ano", "sexo", "regiao_desc", "faixa_desc"]
    ))
    
    # Exemplo: Tabela de sinistros (adicione se existir)
    #manager.register_table(TableConfig(
    #    name="casco3",
    #    file_path="casco3_tratadoA.csv",
    #    description="Dados de seguros de casco3 automotivo",
    #    key_columns=["modelo", "ano", "exposicao", "regiao_desc"]
    # ))
    
    # Exemplo: Tabela de regiões (adicione se existir)
    # manager.register_table(TableConfig(
    #     name="regioes",
    #     file_path="regioes.csv",
    #     description="Informações detalhadas sobre regiões",
    #     key_columns=["regiao_desc", "estado", "indice_risco"]
    # ))
    
    # Exemplo: Tabela de modelos de veículos
    # manager.register_table(TableConfig(
    #     name="modelos",
    #     file_path="modelos.csv",
    #     description="Informações sobre modelos de veículos",
    #     key_columns=["modelo", "marca", "categoria", "valor_fipe"]
    # ))