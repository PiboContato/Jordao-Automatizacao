"""
utils.py — Utilitários gerais do agente Jordão.

Funções auxiliares reutilizáveis que não pertencem a nenhum módulo específico.
"""

import shutil
import time
from datetime import datetime
from pathlib import Path

from src.logger import logger
import os

def _get_pasta_destino() -> Path:
    from src.config import PASTA_DESTINO as CONFIG_PASTA
    env_pasta = os.environ.get("PASTA_DESTINO_DINAMICA")
    return Path(env_pasta) if env_pasta else CONFIG_PASTA


def gerar_nome_arquivo(report_id: int, report_name: str, data_inicio: str, data_fim: str, extension: str = ".csv") -> str:
    """
    Gera o nome padronizado do arquivo de relatório.
    Formato: "[ID] [Nome do Relatório] [Data_Inicio] a [Data_Fim].[ext]"
    """
    safe_name = report_name.replace('/', '').replace('\\', '').strip()
    d_i = data_inicio.replace('-', '_') if data_inicio else ""
    d_f = data_fim.replace('-', '_') if data_fim else ""
    
    if d_i and not d_f:
        return f"{safe_name} {d_i}{extension}"
    elif not d_i and not d_f:
        return f"{safe_name}{extension}"
    
    d_i_str = d_i if d_i else "sem_data_i"
    d_f_str = d_f if d_f else "sem_data_f"
    return f"{safe_name} {d_i_str} a {d_f_str}{extension}"


def garantir_pasta_destino() -> Path:
    pasta = _get_pasta_destino()
    pasta.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Pasta de destino verificada/criada: {pasta}")
    return pasta


def mover_arquivo_para_destino(arquivo_origem: Path, nome_destino: str) -> Path:
    """
    Move o arquivo baixado da pasta de downloads para a pasta de destino.

    Valida:
    - Arquivo existe na origem
    - Arquivo tem tamanho > 0 (não está corrompido/vazio)

    Args:
        arquivo_origem: Path do arquivo na pasta de downloads
        nome_destino: nome final do arquivo na pasta de destino

    Returns:
        Path do arquivo no destino

    Raises:
        FileNotFoundError: se origem não existir
        ValueError: se arquivo estiver vazio
    """
    if not arquivo_origem.exists():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {arquivo_origem}")

    if arquivo_origem.stat().st_size == 0:
        raise ValueError(f"Arquivo de origem está vazio (0 bytes): {arquivo_origem}")

    pasta = _get_pasta_destino()
    destino = pasta / nome_destino

    shutil.move(str(arquivo_origem), str(destino))
    logger.info(f"Arquivo movido: {arquivo_origem} -> {destino}")

    return destino


def validar_arquivo_excel(caminho: Path) -> bool:
    """
    Validação mínima de que o arquivo parece um Excel válido.

    Verifica:
    - Existe no disco
    - Tamanho > 0
    - Começa com assinatura de ZIP (PK) — XLSX é um ZIP internamente

    Por que isso: um botão de exportação que falhou silenciosamente
    pode gerar um HTML de erro disfarçado de .xlsx. Isso detecta esse caso.
    """
    try:
        if not caminho.exists():
            logger.error(f"Arquivo não existe: {caminho}")
            return False

        if caminho.stat().st_size == 0:
            logger.error(f"Arquivo vazio (0 bytes): {caminho}")
            return False

        # Assinatura ZIP: primeiros 2 bytes = b'PK' (para XLSX)
        with open(caminho, "rb") as f:
            assinatura = f.read(2)

        if caminho.suffix.lower() == ".csv":
            # Para CSV, apenas garantimos que tem algum conteúdo legível (não binário)
            try:
                with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                    conteudo = f.read(1024)
                if not conteudo:
                    logger.error(f"Arquivo CSV parece estar vazio ou ilegível: {caminho}")
                    return False
            except Exception as e:
                logger.error(f"Erro ao ler CSV {caminho}: {e}")
                return False
        elif caminho.suffix.lower() == ".pdf":
            # Para PDF, checa se a assinatura é %PDF (em bytes = b'%P')
            if assinatura != b"%P":
                logger.error(f"Arquivo não parece ser um PDF válido (assinatura incorreta): {caminho}")
                return False
        elif assinatura != b"PK":
            logger.error(
                f"Arquivo não parece ser um XLSX válido (assinatura incorreta): {caminho}"
            )
            return False

        logger.info(f"Arquivo validado com sucesso: {caminho} ({caminho.stat().st_size} bytes)")
        return True

    except Exception as e:
        logger.error(f"Erro ao validar arquivo {caminho}: {e}")
        return False


def limpar_arquivos_antigos(diretorio: Path, dias: int) -> None:
    """
    Remove arquivos do diretório cuja data de modificação seja mais antiga que 'dias'.
    """
    logger.info(f"Iniciando limpeza de arquivos locais mais antigos que {dias} dias em: {diretorio}")
    limite = time.time() - (dias * 24 * 3600)
    count = 0
    try:
        if not diretorio.exists():
            return
        for item in diretorio.iterdir():
            if item.is_file() and item.stat().st_mtime < limite:
                try:
                    item.unlink()
                    count += 1
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo antigo {item.name}: {e}")
        logger.info(f"Limpeza concluída. {count} arquivos removidos.")
    except Exception as e:
        logger.error(f"Erro durante a limpeza de arquivos antigos: {e}")

def calcular_datas_padrao() -> list:
    import datetime
    today = datetime.date.today()
    
    # primeiro dia do mes atual
    first_day_curr = today.replace(day=1)
    first_day_curr_str = first_day_curr.strftime("%Y-%m-%d")
    
    # ultimo dia do mes atual
    next_month = today.replace(day=28) + datetime.timedelta(days=4)
    last_day_curr = next_month - datetime.timedelta(days=next_month.day)
    last_day_curr_str = last_day_curr.strftime("%Y-%m-%d")
    
    # mes anterior YYYY-MM
    first_day_prev = (first_day_curr - datetime.timedelta(days=1)).replace(day=1)
    prev_month_str = first_day_prev.strftime("%Y-%m")
    
    relatorios = []
    # Usar um placeholder para REPORTS para não importar circularmente
    for rid in range(1, 16):
        # Excluir relatórios 3, 9 e 10 (desativados)
        if rid in [3, 9, 10]:
            continue
            
        dt_ini = ""
        dt_fim = ""
        
        # Grupo A: Snapshot / Estáticos
        if rid in [1, 2, 4, 5, 8, 12]:
            dt_ini = first_day_curr_str
            dt_fim = ""
        # Grupo B: Mês Atual
        elif rid in [13, 15]:
            dt_ini = first_day_curr_str
            dt_fim = last_day_curr_str
        # Grupo C e D: Mês Anterior + Atual
        elif rid in [6, 7, 11, 14]:
            dt_ini = prev_month_str + "-01"
            dt_fim = last_day_curr_str
            
        relatorios.append({
            "id": rid,
            "data_inicio": dt_ini,
            "data_fim": dt_fim
        })
    return relatorios

