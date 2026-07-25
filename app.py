import threading
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory

from src.config import DASHBOARD_USER, DASHBOARD_PASS, PASTA_DESTINO, JORDAO_USUARIO, JORDAO_SENHA, DIAS_RETENCAO_LOCAL
from src.utils import gerar_nome_arquivo, garantir_pasta_destino, limpar_arquivos_antigos
from src.logger import logger, obter_logs_recentes, limpar_logs_recentes
from src.supabase_client import get_supabase

import os
app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.png", mimetype="image/png")

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
    
    try:
        limpar_logs_recentes()
        logger.info("Processamento da fila de relatórios iniciado.")

        # Guardar quais IDs entraram nesta fila para ingestão posterior
        ids_nesta_fila = [str(item["report_id"]) for item in status_robo["fila"]]

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
            # Executar a ingestão no Supabase dos novos relatórios baixados com sucesso
            from src.ingestao import INGESTORES
            from src.orquestrador import _encontrar_excel_reports, _registrar_execucao
            try:
                # Determinamos se foi em lote ou manual
                origem = "Lote" if len(ids_nesta_fila) > 1 else "Manual"
                
                for report_id_str in ids_nesta_fila:
                    rid = int(report_id_str)
                    status = status_robo["historico"].get(report_id_str)
                    
                    # Se for o relatório 10, ele só gera PDF e não tem ingestão, mas registramos sucesso/falha
                    if rid == 10:
                        if status == "sucesso":
                            _registrar_execucao(
                                tipo="completo",
                                status="sucesso",
                                relatorios_processados=1,
                                relatorios_sucesso=1,
                                relatorios_falha=0,
                                total_linhas_inseridas=0,
                                mensagem=f"Extração em {origem} Report 10 concluída com sucesso (apenas PDF)."
                            )
                        else:
                            _registrar_execucao(
                                tipo="completo",
                                status="falha",
                                relatorios_processados=1,
                                relatorios_sucesso=0,
                                relatorios_falha=1,
                                total_linhas_inseridas=0,
                                mensagem=f"Extração em {origem} Report 10 falhou ou foi cancelada durante o processo."
                            )
                        continue

                    if status == "sucesso":
                        if rid not in INGESTORES:
                            continue
                        
                        excel_paths = _encontrar_excel_reports(rid)
                        if not excel_paths:
                            logger.warning(f"Excel não encontrado para o relatório {rid} pós-extração.")
                            _registrar_execucao(
                                tipo="completo",
                                status="falha",
                                relatorios_processados=1,
                                relatorios_sucesso=0,
                                relatorios_falha=1,
                                total_linhas_inseridas=0,
                                mensagem=f"Extração em {origem} Report {rid}: Excel não encontrado após a extração."
                            )
                            continue
                        
                        report_sucesso = False
                        for excel_path in excel_paths:
                            try:
                                logger.info(f"Ingestão pós-extração para o relatório {rid} ({excel_path.name}) iniciada...")
                                ingestor_cls = INGESTORES[rid]
                                ingestor = ingestor_cls()
                                res = ingestor.executar(excel_path)
                                report_sucesso = True
                                logger.info(f"Ingestão concluída para relatório {rid} ({excel_path.name}): {res['inseridos']} inseridos, {res['duplicados']} duplicados.")
                                
                                mensagem = f"Extração em {origem} Report {rid} ({excel_path.name}): {res['inseridos']} inseridos, {res['duplicados']} duplicados."
                                if res.get("total_supabase") is not None:
                                    total_formatado = f"{res['total_supabase']:,}".replace(",", ".")
                                    mensagem += f"\nTotal de itens da tabela no Supabase: {total_formatado}"
                                if res.get("data_min") and res.get("data_max"):
                                    mensagem += f"\nData início da tabela no Supabase: {res['data_min']}\nData fim da tabela do Supabase: {res['data_max']}"
                                
                                _registrar_execucao(
                                    tipo="completo",
                                    status="sucesso",
                                    relatorios_processados=1,
                                    relatorios_sucesso=1,
                                    relatorios_falha=0,
                                    total_linhas_inseridas=res["inseridos"],
                                    mensagem=mensagem
                                )
                            except Exception as e_ing:
                                logger.error(f"Erro ao processar ingestão para o Report {rid} ({excel_path.name}): {e_ing}")
                                _registrar_execucao(
                                    tipo="completo",
                                    status="falha",
                                    relatorios_processados=1,
                                    relatorios_sucesso=0,
                                    relatorios_falha=1,
                                    total_linhas_inseridas=0,
                                    mensagem=f"Extração em {origem} Report {rid} ({excel_path.name}): Falha na ingestão: {str(e_ing)}"
                                )
                        
                        if not report_sucesso:
                            status_robo["historico"][report_id_str] = "falha"
                    else:
                        _registrar_execucao(
                            tipo="completo",
                            status="falha",
                            relatorios_processados=1,
                            relatorios_sucesso=0,
                            relatorios_falha=1,
                            total_linhas_inseridas=0,
                            mensagem=f"Extração em {origem} Report {rid}: Falha ou cancelada durante a extração."
                        )
            except Exception as e:
                logger.error(f"Erro ao processar ingestão no lote: {e}")
            
        try:
            limpar_arquivos_antigos(PASTA_DESTINO, DIAS_RETENCAO_LOCAL)
        except Exception as e_clean:
            logger.error(f"Falha na auto-limpeza de arquivos locais: {e_clean}")
    finally:
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
        
        if (username == DASHBOARD_USER and password == DASHBOARD_PASS) or \
           (username == JORDAO_USUARIO and password == JORDAO_SENHA):
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

