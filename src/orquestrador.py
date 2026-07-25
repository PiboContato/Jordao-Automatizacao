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

from src.config import PASTA_DESTINO, DIAS_RETENCAO_LOCAL
from src.logger import logger
from src.supabase_client import get_supabase, testar_conexao
from src.ingestao import INGESTORES
from src.alertas import alertar_falha
from src.utils import limpar_arquivos_antigos

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

# Relatórios com limitações técnicas conhecidas — pulados na execução em massa
REPORTS_EXCLUIDOS = {3, 9, 10}


def _encontrar_excel_reports(report_id: int) -> list[Path]:
    """Encontra TODOS os arquivos .xlsx para um report_id na pasta destino.

    Relatórios que extraem mês a mês (6, 11, 14) geram múltiplos arquivos.
    Retornar apenas o mais recente causava perda silenciosa de dados de meses anteriores.
    """
    PASTA_DESTINO.mkdir(parents=True, exist_ok=True)
    padrao = f"{report_id:02d} *.xlsx"
    arquivos = sorted(
        PASTA_DESTINO.glob(padrao),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return list(arquivos)


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


def executar(data_inicio: str = None, data_fim: str = None, report_id: int = None, skip_extract: bool = False) -> dict:
    """
    Executa o fluxo completo: extração + ingestão.

    Args:
        report_id: se informado, roda apenas esse relatório (1-15)
        skip_extract: se True, pula a extração e vai direto para ingestão

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
        mensagem=f"Início: data_inicio={data_inicio}, data_fim={data_fim}, report_id={report_id}",
    )

    # Filtrar relatório específico se --report-id informado
    reports_alvo = REPORTS
    if report_id is not None:
        reports_alvo = [r for r in REPORTS if r["id"] == report_id]
        if not reports_alvo:
            logger.error(f"report_id={report_id} não encontrado. IDs válidos: 1-15")
            return {"sucesso": False, "erro": f"report_id {report_id} inválido"}
    else:
        reports_alvo = [r for r in reports_alvo if r["id"] not in REPORTS_EXCLUIDOS]
        if REPORTS_EXCLUIDOS:
            logger.info(f"Relatórios excluídos (limitações técnicas): IDs {sorted(REPORTS_EXCLUIDOS)}")

    from src.utils import calcular_datas_padrao
    mapa_datas = { r["id"]: r for r in calcular_datas_padrao() }

    # 3. Preparar fila de extração
    fila = []
    for report in reports_alvo:
        rid = report["id"]
        # Usa data_inicio/fim se vier via CLI, caso contrário puxa do mapa de datas inteligentes
        d_ini = data_inicio if data_inicio else mapa_datas.get(rid, {}).get("data_inicio", "")
        d_fim = data_fim if data_fim else mapa_datas.get(rid, {}).get("data_fim", "")
        
        fila.append({
            "report_id": rid,
            "report_name": report["name"],
            "data_inicio": d_ini,
            "data_fim": d_fim,
        })

    # 4. Executar extração
    status_robo = {
        "historico": {},
        "relatorio_atual": None,
        "tempos_execucao": {},
    }

    extracao_sucesso = []
    extracao_falha = []

    if skip_extract:
        logger.info("Modo --skip-extract: pulando extração, verificando Excels existentes...")
        for report in reports_alvo:
            excel_paths = _encontrar_excel_reports(report["id"])
            if excel_paths:
                extracao_sucesso.append(report["id"])
                status_robo["historico"][str(report["id"])] = "sucesso"
                logger.info(f"Excel(s) encontrado(s) para report {report['id']}: {', '.join(p.name for p in excel_paths)}")
            else:
                extracao_falha.append(report["id"])
                status_robo["historico"][str(report["id"])] = "falha"
                logger.warning(f"Excel NÃO encontrado para report {report['id']}")
    else:
        logger.info(f"Extraindo {len(fila)} relatórios...")
        try:
            from src.base_agente import processar_fila_em_massa
            processar_fila_em_massa(fila=fila, status_robo=status_robo)
        except Exception as e:
            logger.error(f"Erro fatal na extração: {e}")

        # 5. Analisar resultados da extração
        for report in reports_alvo:
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
    try:
        for rid in extracao_sucesso:
            # Report 10 só gera PDF, sem Excel para ingerir
            if rid == 10:
                logger.info("Report 10 (Pagamentos Beneficiários) — apenas PDF, pulando ingestão")
                _registrar_execucao(
                    tipo="completo",
                    status="sucesso",
                    relatorios_processados=1,
                    relatorios_sucesso=1,
                    relatorios_falha=0,
                    total_linhas_inseridas=0,
                    mensagem="Report 10 (Pagamentos Beneficiários) — apenas PDF, sem ingestão."
                )
                continue

            if rid not in INGESTORES:
                logger.warning(f"Nenhum ingestor mapeado para report_id={rid}")
                continue

            excel_paths = _encontrar_excel_reports(rid)
            if not excel_paths:
                logger.warning(f"Excel não encontrado para report_id={rid} na pasta {PASTA_DESTINO}")
                ingestao_falha.append(rid)
                continue

            ingestor_cls = INGESTORES[rid]
            report_sucesso = False

            for excel_path in excel_paths:
                try:
                    ingestor = ingestor_cls()
                    resultado_ingestao = ingestor.executar(excel_path)
                    report_sucesso = True
                    total_linhas += resultado_ingestao["inseridos"]
                    logger.info(f"Ingestão report {rid} ({excel_path.name}): {resultado_ingestao['inseridos']} linhas inseridas, {resultado_ingestao['duplicados']} duplicadas ignoradas")

                    mensagem = f"Report {rid} ({excel_path.name}): {resultado_ingestao['inseridos']} inseridos, {resultado_ingestao['duplicados']} duplicados."
                    if resultado_ingestao.get("total_supabase") is not None:
                        total_formatado = f"{resultado_ingestao['total_supabase']:,}".replace(",", ".")
                        mensagem += f"\nTotal de itens da tabela no Supabase: {total_formatado}"
                    if resultado_ingestao.get("data_min") and resultado_ingestao.get("data_max"):
                        mensagem += f"\nData início da tabela no Supabase: {resultado_ingestao['data_min']}\nData fim da tabela do Supabase: {resultado_ingestao['data_max']}"

                    _registrar_execucao(
                        tipo="completo",
                        status="sucesso",
                        relatorios_processados=1,
                        relatorios_sucesso=1,
                        relatorios_falha=0,
                        total_linhas_inseridas=resultado_ingestao["inseridos"],
                        mensagem=mensagem
                    )
                except Exception as e:
                    logger.error(f"Falha na ingestão report {rid} ({excel_path.name}): {e}")
                    alertar_falha(
                        etapa=f"ingestao_report_{rid}",
                        detalhes=f"Report {rid} ({excel_path.name}): {str(e)}"
                    )
                    _registrar_execucao(
                        tipo="completo",
                        status="falha",
                        relatorios_processados=1,
                        relatorios_sucesso=0,
                        relatorios_falha=1,
                        total_linhas_inseridas=0,
                        mensagem=f"Falha ao ingerir Report {rid} ({excel_path.name}): {str(e)}"
                    )

            if report_sucesso:
                ingestao_sucesso.append(rid)
            else:
                ingestao_falha.append(rid)
    except Exception as e_geral:
        logger.error(f"Erro inesperado na fase de ingestão: {e_geral}")
        alertar_falha(
            etapa="ingestao_geral",
            detalhes=f"Erro inesperado na fase de ingestão: {str(e_geral)}"
        )
        _registrar_execucao(
            tipo="completo",
            status="falha",
            relatorios_processados=len(extracao_sucesso),
            relatorios_sucesso=len(ingestao_sucesso),
            relatorios_falha=len(ingestao_falha),
            total_linhas_inseridas=total_linhas,
            mensagem=f"Erro inesperado na fase de ingestão: {str(e_geral)}"
        )

    # 7. Registrar resultado final
    tempo_total = time.time() - tempo_inicio
    sucesso_geral = len(ingestao_falha) == 0
    status_final = "sucesso" if sucesso_geral else "falha"

    mensagem = (
        f"Extração: {len(extracao_sucesso)}/{len(reports_alvo)} OK | "
        f"Ingestão: {len(ingestao_sucesso)}/{len(ingestao_sucesso) + len(ingestao_falha)} OK | "
        f"Linhas: {total_linhas} | "
        f"Tempo: {tempo_total:.0f}s"
    )

    _registrar_execucao(
        tipo="completo",
        status=status_final,
        relatorios_processados=len(reports_alvo),
        relatorios_sucesso=len(ingestao_sucesso),
        relatorios_falha=len(ingestao_falha),
        total_linhas_inseridas=total_linhas,
        mensagem=mensagem,
    )

    logger.info("=" * 60)
    logger.info(f"ORQUESTRADOR — Concluído em {tempo_total:.1f}s")
    logger.info(f"  Extração: {len(extracao_sucesso)}/{len(reports_alvo)} sucesso")
    logger.info(f"  Ingestão: {len(ingestao_sucesso)}/{len(ingestao_sucesso) + len(ingestao_falha)} sucesso")
    logger.info(f"  Linhas inseridas: {total_linhas}")
    logger.info("=" * 60)

    # Executa a auto-limpeza de arquivos locais antigos
    try:
        limpar_arquivos_antigos(PASTA_DESTINO, DIAS_RETENCAO_LOCAL)
    except Exception as e:
        logger.error(f"Falha na auto-limpeza de arquivos: {e}")

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
    parser.add_argument("--report-id", type=int, help="Rodar apenas um relatório específico (ID 1-15)")
    parser.add_argument("--skip-extract", action="store_true", help="Pular extração, apenas ingerir Excel existente")
    args = parser.parse_args()

    resultado = executar(
        data_inicio=args.data_inicio,
        data_fim=args.data_fim,
        report_id=args.report_id,
        skip_extract=args.skip_extract,
    )
    status = "SUCESSO" if resultado["sucesso"] else "FALHA"
    total_reports = len(resultado.get("extracao_sucesso", [])) + len(resultado.get("extracao_falha", []))
    print(f"\n{'='*40}")
    print(f"Resultado: {status}")
    print(f"Extração:  {len(resultado['extracao_sucesso'])}/{total_reports}")
    print(f"Ingestão:  {len(resultado['ingestao_sucesso'])}/{len(resultado['ingestao_sucesso']) + len(resultado['ingestao_falha'])}")
    print(f"Linhas:    {resultado['total_linhas']}")
    print(f"Tempo:     {resultado['tempo_total']:.0f}s")
