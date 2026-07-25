"""
alertas.py — Envio de alertas por e-mail (Outlook/Hotmail via SMTP).

Responsabilidade única: notificar sobre falhas e sucessos da execução.
Nunca loga senhas ou dados sensíveis.
"""

import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from src.config import (
    EMAIL_REMETENTE,
    EMAIL_SENHA,
    EMAIL_DESTINATARIO,
    SMTP_SERVIDOR,
    SMTP_PORTA,
)
from src.logger import logger


def _enviar_email(assunto: str, corpo: str) -> bool:
    """
    Envia um e-mail via SMTP (TLS).
    Retorna True se enviado com sucesso, False caso contrário.

    Por que não lança exceção: o alerta de falha não deve causar
    uma segunda falha não tratada no fluxo principal.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = ", ".join(EMAIL_DESTINATARIO)

        corpo_html = f"""
        <html><body>
        <pre style="font-family:monospace;font-size:13px;">{corpo}</pre>
        <hr>
        <small>Mensagem automática — Agente Jordão | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</small>
        </body></html>
        """

        msg.attach(MIMEText(corpo, "plain", "utf-8"))
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PORTA, timeout=30) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(EMAIL_REMETENTE, EMAIL_SENHA)
            servidor.sendmail(EMAIL_REMETENTE, EMAIL_DESTINATARIO, msg.as_string())

        logger.info(f"E-mail enviado com sucesso para: {EMAIL_DESTINATARIO}")
        return True

    except Exception:
        # Registra o erro de envio sem relançar — falha de alerta não deve
        # mascarar a falha original que motivou o alerta
        logger.error("Falha ao enviar e-mail de alerta:\n" + traceback.format_exc())
        return False


def alertar_falha(etapa: str, detalhes: str) -> None:
    """
    Envia alerta de falha com contexto da etapa onde ocorreu.

    Args:
        etapa: Nome da etapa onde falhou (ex: 'login', 'exportacao')
        detalhes: Mensagem de erro detalhada (sem dados sensíveis)
    """
    assunto = f"[FALHA] Agente Jordão — Erro na etapa: {etapa} ({datetime.now().strftime('%d/%m/%Y')})"
    corpo = (
        f"O agente de automação Jordão encontrou um erro e não completou a execução.\n\n"
        f"Etapa com falha: {etapa}\n"
        f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"Detalhes:\n{detalhes}\n\n"
        f"Ação necessária: verificar logs em logs/jordao_agente.log para diagnóstico completo."
    )
    logger.warning(f"Disparando alerta de falha — etapa: {etapa}")
    _enviar_email(assunto, corpo)


def alertar_sucesso(arquivo_salvo: str) -> None:
    """
    Envia confirmação de execução bem-sucedida.
    Opcional — pode ser desabilitado para reduzir ruído de e-mails.

    Args:
        arquivo_salvo: Nome do arquivo salvo com sucesso
    """
    assunto = f"[OK] Agente Jordão — Relatório extraído ({datetime.now().strftime('%d/%m/%Y')})"
    corpo = (
        f"Execução concluída com sucesso.\n\n"
        f"Arquivo salvo: {arquivo_salvo}\n"
        f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    _enviar_email(assunto, corpo)