@app.route("/api/supabase/dados", methods=["GET"])
def api_supabase_dados():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    
    tabela = request.args.get("tabela")
    if not tabela:
        return jsonify({"error": "Tabela não especificada"}), 400
        
    try:
        supabase = get_supabase()
        # Buscar todos os dados com paginação (sem limite cego de 1000)
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
            
        # Extrair todas as chaves possíveis de "dados"
        colunas_set = set()
        linhas_formatadas = []
        for reg in registros:
            dados_internos = reg.get("dados") or {}
            colunas_set.update(dados_internos.keys())
            
            # Adiciona metadados da linha
            linha = {
                "__id": reg.get("id"),
                "__data_extracao": reg.get("data_extracao")
            }
            # Adiciona dados reais
            for col, val in dados_internos.items():
                linha[col] = val
            linhas_formatadas.append(linha)
            
        colunas = sorted(list(colunas_set))
        return jsonify({
            "colunas": colunas,
            "linhas": linhas_formatadas,
            "total": len(linhas_formatadas)
        })
    except Exception as e:
        logger.error(f"Erro ao buscar dados da tabela {tabela}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/execucoes", methods=["GET"])
def api_supabase_execucoes():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    try:
        supabase = get_supabase()
        response = supabase.table("execucoes").select("*").order("id", desc=True).limit(500).execute()
        return jsonify({"execucoes": response.data or []})
    except Exception as e:
        logger.error(f"Erro ao buscar execuções do Supabase: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/kpis", methods=["GET"])
def api_supabase_kpis():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    try:
        supabase = get_supabase()
        kpis = {}
        
        # 1. Total de Imóveis
        try:
            res = supabase.table("relatorio_01_imoveis").select("id", count="exact").limit(1).execute()
            kpis["total_imoveis"] = res.count or 0
        except Exception:
            kpis["total_imoveis"] = "-"
            
        # 2. Total de Contratos Ativos
        try:
            res = supabase.table("relatorio_02_contratos").select("id", count="exact").limit(1).execute()
            kpis["total_contratos"] = res.count or 0
        except Exception:
            kpis["total_contratos"] = "-"
            
        # 3. Contas a Receber vs Pagar (Mês Corrente)
        contas_receber = 0.0
        contas_pagar = 0.0
        try:
            # Puxamos as contas de contas_pagar_receber (id 15)
            res = supabase.table("relatorio_15_contas_pagar_receber").select("dados").limit(1000).execute()
            for row in (res.data or []):
                dados = row.get("dados") or {}
                # Limpar e somar valores
                tipo = str(dados.get("Tipo") or "").upper()
                valor_str = str(dados.get("Valor") or "0").replace(".", "").replace(",", ".")
                try:
                    valor = float(valor_str)
                except ValueError:
                    valor = 0.0
                    
                if "RECEBER" in tipo or "RECEB" in tipo:
                    contas_receber += valor
                elif "PAGAR" in tipo or "PAG" in tipo:
                    contas_pagar += valor
            kpis["contas_receber"] = round(contas_receber, 2)
            kpis["contas_pagar"] = round(contas_pagar, 2)
        except Exception as e:
            logger.warning(f"Erro ao calcular contas a pagar/receber para KPIs: {e}")
            kpis["contas_receber"] = "-"
            kpis["contas_pagar"] = "-"
            
        return jsonify(kpis)
    except Exception as e:
        logger.error(f"Erro ao gerar KPIs: {e}")
        return jsonify({"error": str(e)}), 500

