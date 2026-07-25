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
JORDAO_URL: str = _get_required("JORDAO_URL")
JORDAO_USUARIO: str = _get_required("JORDAO_USUARIO")
JORDAO_SENHA: str = _get_required("JORDAO_SENHA")

# --- URL base para navegação nos relatórios (sem /login) ---
JORDAO_BASE_URL: str = os.getenv("JORDAO_BASE_URL", "https://admin.jordaogestaodeimoveis.com.br")


def montar_url(recurso: str) -> str:
    """Concatena a base URL com o caminho do recurso."""
    base = JORDAO_BASE_URL.rstrip("/")
    path = recurso.lstrip("/")
    return f"{base}/{path}"


# --- Painel Web (Dashboard) ---
DASHBOARD_USER: str = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS: str = os.getenv("DASHBOARD_PASS", "admin")

# --- Chave secreta do Flask ---
SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-dev-only")

# --- Pastas ---
_pasta_env = os.getenv("PASTA_DESTINO")
PASTA_DESTINO: Path = Path(_pasta_env) if _pasta_env else (Path(__file__).parent.parent / "Relatorios")
PASTA_DOWNLOADS_SO: Path = Path.home() / "Downloads"

# --- Supabase ---
SUPABASE_URL: str = _get_required("SUPABASE_URL")
SUPABASE_KEY: str = _get_required("SUPABASE_KEY")

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
TIMEOUT_NAVEGACAO: int = int(os.getenv("TIMEOUT_NAVEGACAO", "60000"))
TIMEOUT_DOWNLOAD: int = int(os.getenv("TIMEOUT_DOWNLOAD", "120000"))

# --- Retry ---
TENTATIVAS_MAX: int = int(os.getenv("TENTATIVAS_MAX", "3"))
ESPERA_ENTRE_TENTATIVAS: int = int(os.getenv("ESPERA_ENTRE_TENTATIVAS", "10"))

# --- Limpeza de arquivos ---
DIAS_RETENCAO_LOCAL: int = int(os.getenv("DIAS_RETENCAO_LOCAL", "7"))
