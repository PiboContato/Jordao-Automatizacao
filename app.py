import threading
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session

from src.config import DASHBOARD_USER, DASHBOARD_PASS, PASTA_DESTINO, SECRET_KEY
from src.utils import gerar_nome_arquivo, garantir_pasta_destino
from src.alertas import alertar_sucesso
from src.logger import logger, obter_logs_recentes, limpar_logs_recentes

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Definição dos 15 relatórios
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

    from src.base_agente import processar_fila_em_massa
    processar_fila_em_massa(
        fila=status_robo["fila"],
        status_robo=status_robo,
        on_browser_start=_on_browser_start,
        is_cancelled=lambda: status_robo["cancelado"]
    )

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
    return render_template("dashboard.html", reports=REPORTS, pasta_destino=str(PASTA_DESTINO.absolute()))

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

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
    pasta_destino = data.get("pasta_destino")
    if pasta_destino:
        import os
        os.environ["PASTA_DESTINO_DINAMICA"] = pasta_destino
    
    if not report_id:
        return jsonify({"error": "report_id não fornecido"}), 400
        
    report_name = next((r["name"] for r in REPORTS if r["id"] == int(report_id)), f"Relatório {report_id}")
    
    status_robo["fila"].append({
        "report_id": int(report_id),
        "report_name": report_name,
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
    pasta_destino = data.get("pasta_destino")
    if pasta_destino:
        import os
        os.environ["PASTA_DESTINO_DINAMICA"] = pasta_destino
    
    for rel in relatorios:
        report_id = int(rel.get("id"))
        report_name = next((r["name"] for r in REPORTS if r["id"] == report_id), f"Relatório {report_id}")
        status_robo["fila"].append({
            "report_id": report_id,
            "report_name": report_name,
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
            logger.error(f"Erro ao cancelar robô: {e}")
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"status": "Sinal de cancelamento enviado"})

@app.route("/api/selecionar_pasta", methods=["POST"])
def selecionar_pasta():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    try:
        import tkinter as tk
        import tkinter.filedialog as fd
    except ImportError:
        return jsonify({"success": False, "message": "Seletor de pasta não disponível neste ambiente. Digite o caminho manualmente."})
    import subprocess
    import sys
    try:
        script = "import tkinter as tk, tkinter.filedialog as fd; root=tk.Tk(); root.withdraw(); root.attributes('-topmost', True); p=fd.askdirectory(); print(p)"
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        selected_path = result.stdout.strip()
        if selected_path:
            import os
            os.environ["PASTA_DESTINO_DINAMICA"] = selected_path
            return jsonify({"success": True, "path": selected_path})
        else:
            return jsonify({"success": False, "message": "Nenhuma pasta selecionada."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == "__main__":
    garantir_pasta_destino()
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
