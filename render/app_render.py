"""
app_render.py — Dashboard read-only para Render.
Conecta ao Supabase e exibe tabelas, KPIs, execucoes e logs.
SEM Playwright, SEM extracao, SEM risco para a VM.
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "render-secret-change-me")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "admin")

_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

REPORTS = [
    {"id": 1, "name": "01 Relatorio de Imoveis", "table": "relatorio_01_imoveis", "desc": "Cadastro geral de imoveis, proprietarios, dados de enderecos e status."},
    {"id": 2, "name": "02 Relatorio de Contratos", "table": "relatorio_02_contratos", "desc": "Contratos ativos, inquilinos, datas de vigencia e reajuste."},
    {"id": 4, "name": "04 Relatorio Ficha do Contrato", "table": "relatorio_04_ficha_contrato", "desc": "Fichas de contrato detalhadas com fiadores, taxas e garantias."},
    {"id": 5, "name": "05 Relatorio por Tipo de Recebimento", "table": "relatorio_05_tipo_recebimento", "desc": "Separacao de repasses e taxas cobradas agrupadas por tipo."},
    {"id": 6, "name": "06 Relatorio de Cobranca Aluguel e IPTU", "table": "relatorio_06_cobranca_aluguel", "desc": "Boletos gerados, taxas de IPTU associadas e vencimentos."},
    {"id": 7, "name": "07 Relatorio de Cobrancas Recebidas", "table": "relatorio_07_cobrancas_recebidas", "desc": "Baixas e pagamentos recebidos de inquilinos com data do repasse."},
    {"id": 8, "name": "08 Relatorio de Contratos x Cobrancas", "table": "relatorio_08_contratos_x_cobrancas", "desc": "Auditoria comparativa entre cobrancas previstas em contrato e geradas."},
    {"id": 11, "name": "11 Relatorio de Conferencia de Despesas", "table": "relatorio_11_conferencia_despesas", "desc": "Despesas pagas a prestadores e lancadas nas contas de proprietarios."},
    {"id": 12, "name": "12 Relatorio de Pessoas Ativos", "table": "relatorio_12_pessoas_ativos", "desc": "Cadastro de proprietarios, inquilinos e prestadores ativos no sistema."},
    {"id": 13, "name": "13 Relatorio de Recebimentos e Pagamentos", "table": "relatorio_13_recebimentos_pagamentos", "desc": "Resumo de caixa contendo entradas de recebimentos e saidas de pagamentos."},
    {"id": 14, "name": "14 Relatorio Conferencia Movimentos Detalhado", "table": "relatorio_14_movimentos_detalhados", "desc": "Auditoria de todos os lancamentos manuais e automaticos detalhados."},
    {"id": 15, "name": "15 Relatorio de Contas a Pagar / Receber", "table": "relatorio_15_contas_pagar_receber", "desc": "Projeccoes financeiras de contas e taxas futuras em aberto."},
]

def check_auth():
    return session.get("logged_in", False)

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.png", mimetype="image/png")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def index():
    if not check_auth():
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == DASHBOARD_USER and password == DASHBOARD_PASS:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Credenciais invalidas"
    return render_template("login_render.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not check_auth():
        return redirect(url_for("login"))
    return render_template("dashboard_render.html", reports=REPORTS)

@app.route("/api/supabase/dados", methods=["GET"])
def api_supabase_dados():
    if not check_auth():
        return jsonify({"error": "Nao autorizado"}), 401
    tabela = request.args.get("tabela")
    if not tabela:
        return jsonify({"error": "Tabela nao especificada"}), 400
    try:
        supabase = get_supabase()
        limit = 1000
        offset = 0
        registros = []
        while True:
            response = supabase.table(tabela).select("*").order("id", desc=True).range(offset, offset + limit - 1).execute()
            if not response.data:
                break
            registros.extend(response.data)
            if len(response.data) < limit:
                break
            offset += limit
        if not registros:
            return jsonify({"colunas": [], "linhas": [], "total": 0})
        colunas_set = set()
        linhas_formatadas = []
        for reg in registros:
            dados_internos = reg.get("dados") or {}
            colunas_set.update(dados_internos.keys())
            linha = {"__id": reg.get("id"), "__data_extracao": reg.get("data_extracao")}
            for col, val in dados_internos.items():
                linha[col] = val
            linhas_formatadas.append(linha)
        colunas = sorted(list(colunas_set))
        return jsonify({"colunas": colunas, "linhas": linhas_formatadas, "total": len(linhas_formatadas)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/execucoes", methods=["GET"])
def api_supabase_execucoes():
    if not check_auth():
        return jsonify({"error": "Nao autorizado"}), 401
    try:
        supabase = get_supabase()
        response = supabase.table("execucoes").select("*").order("id", desc=True).limit(500).execute()
        return jsonify({"execucoes": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/kpis", methods=["GET"])
def api_supabase_kpis():
    if not check_auth():
        return jsonify({"error": "Nao autorizado"}), 401
    try:
        supabase = get_supabase()
        kpis = {}
        try:
            res = supabase.table("relatorio_01_imoveis").select("id", count="exact").limit(1).execute()
            kpis["total_imoveis"] = res.count or 0
        except Exception:
            kpis["total_imoveis"] = "-"
        try:
            res = supabase.table("relatorio_02_contratos").select("id", count="exact").limit(1).execute()
            kpis["total_contratos"] = res.count or 0
        except Exception:
            kpis["total_contratos"] = "-"
        contas_receber = 0.0
        contas_pagar = 0.0
        try:
            res = supabase.table("relatorio_15_contas_pagar_receber").select("dados").limit(1000).execute()
            for row in (res.data or []):
                dados = row.get("dados") or {}
                tipo = str(dados.get("Tipo") or "").upper()
                valor_str = str(dados.get("Valor") or "0").replace(".", "").replace(",", ".")
                try:
                    valor = float(valor_str)
                except (ValueError, TypeError):
                    valor = 0.0
                if "RECEBER" in tipo or "RECEB" in tipo:
                    contas_receber += valor
                elif "PAGAR" in tipo or "PAG" in tipo:
                    contas_pagar += valor
        except Exception:
            pass
        kpis["contas_receber"] = contas_receber
        kpis["contas_pagar"] = contas_pagar
        try:
            res = supabase.table("execucoes").select("id", count="exact").limit(1).execute()
            kpis["total_execucoes"] = res.count or 0
        except Exception:
            kpis["total_execucoes"] = "-"
        try:
            res = supabase.table("execucoes").select("status").order("id", desc=True).limit(50).execute()
            sucessos = sum(1 for e in (res.data or []) if e.get("status") == "sucesso")
            total = len(res.data or [])
            kpis["taxa_sucesso"] = f"{sucessos}/{total}" if total > 0 else "-"
        except Exception:
            kpis["taxa_sucesso"] = "-"
        return jsonify(kpis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/logs", methods=["GET"])
def api_supabase_logs():
    if not check_auth():
        return jsonify({"error": "Nao autorizado"}), 401
    try:
        supabase = get_supabase()
        nivel = request.args.get("nivel")
        query = supabase.table("logs").select("*").order("id", desc=True).limit(200)
        if nivel and nivel != "todos":
            query = query.eq("nivel", nivel)
        response = query.execute()
        return jsonify({"logs": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
