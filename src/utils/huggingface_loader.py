"""
Módulo para carregar datasets do HuggingFace
VERSÃO CORRIGIDA - Com tratamento para notação científica em acidentes_2019
"""
import pandas as pd
import streamlit as st
from typing import Optional, Dict
import io


class HuggingFaceLoader:
    """Carrega datasets do HuggingFace Hub"""
    
    def __init__(self):
        self.dataset_repo = self._get_dataset_repo()
        self.file_configs = self._get_file_configs()
        
    def _get_dataset_repo(self) -> str:
        """Obtém o nome do repositório do dataset"""
        # Tenta primeiro dos secrets do Streamlit
        if hasattr(st, 'secrets') and 'huggingface' in st.secrets:
            return st.secrets['huggingface'].get('dataset_repo', '')
        
        # Fallback: variável de ambiente
        import os
        repo = os.getenv('HF_DATASET_REPO', '')
        
        # Fallback final: dataset padrão
        if not repo:
            repo = 'Pichau2907/casco_dataset'
        
        return repo
    
    def _get_file_configs(self) -> Dict:
        """Configuração dos arquivos no dataset"""
        return {
            'casco_sem1': {
                'filename': 'casco_tratadoA.csv',
                'separator': ',',
                'encoding': 'utf-8',
                'description': '1º Semestre 2019'
            },
            'casco_sem2': {
                'filename': 'casco_tratadoB.csv',
                'separator': ',',
                'encoding': 'utf-8',
                'description': '2º Semestre 2019'
            },
            'acidentes_2019': {
                'filename': 'acidentes2019_todas_causas_tipos.csv',
                'separator': ';',
                'encoding': 'latin1',
                'description': 'Acidentes 2019',
                'has_scientific_notation': True  # ← NOVA FLAG
            },
            'seguranca_publica': {
                'filename': 'indicadoressegurancapublicauf.csv',
                'separator': ',',
                'encoding': 'utf-8',
                'description': 'Segurança Pública',
                'has_header': False,
                'column_names': ['estado', 'tipo_crime', 'ano', 'mes', 'quantidade']
            },
            'projecoes_populacao': {
                'filename': 'projecoes_grupos_etarios_quantidades.csv',
                'separator': ',',
                'encoding': 'utf-8',
                'description': 'Projeções Populacionais'
            }
        }
    
    @st.cache_data(ttl=3600, show_spinner="Carregando dados do HuggingFace...")
    def load_csv(_self, table_name: str) -> Optional[pd.DataFrame]:
        """
        Carrega CSV do HuggingFace com correção de formatação
        
        Args:
            table_name: Nome da tabela (casco_sem1, acidentes_2019, etc)
            
        Returns:
            DataFrame ou None se falhar
        """
        if table_name not in _self.file_configs:
            st.error(f"Tabela não configurada: {table_name}")
            return None
        
        config = _self.file_configs[table_name]
        filename = config['filename']
        
        if not _self.dataset_repo:
            st.error("Dataset HuggingFace não configurado. Configure HF_DATASET_REPO.")
            return None
        
        try:
            # Importa datasets (lazy import)
            from datasets import load_dataset
            
            # ============================================================
            # TRATAMENTO ESPECIAL PARA ACIDENTES_2019
            # ============================================================
            if config.get('has_scientific_notation', False):
                print(f"⚠️ {filename} tem notação científica - usando modo especial")
                
                # Carrega como texto puro primeiro
                dataset = load_dataset(
                    _self.dataset_repo,
                    data_files=filename,
                    split='train',
                    features=None  # Não força tipos
                )
                
                # Converte para pandas
                df = dataset.to_pandas()
                
                # Corrige a formatação de uma única coluna se necessário
                if len(df.columns) == 1:
                    print(f"   Detectado problema de formatação - corrigindo...")
                    single_column_data = df.iloc[:, 0].astype(str)
                    
                    # Re-parse com separador correto
                    df = pd.read_csv(
                        io.StringIO('\n'.join(single_column_data)),
                        sep=config['separator'],
                        encoding=config.get('encoding', 'utf-8'),
                        low_memory=False
                    )
                
                # CORREÇÃO PRINCIPAL: Converte colunas com notação científica
                print(f"   Corrigindo notação científica nas colunas...")
                for col in df.columns:
                    if df[col].dtype == 'object':
                        try:
                            # Tenta detectar se tem notação científica (Ex: 2,00E+05)
                            sample = str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else ""
                            
                            if 'E+' in sample.upper() or 'E-' in sample.upper():
                                print(f"      • {col}: convertendo notação científica")
                                # Substitui vírgula por ponto e converte
                                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                                df[col] = pd.to_numeric(df[col], errors='coerce')
                        except Exception as e:
                            print(f"      • {col}: mantido como está ({e})")
                            pass
                
            else:
                # ============================================================
                # CARREGAMENTO NORMAL (outras tabelas)
                # ============================================================
                dataset = load_dataset(
                    _self.dataset_repo,
                    data_files=filename,
                    split='train'
                )
                
                # Converte para pandas
                df = dataset.to_pandas()
                
                # CORREÇÃO DE FORMATAÇÃO: Detecta se dados estão em uma única coluna
                if len(df.columns) == 1:
                    print(f"⚠️ Detectado problema de formatação em {filename}")
                    print(f"   Tentando corrigir com separador: {config['separator']}")
                    
                    # Pega os dados da única coluna
                    single_column_data = df.iloc[:, 0].astype(str)
                    
                    # Re-parse com separador correto
                    df = pd.read_csv(
                        io.StringIO('\n'.join(single_column_data)),
                        sep=config['separator'],
                        encoding=config.get('encoding', 'utf-8'),
                        low_memory=False
                    )
            
            # Se ainda tem problema, tenta detectar separador automaticamente
            if len(df.columns) == 1:
                print(f"   Tentando detectar separador automaticamente...")
                
                # Testa separadores comuns
                for sep in [';', ',', '\t', '|']:
                    try:
                        single_column_data = df.iloc[:, 0].astype(str)
                        df_test = pd.read_csv(
                            io.StringIO('\n'.join(single_column_data)),
                            sep=sep,
                            encoding=config.get('encoding', 'utf-8'),
                            low_memory=False,
                            nrows=5  # Testa apenas primeiras linhas
                        )
                        
                        if len(df_test.columns) > 1:
                            print(f"   ✅ Separador detectado: '{sep}'")
                            # Recarrega com separador correto
                            single_column_data = df.iloc[:, 0].astype(str)
                            df = pd.read_csv(
                                io.StringIO('\n'.join(single_column_data)),
                                sep=sep,
                                encoding=config.get('encoding', 'utf-8'),
                                low_memory=False
                            )
                            break
                    except:
                        continue
            
            # Configurações específicas por tabela
            if table_name == 'seguranca_publica' and config.get('has_header') == False:
                # Remove header se existir e adiciona nomes corretos
                if df.columns[0] in ['estado', 'Alagoas']:  # Primeira linha como header
                    df.columns = config['column_names']
                else:
                    # Adiciona header correto
                    df.columns = config['column_names']
            
            # Limpeza geral
            df = _self._clean_dataframe(df, table_name)
            
            print(f"✅ {filename}: {len(df)} registros, {len(df.columns)} colunas")
            
            return df
            
        except ImportError:
            st.error("Biblioteca 'datasets' não instalada. Execute: pip install datasets")
            return None
        except Exception as e:
            st.error(f"Erro ao carregar {filename}: {str(e)}")
            print(f"❌ Erro detalhado: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _clean_dataframe(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Limpa e formata o DataFrame"""
        
        # Remove colunas completamente vazias
        df = df.dropna(axis=1, how='all')
        
        # Remove linhas completamente vazias
        df = df.dropna(axis=0, how='all')
        
        # Limpa nomes de colunas (remove espaços, caracteres especiais)
        df.columns = df.columns.str.strip()
        
        # Correções específicas por tabela
        if table_name == 'acidentes_2019':
            # Garante que não há colunas duplicadas
            if df.columns.duplicated().any():
                df = df.loc[:, ~df.columns.duplicated()]
        
        return df
    
    def load_all_tables(self) -> Dict[str, pd.DataFrame]:
        """Carrega todas as tabelas configuradas"""
        tables = {}
        
        total = len(self.file_configs)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, (table_name, config) in enumerate(self.file_configs.items()):
            status_text.text(f"Carregando {config['description']}... ({i+1}/{total})")
            
            df = self.load_csv(table_name)
            
            if df is not None:
                tables[table_name] = df
                print(f"✅ {table_name}: {len(df):,} registros")
            else:
                print(f"⚠️ {table_name}: Falha ao carregar")
            
            progress_bar.progress((i + 1) / total)
        
        status_text.text("✅ Carregamento concluído!")
        progress_bar.empty()
        status_text.empty()
        
        return tables
    
    def get_info(self) -> Dict:
        """Retorna informações sobre o dataset"""
        return {
            'dataset_repo': self.dataset_repo,
            'configured': bool(self.dataset_repo),
            'files': {
                name: config['description'] 
                for name, config in self.file_configs.items()
            }
        }


# Instância global
_hf_loader = None


def get_huggingface_loader() -> HuggingFaceLoader:
    """Retorna instância global do loader"""
    global _hf_loader
    if _hf_loader is None:
        _hf_loader = HuggingFaceLoader()
    return _hf_loader


def check_huggingface_config() -> bool:
    """Verifica se HuggingFace está configurado"""
    loader = get_huggingface_loader()
    info = loader.get_info()
    
    if not info['configured']:
        st.warning("⚠️ HuggingFace não está configurado")
        with st.expander("Como configurar"):
            st.markdown("""
            **1. Configure o repositório do dataset:**
            
            Em `.streamlit/secrets.toml`:
            ```toml
            [huggingface]
            dataset_repo = "Pichau2907/casco_dataset"
            ```
            
            Ou como variável de ambiente:
            ```bash
            export HF_DATASET_REPO="Pichau2907/casco_dataset"
            ```
            
            **2. Instale a biblioteca:**
            ```bash
            pip install datasets
            ```
            """)
        return False
    
    st.success(f"✅ Dataset: {info['dataset_repo']}")
    return True


# Script de teste
if __name__ == "__main__":
    print("="*60)
    print("🧪 TESTE DO HUGGINGFACE LOADER")
    print("="*60)
    
    loader = get_huggingface_loader()
    info = loader.get_info()
    
    print(f"\nDataset: {info['dataset_repo']}")
    print(f"Configurado: {info['configured']}")
    
    print("\n📋 Tabelas disponíveis:")
    for name, desc in info['files'].items():
        print(f"  • {name}: {desc}")
    
    # Testa carregamento de uma tabela problemática
    print("\n" + "="*60)
    print("🧪 TESTANDO ACIDENTES_2019 (com notação científica)")
    print("="*60)
    
    try:
        df = loader.load_csv('acidentes_2019')
        if df is not None:
            print(f"\n✅ Carregado com sucesso!")
            print(f"   Registros: {len(df)}")
            print(f"   Colunas: {df.columns.tolist()[:10]}...")
            print(f"\n📊 Primeiras linhas:")
            print(df.head())
            print(f"\n📊 Tipos de dados:")
            print(df.dtypes)
        else:
            print("\n❌ Falha ao carregar")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()