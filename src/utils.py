"""
utils.py — Utilitários gerais do agente Astral.

Funções auxiliares reutilizáveis que não pertencem a nenhum módulo específico.
"""

import shutil
import time
from datetime import datetime
from pathlib import Path

from src.config import PASTA_DESTINO, PASTA_DOWNLOADS_SO
from src.logger import logger


def gerar_nome_arquivo(report_id: int, report_name: str, data_inicio: str, data_fim: str, extension: str = ".csv") -> str:
    """
    Gera o nome padronizado do arquivo de relatório.
    Formato: "[ID] [Nome do Relatório] [Data_Inicio] a [Data_Fim].[ext]"
    """
    d_i = data_inicio.replace('-', '_') if data_inicio else "sem_data_i"
    d_f = data_fim.replace('-', '_') if data_fim else "sem_data_f"
    
    # Remove special characters from report_name just to be safe
    safe_name = report_name.replace('/', '').replace('\\', '').strip()
    return f"{safe_name} {d_i} a {d_f}{extension}"


def garantir_pasta_destino() -> Path:
    """
    Cria a pasta de destino se não existir.
    Retorna o Path da pasta.
    """
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Pasta de destino verificada/criada: {PASTA_DESTINO}")
    return PASTA_DESTINO


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

    garantir_pasta_destino()
    destino = PASTA_DESTINO / nome_destino

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
