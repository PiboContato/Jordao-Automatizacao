import threading
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

from src.config import DASHBOARD_USER, DASHBOARD_PASS
from src.base_agente import executar_com_retry
from src.utils import gerar_nome_arquivo
from src.alertas import alertar_sucesso
from src.logger import logger, obter_logs_recentes, limpar_logs_recentes

app = Flask(__name__)
app.secret_key = "astral_secret_key_123"

# Definição dos 13 relatórios
REPORTS = [
    {"id": 1, "name": "01 Relatório Genérico 01"},
    {"id": 2, "name": "02 Relatório Genérico 02"},
    {"id": 3, "name": "03 Relatório Genérico 03"},
    {"id": 4, "name": "04 Relatório Genérico 04"},
    {"id": 5, "name": "05 Relatório Genérico 05"},
    {"id": 6, "name": "06 Relatório Genérico 06"},
    {"id": 7, "name": "07 Relatório Genérico 07"},
    {"id": 8, "name": "08 Relatório Genérico 08"},
    {"id": 9, "name": "09 Relatório Genérico 09"},
    {"id": 10, "name": "10 Relatório Genérico 10"},
    {"id": 11, "name": "11 Relatório Genérico 11"},
    {"id": 12, "name": "12 Relatório Genérico 12"},
    {"id": 13, "name": "13 Relatório Genérico 13"},
    {"id": 14, "name": "14 Relatório Genérico 14"},
    {"id": 15, "name": "15 Relatório Genérico 15"},
]

# Variável global para armazenar o status do robô e a fila
status_robo = {
    "rodando": False,
    "mensagem": "Aguardando início...",
    "sucesso": None,
    "cancelado": False,
    "fila": [],
    "relatorio_atual": None,
    "historico": {}, # Guarda o status de sucesso/falha de cada relatório pelo ID
    "tempo_inicio": None,
    "tempos_execucao": {}
}

active_browser = None

def _on_browser_start(browser):
    global active_browser
    active_browser = browser

def processar_fila():
    global status_robo, active_browser
    status_robo["rodando"] = True
    status_robo["cancelado"] = False
    
    limpar_logs_recentes()
    logger.info("Processamento da fila de relatórios iniciado.")

    while status_robo["fila"] and not status_robo["cancelado"]:
        item = status_robo["fila"].pop(0)
        report_id = item["report_id"]
        data_inicio = item["data_inicio"]
        data_fim = item["data_fim"]
        
        report_name = next((r["name"] for r in REPORTS if r["id"] == report_id), f"Desconhecido {report_id}")
        
        status_robo["relatorio_atual"] = report_id
        status_robo["mensagem"] = f"Extraindo: {report_id} - {report_name}..."
        status_robo["sucesso"] = None
        status_robo["historico"][str(report_id)] = "rodando"
        status_robo["tempo_inicio"] = time.time()
        
        logger.info(f"=== Iniciando Extração: {report_id} - {report_name} ===")
        
        try:
            if report_id == 1:
                from src.relatorios.roteiro_servicos import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 2:
                from src.relatorios.contingencia import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 3:
                from src.relatorios.produtos_os import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 4:
                from src.relatorios.os_emitidas import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 5:
                from src.relatorios.propostas_geradas import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 6:
                from src.relatorios.servicos_executados import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 7:
                from src.relatorios.valor_hora import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 8:
                from src.relatorios.faturamento_geral import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 9:
                from src.relatorios.contas_receber import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 10:
                from src.relatorios.recebimentos import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 11:
                from src.relatorios.receita_competencia import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 12:
                from src.relatorios.contas_pagar import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 13:
                from src.relatorios.pagamentos import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 14:
                from src.relatorios.movimentos_contas import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            elif report_id == 15:
                from src.relatorios.painel_indicadores import extrair
                sucesso = executar_com_retry(
                    funcao_extracao=extrair,
                    report_id=report_id,
                    report_name=report_name,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    on_browser_start=_on_browser_start,
                    is_cancelled=lambda: status_robo["cancelado"]
                )
                
                if sucesso:
                    logger.info(f"Sucesso ao extrair: {report_name}")
                    status_robo["historico"][str(report_id)] = "sucesso"
                else:
                    logger.error(f"Falha na extração de: {report_name}")
                    status_robo["historico"][str(report_id)] = "falha"
            else:
                logger.info(f"Relatório não implementado: {report_name}")
                status_robo["historico"][str(report_id)] = "falha"
                
        except Exception as e:
            if not status_robo["cancelado"]:
                logger.error(f"Erro inesperado em {report_name}: {str(e)}")
                status_robo["historico"][str(report_id)] = "falha"
                
        if status_robo["tempo_inicio"] is not None:
            status_robo["tempos_execucao"][str(report_id)] = int(time.time() - status_robo["tempo_inicio"])
            status_robo["tempo_inicio"] = None

    if status_robo["cancelado"]:
        status_robo["mensagem"] = "Processo cancelado pelo usuário."
        status_robo["sucesso"] = False
        if status_robo["relatorio_atual"]:
            status_robo["historico"][str(status_robo["relatorio_atual"])] = "falha"
    else:
        status_robo["mensagem"] = "Fila de extração concluída!"
        status_robo["sucesso"] = True
        
    status_robo["rodando"] = False
    status_robo["relatorio_atual"] = None
    active_browser = None

