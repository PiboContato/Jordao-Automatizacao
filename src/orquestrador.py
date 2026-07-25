"""
orquestrador.py — Funções auxiliares para busca de arquivos e registro de auditoria no Supabase.

Nota: A execução em lote CLI/genérica foi desativada para garantir que
todo o processamento seja gerido exclusivamente pelo servidor web (app.py),
gerando registros de auditoria detalhados e individuais por relatório.
"""

import time
from pathlib import Path

from src.config import PASTA_DESTINO
from src.logger import logger
from src.supabase_client import get_supabase

# Lista de relatórios do sistema
REPORTS = [
    {"id": 1, "name": "01 Relatório de imoveis"},
    {"id": 2, "name": "02 Relatório de Contratos"},
    {"id": 3, "name": "03 Relatório de Fluxo de Caixa"},
    {"id": 4, "name": "04 Relatório Ficha do Contrato"},
    {"id": 5, "name": "05 Relatório por tipo de recebimento"},
    {"id": 6, "name": "06 Relatorio de Cobrança de Aluguel e IPTU"},
    {"id": 7, "name": "07 Relatorio de Cobranças Recebidas"},
    {"id": 8, "name": "08 Relatório de Contratos x Cobranças"},
    {"id": 9, "name": "09 Relatório de Comissão das Cobranças Recebidas"},
    {"id": 10, "name": "10 Relatório de Pagamentos aos Beneficiários"},
    {"id": 11, "name": "11 Relatório de Conferencia de Despesas"},
    {"id": 12, "name": "12 Relatório de Pessoas Ativos"},
    {"id": 13, "name": "13 Relatório de Recebimentos e Pagamentos"},
    {"id": 14, "name": "14 Relatório de Conferencia de movimentos detalhado"},
    {"id": 15, "name": "15 Relatório de Contas a Pagar / Receber"},
]

# Relatórios com limitações técnicas conhecidas
REPORTS_EXCLUIDOS = {3, 9, 10}


def _encontrar_excel_reports(report_id: int) -> list[Path]:
    """Encontra os arquivos .xlsx relevantes para um report_id na pasta destino.

    Para relatórios estáticos/snapshots (1, 2, 4, 5, 8, 12), retorna APENAS o arquivo mais recente
    para evitar re-execuções desnecessárias que limpam o banco repetidamente.
    Para relatórios por período (6, 11, 13, 14, 15), retorna apenas arquivos gerados recentemente (últimas 2 horas).
    """
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    padrao = f"{report_id:02d} *.xlsx"
    arquivos = sorted(
        PASTA_DESTINO.glob(padrao),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not arquivos:
        return []

    # Se for relatório snapshot, apenas o arquivo mais recente interessa
    if report_id in {1, 2, 4, 5, 8, 12}:
        return [arquivos[0]]

    # Para relatórios de período, pegar apenas arquivos recentes da execução atual (últimas 2 horas)
    agora = time.time()
    recentes = [p for p in arquivos if (agora - p.stat().st_mtime) < 7200]
    return recentes if recentes else [arquivos[0]]


def _registrar_execucao(tipo: str, status: str, **kwargs) -> None:
    """Registra uma execução na tabela execucoes do Supabase."""
    try:
        supabase = get_supabase()
        registro = {"tipo": tipo, "status": status}
        registro.update(kwargs)
        resultado = supabase.table("execucoes").insert(registro).execute()
        msg_preview = str(kwargs.get("mensagem", ""))[:60]
        logger.info(f"Execução registrada: tipo={tipo}, status={status}, msg={msg_preview}")
    except Exception as e:
        logger.error(f"Falha ao registrar execução no Supabase: {e}")
