"""
config.py — Configurações centralizadas do agente Jordão
Todas as variáveis de ambiente são lidas aqui. NUNCA espalhar
leitura de .env em outros módulos — ponto único de configuração.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto (um nível acima da pasta src)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")


def _get_required(key: str) -> str:
    """Lê variável obrigatória; falha cedo se estiver ausente."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Variável de ambiente obrigatória ausente ou vazia: '{key}'. "
            f"Verifique o arquivo .env (copie de .env.example se necessário)."
        )
    return value


# --- Sistema Jordão ---
ASTRAL_URL: str = _get_required("ASTRAL_URL")
ASTRAL_USUARIO: str = _get_required("ASTRAL_USUARIO")
ASTRAL_SENHA: str = _get_required("ASTRAL_SENHA")

# --- Painel Web (Dashboard) ---
DASHBOARD_USER: str = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS: str = os.getenv("DASHBOARD_PASS", "admin")

# --- Pastas ---
PASTA_DESTINO: Path = Path(_get_required("PASTA_DESTINO"))
PASTA_DOWNLOADS_SO: Path = Path.home() / "Downloads"  # fallback padrão Windows

# --- E-mail ---
EMAIL_REMETENTE: str = _get_required("EMAIL_REMETENTE")
EMAIL_SENHA: str = _get_required("EMAIL_SENHA")
EMAIL_DESTINATARIO: list[str] = [
    e.strip() for e in _get_required("EMAIL_DESTINATARIO").split(",") if e.strip()
]
SMTP_SERVIDOR: str = os.getenv("SMTP_SERVIDOR", "smtp-mail.outlook.com")
SMTP_PORTA: int = int(os.getenv("SMTP_PORTA", "587"))

# --- Comportamento do agente ---
HEADLESS: bool = os.getenv("HEADLESS", "false").lower() == "true"

# --- Timeouts (ms) ---
TIMEOUT_NAVEGACAO: int = int(os.getenv("TIMEOUT_NAVEGACAO", "30000"))
TIMEOUT_DOWNLOAD: int = int(os.getenv("TIMEOUT_DOWNLOAD", "60000"))

# --- Retry ---
TENTATIVAS_MAX: int = int(os.getenv("TENTATIVAS_MAX", "3"))
ESPERA_ENTRE_TENTATIVAS: int = int(os.getenv("ESPERA_ENTRE_TENTATIVAS", "10"))