# ----------------- REGRA DO MOTOR DE AGENDAMENTO (EMBUTIDO) -----------------
AGENDAMENTO_FILE = "agendamento.json"

from src.utils import calcular_datas_padrao

@app.route("/api/agendamento", methods=["GET"])
def obter_agendamento():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    import json
    try:
        if os.path.exists(AGENDAMENTO_FILE):
            with open(AGENDAMENTO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"horarios": []}
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agendamento", methods=["POST"])
def salvar_agendamento():
    if not check_auth():
        return jsonify({"error": "Não autorizado"}), 401
    import json
    try:
        req_data = request.get_json() or {}
        horarios = req_data.get("horarios", [])
        
        # Validar formato HH:MM
        validated = []
        for h in horarios:
            if h and len(h) == 5 and ":" in h:
                parts = h.split(":")
                try:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        validated.append(f"{hour:02d}:{minute:02d}")
                except ValueError:
                    pass
        
        with open(AGENDAMENTO_FILE, "w", encoding="utf-8") as f:
            json.dump({"horarios": validated}, f, indent=2)
            
        return jsonify({"status": "Agendamento atualizado com sucesso!", "horarios": validated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def motor_agendamento():
    global status_robo
    import json
    import datetime
    logger.info("Motor de agendamento em segundo plano iniciado com sucesso.")
    ultimo_disparo = None
    
    while True:
        try:
            time.sleep(30)
            if not os.path.exists(AGENDAMENTO_FILE):
                continue
                
            with open(AGENDAMENTO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            horarios = data.get("horarios", [])
            
            if not horarios:
                continue
                
            agora = datetime.datetime.now()
            agora_hm = agora.strftime("%H:%M")
            agora_completo = agora.strftime("%Y-%m-%d %H:%M")
            
            if agora_hm in horarios and ultimo_disparo != agora_completo:
                if status_robo["rodando"]:
                    logger.warning(f"Horário agendado {agora_hm} atingido, mas o robô já está executando outra tarefa no momento. Pulando execução atual para evitar conflitos.")
                    ultimo_disparo = agora_completo
                    continue
                    
                logger.info(f"Agendamento automático disparado para as {agora_hm}!")
                
                relatorios = calcular_datas_padrao()
                
                status_robo["fila"] = []
                for rel in relatorios:
                    report_id = rel["id"]
                    report_name = next((r["name"] for r in REPORTS if r["id"] == report_id), f"Relatório {report_id}")
                    status_robo["fila"].append({
                        "report_id": report_id,
                        "report_name": report_name,
                        "data_inicio": rel["data_inicio"],
                        "data_fim": rel["data_fim"]
                    })
                    status_robo["historico"][str(report_id)] = "na_fila"
                
                thread = threading.Thread(target=processar_fila)
                thread.start()
                
                ultimo_disparo = agora_completo
                
        except Exception as e_sched:
            logger.error(f"Erro no motor de agendamento de segundo plano: {e_sched}")

# Inicia a thread de fundo do agendador
threading.Thread(target=motor_agendamento, daemon=True).start()

def ouvinte_comandos_remotos():
    """Thread em segundo plano na VM que escuta comandos enviados do Render via Supabase."""
    global status_robo, active_browser
    import json
    logger.info("Ouvinte de comandos remotos em segundo plano iniciado com sucesso.")
    
    while True:
        try:
            time.sleep(5)
            supabase = get_supabase()
            res = supabase.table("comandos_remotos").select("*").eq("status", "pendente").order("id", desc=True).limit(1).execute()
            if not res.data:
                continue
            
            comando = res.data[0]
            cmd_id = comando["id"]
            tipo = comando.get("tipo")
            payload = comando.get("payload", {})
            
            # 1. Trata comando de cancelamento imediatamente sem bloquear
            if tipo == "cancelar_execucao":
                logger.warning(f"Solicitação remota de cancelamento recebida [ID {cmd_id}].")
                status_robo["cancelado"] = True
                status_robo["rodando"] = False
                if active_browser:
                    try:
                        active_browser.close()
                        active_browser = None
                    except Exception as e_br:
                        logger.warning(f"Erro ao fechar navegador ativamente: {e_br}")
                
                supabase.table("comandos_remotos").update({
                    "status": "concluido",
                    "mensagem": "Execução cancelada com sucesso na VM."
                }).eq("id", cmd_id).execute()
                continue

            # 2. Se o robô estiver executando outro processo, aguarda em silêncio
            if status_robo["rodando"]:
                tempo_decorrido = time.time() - status_robo.get("tempo_inicio", time.time())
                if tempo_decorrido > 300:
                    logger.warning(f"Trava de execução resetada por timeout ({int(tempo_decorrido)}s).")
                    status_robo["rodando"] = False
                else:
                    continue

            logger.info(f"Comando remoto capturado na VM [ID {cmd_id}]: tipo={tipo}")

            # 3. Marca status como em_execucao
            supabase.table("comandos_remotos").update({
                "status": "em_execucao",
                "mensagem": "Robô iniciou o processamento na VM..."
            }).eq("id", cmd_id).execute()

            if tipo in ("extracao_massa", "extracao_relatorio"):
                relatorios_lista = payload.get("relatorios", [])
                
                status_robo["fila"] = []
                from src.utils import calcular_datas_padrao
                mapa_datas = { r["id"]: r for r in calcular_datas_padrao() }

                for item in relatorios_lista:
                    if isinstance(item, dict):
                        rid = item.get("report_id")
                        d_ini_cust = item.get("data_inicio")
                        d_fim_cust = item.get("data_fim")
                    else:
                        rid = int(item)
                        d_ini_cust = None
                        d_fim_cust = None

                    if not rid:
                        continue

                    rel_info = next((r for r in REPORTS if r["id"] == rid), None)
                    rname = rel_info["name"] if rel_info else f"Relatório {rid}"
                    
                    d_ini = d_ini_cust if d_ini_cust else mapa_datas.get(rid, {}).get("data_inicio", "")
                    d_fim = d_fim_cust if d_fim_cust else mapa_datas.get(rid, {}).get("data_fim", "")
                    
                    status_robo["fila"].append({
                        "report_id": rid,
                        "report_name": rname,
                        "data_inicio": d_ini,
                        "data_fim": d_fim
                    })
                    status_robo["historico"][str(rid)] = "na_fila"
                
                processar_fila()
                
                supabase.table("comandos_remotos").update({
                    "status": "concluido",
                    "mensagem": "Execução do comando concluída com sucesso na VM."
                }).eq("id", cmd_id).execute()

            elif tipo == "salvar_agendamento":
                horarios = payload.get("horarios", [])
                validated = [h for h in horarios if isinstance(h, str) and len(h) == 5 and ":" in h]
                with open(AGENDAMENTO_FILE, "w", encoding="utf-8") as f:
                    json.dump({"horarios": validated}, f, indent=2)
                
                supabase.table("comandos_remotos").update({
                    "status": "concluido",
                    "mensagem": "Agendamento atualizado com sucesso na VM."
                }).eq("id", cmd_id).execute()

        except Exception as e_cmd:
            logger.error(f"Erro no ouvinte de comandos remotos: {e_cmd}")
            try:
                if 'cmd_id' in locals():
                    supabase.table("comandos_remotos").update({
                        "status": "falha",
                        "mensagem": f"Falha no processamento: {str(e_cmd)}"
                    }).eq("id", cmd_id).execute()
            except Exception:
                pass

# Inicia a thread de fundo do ouvinte remoto
threading.Thread(target=ouvinte_comandos_remotos, daemon=True).start()

if __name__ == "__main__":
    garantir_pasta_destino()
    import os
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
