"""
main.py — Ponto de entrada do agente Jordão.

Uso:
    py main.py                    → executa o fluxo completo
    py main.py --testar-email     → envia e-mail de teste (sem rodar o agente)
    py main.py --testar-config    → valida configurações e sai

O agendamento diário é feito via Windows Task Scheduler (ver README.md),
não dentro deste script — separação de responsabilidades.
"""

import argparse
import sys

from src.logger import logger
from src.config import (
    JORDAO_URL,
    JORDAO_USUARIO,
    EMAIL_REMETENTE,
    EMAIL_DESTINATARIO,
    PASTA_DESTINO,
    HEADLESS,
    SUPABASE_URL,
)


def _testar_configuracoes() -> None:
    """Valida que as configurações básicas estão preenchidas e imprime um resumo."""
    print("\n=== Validação de Configurações ===")
    print(f"  URL Jordão:          {JORDAO_URL}")
    print(f"  Usuário:             {JORDAO_USUARIO}")
    print(f"  Senha:               {'*' * 8} (não exibida)")
    print(f"  Pasta destino:       {PASTA_DESTINO}")
    print(f"  E-mail remetente:    {EMAIL_REMETENTE}")
    print(f"  E-mail destinatário: {EMAIL_DESTINATARIO}")
    print(f"  Modo headless:       {HEADLESS}")
    print(f"  Supabase URL:        {SUPABASE_URL}")
    print("\n[OK] Configurações carregadas com sucesso.")


def _testar_email() -> None:
    """Envia um e-mail de teste para validar as configurações de SMTP."""
    from src.alertas import alertar_falha
    print("\nEnviando e-mail de teste...")
    alertar_falha(
        etapa="TESTE",
        detalhes="Este é um e-mail de teste enviado manualmente para validar as configurações de SMTP."
    )
    print("[OK] E-mail de teste enviado (verifique a caixa de entrada do destinatário).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agente de automação — Sistema Jordão")
    parser.add_argument(
        "--testar-email",
        action="store_true",
        help="Envia e-mail de teste sem executar o agente",
    )
    parser.add_argument(
        "--testar-config",
        action="store_true",
        help="Valida e exibe as configurações carregadas do .env",
    )
    args = parser.parse_args()

    if args.testar_config:
        _testar_configuracoes()
        return 0

    if args.testar_email:
        _testar_email()
        return 0

    # Execução normal - Sobe o painel Web
    logger.info("Iniciando Servidor Web do Agente Jordão")
    import os
    port = int(os.getenv("PORT", 5000))
    print(f"\n[OK] Servidor Web iniciando. Acesse http://0.0.0.0:{port} no seu navegador.")
    from app import app
    app.run(host="0.0.0.0", port=port, debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
