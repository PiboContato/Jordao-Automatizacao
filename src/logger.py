"""
logger.py — Configuração centralizada de logging estruturado.

Saída tripla: console (para desenvolvimento) + arquivo rotativo (para produção) + Supabase (para dashboard remoto).
Formatação inclui timestamp, nível, módulo/função e mensagem.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Lista global para armazenar os logs recentes na memória (para a UI web)
recent_logs: list[str] = []

class MemoryHandler(logging.Handler):
    """Handler customizado que guarda as últimas MAX_LINES na memória"""
    def __init__(self, max_lines: int = 50):
        super().__init__()
        self.max_lines = max_lines

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            recent_logs.append(msg)
            if len(recent_logs) > self.max_lines:
                recent_logs.pop(0)
        except Exception:
            self.handleError(record)


class SupabaseHandler(logging.Handler):
    """Handler que grava logs no Supabase (tabela 'logs') para o dashboard remoto."""
    def __init__(self, level: int = logging.INFO):
        super().__init__(level)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from src.supabase_client import get_supabase
                self._client = get_supabase()
            except Exception:
                pass
        return self._client

    def emit(self, record: logging.LogRecord) -> None:
        try:
            client = self._get_client()
            if client is None:
                return
            nivel = record.levelname
            modulo = record.module
            mensagem = self.format(record)
            client.table("logs").insert({
                "nivel": nivel,
                "modulo": modulo,
                "mensagem": mensagem,
            }).execute()
        except Exception:
            self.handleError(record)


def obter_logs_recentes() -> list[str]:
    return recent_logs

def limpar_logs_recentes() -> None:
    recent_logs.clear()


def configurar_logger(nome: str = "jordao_agente") -> logging.Logger:
    """
    Cria e retorna um logger configurado com:
    - Handler de console (stdout)
    - Handler de arquivo rotativo (logs/jordao_agente.log, max 5MB, 3 backups)
    - Handler de memoria (para UI local)
    - Handler de Supabase (para dashboard remoto no Render)
    """
    pasta_logs = Path(__file__).parent.parent / "logs"
    pasta_logs.mkdir(exist_ok=True)

    logger = logging.getLogger(nome)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formato)

    arquivo_handler = RotatingFileHandler(
        filename=pasta_logs / "jordao_agente.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    arquivo_handler.setLevel(logging.DEBUG)
    arquivo_handler.setFormatter(formato)

    memoria_handler = MemoryHandler(max_lines=50)
    memoria_handler.setLevel(logging.INFO)
    memoria_handler.setFormatter(formato)

    supabase_handler = SupabaseHandler(level=logging.INFO)
    supabase_handler.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(console_handler)
    logger.addHandler(arquivo_handler)
    logger.addHandler(memoria_handler)
    logger.addHandler(supabase_handler)

    return logger


logger = configurar_logger()
