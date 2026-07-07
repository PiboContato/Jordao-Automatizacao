"""
logger.py — Configuração centralizada de logging estruturado.

Saída dupla: console (para desenvolvimento) + arquivo rotativo (para produção).
Formato inclui timestamp, nível, módulo/função e mensagem.
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

def obter_logs_recentes() -> list[str]:
    return recent_logs

def limpar_logs_recentes() -> None:
    recent_logs.clear()


def configurar_logger(nome: str = "astral_agente") -> logging.Logger:
    """
    Cria e retorna um logger configurado com:
    - Handler de console (stdout)
    - Handler de arquivo rotativo (logs/astral_agente.log, máx 5MB, 3 backups)

    Por que rotativo: evita que logs acumulem indefinidamente em produção.
    """
    pasta_logs = Path(__file__).parent.parent / "logs"
    pasta_logs.mkdir(exist_ok=True)

    logger = logging.getLogger(nome)
    logger.setLevel(logging.DEBUG)

    # Evitar handlers duplicados se o módulo for importado múltiplas vezes
    if logger.handlers:
        return logger

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Handler: Console ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formato)

    # --- Handler: Arquivo rotativo ---
    arquivo_handler = RotatingFileHandler(
        filename=pasta_logs / "astral_agente.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    arquivo_handler.setLevel(logging.DEBUG)
    arquivo_handler.setFormatter(formato)

    # --- Handler: Memória (Para UI) ---
    memoria_handler = MemoryHandler(max_lines=50)
    memoria_handler.setLevel(logging.INFO)
    memoria_handler.setFormatter(formato)

    logger.addHandler(console_handler)
    logger.addHandler(arquivo_handler)
    logger.addHandler(memoria_handler)

    return logger


# Logger padrão do projeto — importar diretamente nos outros módulos
logger = configurar_logger()
