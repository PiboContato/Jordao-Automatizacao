"""
orquestrador.py — Coordena extração + ingestão Supabase.

Fluxo:
1. Extrai todos os 15 relatórios via Playwright (processar_fila_em_massa)
2. Para cada relatório com sucesso, encontra o Excel na pasta destino
3. Roda o ingestor correspondente para enviar ao Supabase
4. Registra resultado na tabela execucoes
"""

import time
from pathlib import Path

from src.config import PASTA_DESTINO
from src.logger import logger
from src.supabase_client import get_supabase, testar_conexao
from src.ingestao import INGESTORES

# Mesma lista do app.py
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


def _encontrar_excel_report(report_id: int) -> Path | None:
    """Encontra o arquivo .xlsx mais recente para um report_id na pasta destino."""
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    padrao = f"{report_id:02d} *.xlsx"
    arquivos = sorted(
        PASTA_DESTINO.glob(padrao),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return arquivos[0] if arquivos else None


def _registrar_execucao(tipo: str, status: str, **kwargs) -> None:
    """Registra uma execução na tabela execucoes do Supabase."""
    try:
        supabase = get_supabase()
        registro = {"tipo": tipo, "status": status}
        registro.update(kwargs)
        supabase.table("execucoes").insert(registro).execute()
    except Exception as e:
        logger.error(f"Falha ao registrar execução no Supabase: {e}")


def executar(data_inicio: str = None, data_fim: str = None) -> dict:
    """
    Executa o fluxo completo: extração + ingestão.

    Returns:
        dict com resumo da execução
    """
    logger.info("=" * 60)
    logger.info("ORQUESTRADOR — Iniciando fluxo completo")
    logger.info("=" * 60)

    tempo_inicio = time.time()
    id_execucao = None

    # 1. Testar conexão Supabase
    if not testar_conexao():
        logger.error("Falha na conexão com Supabase. Abortando.")
        return {"sucesso": False, "erro": "Conexão Supabase falhou"}

    # 2. Registrar início da execução
    _registrar_execucao(
        tipo="completo",
        status="iniciou",
        mensagem=f"Início: data_inicio={data_inicio}, data_fim={data_fim}",
    )

    # 3. Preparar fila de extração
    fila = []
    for report in REPORTS:
        fila.append({
            "report_id": report["id"],
            "report_name": report["name"],
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        })

    # 4. Executar extração
    status_robo = {
        "historico": {},
        "relatorio_atual": None,
    }

    logger.info(f"Extraindo {len(fila)} relatórios...")
    try:
        from src.base_agente import processar_fila_em_massa
        processar_fila_em_massa(fila=fila, status_robo=status_robo)
    except Exception as e:
        logger.error(f"Erro fatal na extração: {e}")

    # 5. Analisar resultados da extração
    extracao_sucesso = []
    extracao_falha = []

    for report in REPORTS:
        rid = str(report["id"])
        status = status_robo["historico"].get(rid, "desconhecido")
        if status == "sucesso":
            extracao_sucesso.append(report["id"])
        else:
            extracao_falha.append(report["id"])

    logger.info(f"Extração: {len(extracao_sucesso)} sucesso, {len(extracao_falha)} falha")

    # 6. Ingerir no Supabase
    ingestao_sucesso = []
    ingestao_falha = []
    total_linhas = 0

    for report_id in extracao_sucesso:
        # Report 10 só gera PDF, sem Excel para ingerir
        if report_id == 10:
            logger.info("Report 10 (Pagamentos Beneficiários) — apenas PDF, pulando ingestão")
            continue

        if report_id not in INGESTORES:
            logger.warning(f"Nenhum ingestor mapeado para report_id={report_id}")
            continue

        excel_path = _encontrar_excel_report(report_id)
        if excel_path is None:
            logger.warning(f"Excel não encontrado para report_id={report_id} na pasta {PASTA_DESTINO}")
            ingestao_falha.append(report_id)
            continue

        try:
            ingestor_cls = INGESTORES[report_id]
            ingestor = ingestor_cls()
            total = ingestor.executar(excel_path)
            ingestao_sucesso.append(report_id)
            total_linhas += total
            logger.info(f"Ingestão report {report_id}: {total} linhas inseridas")
        except Exception as e:
            logger.error(f"Falha na ingestão report {report_id}: {e}")
            ingestao_falha.append(report_id)

    # 7. Registrar resultado final
    tempo_total = time.time() - tempo_inicio
    sucesso_geral = len(ingestao_falha) == 0
    status_final = "sucesso" if sucesso_geral else "falha"

    mensagem = (
        f"Extração: {len(extracao_sucesso)}/{len(REPORTS)} OK | "
        f"Ingestão: {len(ingestao_sucesso)}/{len(ingestao_sucesso) + len(ingestao_falha)} OK | "
        f"Linhas: {total_linhas} | "
        f"Tempo: {tempo_total:.0f}s"
    )

    _registrar_execucao(
        tipo="completo",
        status=status_final,
        relatorios_processados=len(REPORTS),
        relatorios_sucesso=len(ingestao_sucesso),
        relatorios_falha=len(ingestao_falha),
        total_linhas_inseridas=total_linhas,
        mensagem=mensagem,
    )

    logger.info("=" * 60)
    logger.info(f"ORQUESTRADOR — Concluído em {tempo_total:.1f}s")
    logger.info(f"  Extração: {len(extracao_sucesso)}/{len(REPORTS)} sucesso")
    logger.info(f"  Ingestão: {len(ingestao_sucesso)}/{len(ingestao_sucesso) + len(ingestao_falha)} sucesso")
    logger.info(f"  Linhas inseridas: {total_linhas}")
    logger.info("=" * 60)

    return {
        "sucesso": sucesso_geral,
        "extracao_sucesso": extracao_sucesso,
        "extracao_falha": extracao_falha,
        "ingestao_sucesso": ingestao_sucesso,
        "ingestao_falha": ingestao_falha,
        "total_linhas": total_linhas,
        "tempo_total": tempo_total,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Orquestrador: extração + ingestão Supabase")
    parser.add_argument("--data-inicio", help="Data início (YYYY-MM-DD)")
    parser.add_argument("--data-fim", help="Data fim (YYYY-MM-DD)")
    args = parser.parse_args()

    resultado = executar(data_inicio=args.data_inicio, data_fim=args.data_fim)
    status = "SUCESSO" if resultado["sucesso"] else "FALHA"
    print(f"\n{'='*40}")
    print(f"Resultado: {status}")
    print(f"Extração:  {len(resultado['extracao_sucesso'])}/15")
    print(f"Ingestão:  {len(resultado['ingestao_sucesso'])}/15")
    print(f"Linhas:    {resultado['total_linhas']}")
    print(f"Tempo:     {resultado['tempo_total']:.0f}s")