def check_auth():
    return session.get("logged_in")

@app.route("/", methods=["GET"])
def index():
    if not check_auth():
        return redirect(url_for("login"))
    return render_template("dashboard.html", reports=REPORTS)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == DASHBOARD_USER and password == DASHBOARD_PASS:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            error = "Usuário ou senha inválidos."
            
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/api/iniciar", methods=["POST"])
def iniciar_robo():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
        
    global status_robo
    
    data = request.get_json() or {}
    report_id = data.get("report_id")
    data_inicio = data.get("data_inicio")
    data_fim = data.get("data_fim")
    
    if not report_id:
        return jsonify({"error": "report_id não fornecido"}), 400
        
    status_robo["fila"].append({
        "report_id": int(report_id),
        "data_inicio": data_inicio,
        "data_fim": data_fim
    })
    status_robo["historico"][str(report_id)] = "na_fila"
        
    if not status_robo["rodando"]:
        thread = threading.Thread(target=processar_fila)
        thread.start()
    
    return jsonify({"status": "Adicionado à fila!"})

@app.route("/api/iniciar_todos", methods=["POST"])
def iniciar_todos():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
        
    global status_robo
    
    data = request.get_json() or {}
    relatorios = data.get("relatorios", [])
    
    for rel in relatorios:
        report_id = int(rel.get("id"))
        status_robo["fila"].append({
            "report_id": report_id,
            "data_inicio": rel.get("data_inicio"),
            "data_fim": rel.get("data_fim")
        })
        status_robo["historico"][str(report_id)] = "na_fila"
        
    if not status_robo["rodando"]:
        thread = threading.Thread(target=processar_fila)
        thread.start()
    
    return jsonify({"status": f"{len(relatorios)} relatórios adicionados à fila!"})

@app.route("/api/status", methods=["GET"])
def obter_status():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    return jsonify({
        "rodando": status_robo["rodando"],
        "mensagem": status_robo["mensagem"],
        "sucesso": status_robo["sucesso"],
        "tamanho_fila": len(status_robo["fila"]),
        "relatorio_atual": status_robo["relatorio_atual"],
        "historico": status_robo["historico"],
        "tempo_inicio": status_robo.get("tempo_inicio"),
        "tempos_execucao": status_robo.get("tempos_execucao", {})
    })

@app.route("/api/logs", methods=["GET"])
def obter_logs():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    return jsonify({"logs": obter_logs_recentes()})

@app.route("/api/cancelar", methods=["POST"])
def cancelar_robo():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
        
    global status_robo, active_browser
    
    if not status_robo["rodando"] and not status_robo["fila"]:
        return jsonify({"status": "Robô não está rodando e fila está vazia"}), 400
        
    status_robo["cancelado"] = True
    status_robo["fila"] = []
    status_robo["mensagem"] = "Cancelamento solicitado. Limpando fila e interrompendo..."
    status_robo["sucesso"] = False
    
    if active_browser:
        try:
            active_browser.close()
        except Exception as e:
            logger.error(f"Erro ao tentar fechar navegador durante cancelamento: {e}")
            
    return jsonify({"status": "Sinal de cancelamento enviado"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
