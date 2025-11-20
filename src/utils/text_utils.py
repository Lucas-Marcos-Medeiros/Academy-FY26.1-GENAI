"""
Utilitários para processamento e limpeza de texto
"""
import re
from typing import Optional


def clean_llm_response(text: str) -> str:
    """
    Limpa formatação problemática de respostas da LLM
    
    Remove:
    - Markdown (**, __, *)
    - LaTeX
    - Símbolos matemáticos problemáticos
    - Caracteres especiais que quebram a renderização
    
    Args:
        text: Texto da resposta da LLM
        
    Returns:
        Texto limpo e legível
    """
    if not text:
        return ""
    
    # Remove asteriscos de markdown
    text = text.replace("**", "")
    text = text.replace("__", "")
    
    # Remove asteriscos isolados (mas mantém * em contextos válidos como listas)
    # Só remove se estiver cercado de letras
    text = re.sub(r'(\w)\*(\w)', r'\1\2', text)
    
    # Remove comandos LaTeX (\command)
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    
    # Remove símbolos matemáticos problemáticos
    text = text.replace('~', '')
    text = text.replace('^', '')
    text = text.replace('∗', '')
    text = text.replace('ˊ', '')
    text = text.replace('~', '')
    
    # Corrige espaçamento ao redor de R$
    text = re.sub(r'R\s*\$\s*(\d)', r'R$ \1', text)
    text = re.sub(r'\$\s*R', r'R$', text)
    
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    
    # Remove espaços antes de pontuação
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    
    # Garante espaço depois de pontuação
    text = re.sub(r'([,.;:!?])([A-Za-z])', r'\1 \2', text)
    
    return text.strip()


def format_currency(value: float) -> str:
    """
    Formata valor como moeda brasileira
    
    Args:
        value: Valor numérico
        
    Returns:
        String formatada (ex: "R$ 1.234,56")
    """
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Formata valor como porcentagem
    
    Args:
        value: Valor numérico (ex: 0.15 ou 15)
        decimals: Número de casas decimais
        
    Returns:
        String formatada (ex: "15,50%")
    """
    # Detecta se já está em porcentagem (> 1)
    if abs(value) > 1:
        pct = value
    else:
        pct = value * 100
    
    formatted = f"{pct:.{decimals}f}".replace(".", ",")
    return f"{formatted}%"


def extract_numbers_from_text(text: str) -> list:
    """
    Extrai todos os números de um texto
    
    Args:
        text: Texto contendo números
        
    Returns:
        Lista de números encontrados (como float)
    """
    # Padrão para números com pontos/vírgulas
    pattern = r'\d+(?:[.,]\d+)*'
    matches = re.findall(pattern, text)
    
    numbers = []
    for match in matches:
        try:
            # Normaliza para formato Python
            normalized = match.replace(".", "").replace(",", ".")
            numbers.append(float(normalized))
        except ValueError:
            continue
    
    return numbers


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Trunca texto mantendo palavras inteiras
    
    Args:
        text: Texto para truncar
        max_length: Comprimento máximo
        suffix: Sufixo para indicar truncamento
        
    Returns:
        Texto truncado
    """
    if len(text) <= max_length:
        return text
    
    # Encontra o último espaço antes do limite
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return truncated + suffix


def highlight_keywords(text: str, keywords: list, wrapper: str = "**{}**") -> str:
    """
    Destaca palavras-chave no texto
    
    Args:
        text: Texto original
        keywords: Lista de palavras para destacar
        wrapper: Formato para destacar (padrão: Markdown bold)
        
    Returns:
        Texto com palavras destacadas
    """
    result = text
    for keyword in keywords:
        # Case insensitive replacement
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        result = pattern.sub(wrapper.format(keyword), result)
    
    return result


def create_summary(text: str, num_sentences: int = 3) -> str:
    """
    Cria resumo mantendo as primeiras N sentenças
    
    Args:
        text: Texto completo
        num_sentences: Número de sentenças para manter
        
    Returns:
        Resumo do texto
    """
    # Divide em sentenças (simplificado)
    sentences = re.split(r'[.!?]+\s+', text)
    
    # Remove sentenças vazias
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Retorna primeiras N sentenças
    summary_sentences = sentences[:num_sentences]
    
    return '. '.join(summary_sentences) + '.'


def normalize_whitespace(text: str) -> str:
    """
    Normaliza espaços em branco no texto
    
    Args:
        text: Texto com espaçamento irregular
        
    Returns:
        Texto com espaçamento normalizado
    """
    # Remove espaços no início e fim
    text = text.strip()
    
    # Substitui múltiplos espaços por um único
    text = re.sub(r'\s+', ' ', text)
    
    # Substitui múltiplas quebras de linha por duas (parágrafo)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    return text


def sanitize_filename(filename: str) -> str:
    """
    Remove caracteres inválidos de nomes de arquivo
    
    Args:
        filename: Nome de arquivo proposto
        
    Returns:
        Nome de arquivo seguro
    """
    # Remove caracteres não permitidos
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Substitui espaços por underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Remove múltiplos underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized.strip('_')


def format_phone_number(phone: str) -> str:
    """
    Formata número de telefone brasileiro
    
    Args:
        phone: Número sem formatação (ex: "11999887766")
        
    Returns:
        Número formatado (ex: "(11) 99988-7766")
    """
    # Remove tudo exceto números
    digits = re.sub(r'\D', '', phone)
    
    # Formata conforme quantidade de dígitos
    if len(digits) == 11:  # Celular com DDD
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:  # Fixo com DDD
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    elif len(digits) == 9:  # Celular sem DDD
        return f"{digits[:5]}-{digits[5:]}"
    elif len(digits) == 8:  # Fixo sem DDD
        return f"{digits[:4]}-{digits[4:]}"
    else:
        return phone  # Retorna original se não conseguir formatar


def create_prompt_with_formatting_rules() -> str:
    """
    Retorna instruções padrão de formatação para incluir em prompts
    
    Returns:
        String com instruções
    """
    return """
REGRAS DE FORMATAÇÃO:
- Escreva em português claro e correto
- NÃO use asteriscos (**), underscores (_) ou símbolos matemáticos
- Use apenas texto puro
- Escreva valores monetários como: R$ 1.234,56
- Use quebras de linha para organizar
- Mantenha respostas objetivas e diretas
"""


# Aliases para compatibilidade
clean_text = clean_llm_response
format_money = format_currency