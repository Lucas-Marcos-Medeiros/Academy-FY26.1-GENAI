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
        
        # Detecta separador e encoding apropriados
        if "acidentes" in table_name:
            # CSV com separador ; e encoding específico
            self.tables[table_name] = pd.read_csv(
                file_path, 
                sep=';', 
                encoding='latin1',
                na_values=['NA', 'N/A', ''],
                low_memory=False  # Evita warning de dtype
            )
        elif "seguranca" in table_name:
            # CSV sem header, precisa definir colunas
            self.tables[table_name] = pd.read_csv(
                file_path,
                header=None,
                names=["estado", "tipo_crime", "ano", "mes", "quantidade"],
                encoding='utf-8',
                low_memory=False
            )
        else:
            # CSV padrão - com low_memory=False para evitar warnings
            self.tables[table_name] = pd.read_csv(
                file_path,
                low_memory=False
            )
            
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
            "casco": {"modelo": "CIVIC", "ano": 2020},
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
    
    def combine_tables(self, table_names: List[str], add_period_column: bool = True) -> pd.DataFrame:
        """
        Combina múltiplas tabelas verticalmente (concatenação)
        
        Args:
            table_names: Lista de nomes das tabelas para combinar
            add_period_column: Se True, adiciona coluna identificando o período
            
        Returns:
            DataFrame combinado
        """
        dfs = []
        
        for i, table_name in enumerate(table_names):
            df = self.get_table(table_name).copy()
            
            if add_period_column:
                # Adiciona coluna de período baseada no nome da tabela
                if "sem1" in table_name:
                    df['periodo'] = "1º Semestre 2019"
                    df['semestre'] = 1
                elif "sem2" in table_name:
                    df['periodo'] = "2º Semestre 2019"
                    df['semestre'] = 2
                else:
                    df['periodo'] = table_name
                    df['semestre'] = i + 1
                    
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)
    
    def get_combined_casco_data(self) -> pd.DataFrame:
        """
        Retorna dados combinados dos dois semestres de 2019
        (cached para performance)
        """
        cache_key = "casco_combined"
        
        if cache_key not in self.tables:
            try:
                self.tables[cache_key] = self.combine_tables(
                    ["casco_sem1", "casco_sem2"],
                    add_period_column=True
                )
            except Exception as e:
                # Se falhar ao combinar, tenta retornar apenas o primeiro semestre
                print(f"Erro ao combinar tabelas: {e}")
                try:
                    df = self.get_table("casco_sem1").copy()
                    df['periodo'] = "1º Semestre 2019"
                    df['semestre'] = 1
                    self.tables[cache_key] = df
                except Exception as e2:
                    print(f"Erro ao carregar casco_sem1: {e2}")
                    # Retorna DataFrame vazio como último recurso
                    return pd.DataFrame()
            
        return self.tables[cache_key]
    
    def compare_periods(self, 
                       metric: str,
                       group_by: List[str],
                       table1: str = "casco_sem1",
                       table2: str = "casco_sem2") -> pd.DataFrame:
        """
        Compara uma métrica entre dois períodos
        
        Args:
            metric: Coluna numérica para comparar (ex: 'premio1')
            group_by: Colunas para agrupar (ex: ['modelo', 'regiao_desc'])
            table1: Primeira tabela (1º período)
            table2: Segunda tabela (2º período)
            
        Returns:
            DataFrame com comparação
        """
        df1 = self.get_table(table1)
        df2 = self.get_table(table2)
        
        # Agrupa e calcula média
        agg1 = df1.groupby(group_by)[metric].mean().reset_index()
        agg1.columns = list(group_by) + [f'{metric}_sem1']
        
        agg2 = df2.groupby(group_by)[metric].mean().reset_index()
        agg2.columns = list(group_by) + [f'{metric}_sem2']
        
        # Merge e calcula variação
        comparison = pd.merge(agg1, agg2, on=group_by, how='outer')
        comparison['variacao_absoluta'] = comparison[f'{metric}_sem2'] - comparison[f'{metric}_sem1']
        comparison['variacao_percentual'] = (
            (comparison['variacao_absoluta'] / comparison[f'{metric}_sem1']) * 100
        ).round(2)
        
        return comparison
    
    def get_unique_values(self, table_name: str, column: str) -> List:
        """Retorna valores únicos de uma coluna"""
        # Se for solicitado 'casco', usa a tabela combinada
        if table_name == "casco":
            df = self.get_combined_casco_data()
        else:
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
    
    # ========================================
    # TABELAS PRINCIPAIS - DADOS DE CASCO
    # ========================================
    
    # Tabela 1º semestre 2019
    manager.register_table(TableConfig(
        name="casco_sem1",
        file_path="casco_tratadoA.csv",
        description="Dados de seguros de casco - 1º Semestre 2019",
        key_columns=["modelo", "ano", "sexo", "regiao_desc", "faixa_desc"]
    ))
    
    # Tabela 2º semestre 2019
    manager.register_table(TableConfig(
        name="casco_sem2",
        file_path="casco_tratadoB.csv",
        description="Dados de seguros de casco - 2º Semestre 2019",
        key_columns=["modelo", "ano", "sexo", "regiao_desc", "faixa_desc"]
    ))
    
    # ========================================
    # TABELAS AUXILIARES - CONTEXTO ADICIONAL
    # ========================================
    
    # Acidentes 2019 - Causas e tipos
    manager.register_table(TableConfig(
        name="acidentes_2019",
        file_path="acidentes2019_todas_causas_tipos.csv",
        description="Dados de acidentes de trânsito em 2019 - causas, tipos e perfil dos envolvidos",
        key_columns=["uf", "causa_acidente", "tipo_acidente", "marca", "ano_fabricacao_veiculo", "sexo", "idade"]
    ))
    
    # Indicadores de segurança pública por UF
    manager.register_table(TableConfig(
        name="seguranca_publica",
        file_path="indicadoressegurancapublicauf.csv",
        description="Indicadores de roubos e furtos de veículos por estado (2015-2022)",
        key_columns=["estado", "tipo_crime", "ano", "mes"]
    ))
    
    # Projeções populacionais
    manager.register_table(TableConfig(
        name="projecoes_populacao",
        file_path="projecoes_grupos_etarios_quantidades.csv",
        description="Projeções demográficas por faixa etária e região",
        key_columns=["ANO", "SIGLA", "LOCAL"]
    ))