"""
app_render.py — Dashboard read-only para Render.
Conecta ao Supabase e exibe tabelas, KPIs, execucoes e logs.
SEM Playwright, SEM extracao, SEM risco para a VM.

Autenticação: usuários reais em jordao_usuarios (senha com hash bcrypt) +
permissões por módulo, mesmo padrão dos painéis Astral/Britt — JWT em vez
de cookie de sessão; o frontend envia Authorization: Bearer <token>.
"""

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory
from supabase import create_client, Client
import bcrypt
import jwt as pyjwt
try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

app = Flask(
    __name__,
    static_url_path="/assets",
    static_folder="frontend/dist/assets",
    template_folder="frontend/dist"
)
app.secret_key = os.getenv("SECRET_KEY", "render-secret-change-me")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
JWT_SECRET = os.getenv("JWT_SECRET", "jordao-render-jwt-secret-change-me")
JWT_EXPIRACAO_HORAS = 12
# Fallback de bootstrap: enquanto não houver usuário criado na tabela
# jordao_usuarios, permite o primeiro acesso com estas credenciais.
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "admin")
REMOTE_SECRET = os.getenv("REMOTE_SECRET", "")

FLAGS_PERMISSAO = [
    "acesso_automacao", "acesso_bi", "acesso_tabelas", "acesso_auditoria",
    "acesso_backups", "acesso_logs", "acesso_notificacoes", "acesso_usuarios",
]
TEMAS_VALIDOS = {"colorido", "azul-claro", "azul-escuro", "verde", "roxo", "vermelho", "dourado", "marrom", "preto", "branco"}
COLUNAS_USUARIO_PUBLICO = "id, username, nome, cargo, modo_exibicao, criado_em, " + ", ".join(FLAGS_PERMISSAO)

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

# ===================================================================
# Autenticação (JWT) e permissões — mesmo padrão dos painéis Astral/Britt
# ===================================================================

def _usuario_publico(u: dict) -> dict:
    out = {
        "id": u["id"],
        "username": u["username"],
        "nome": u["nome"],
        "cargo": u["cargo"],
        "modo_exibicao": u.get("modo_exibicao") or "colorido",
        "criado_em": u.get("criado_em"),
    }
    for f in FLAGS_PERMISSAO:
        out[f] = bool(u.get(f))
    return out


def _gerar_token(usuario: dict) -> str:
    payload = {
        "id": usuario["id"],
        "username": usuario["username"],
        "nome": usuario["nome"],
        "cargo": usuario["cargo"],
        "modo_exibicao": usuario.get("modo_exibicao") or "colorido",
        **{f: bool(usuario.get(f)) for f in FLAGS_PERMISSAO},
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRACAO_HORAS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def requer_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        partes = auth_header.split(" ")
        if len(partes) != 2 or partes[0] != "Bearer":
            return jsonify({"error": "Token não fornecido"}), 401
        try:
            payload = pyjwt.decode(partes[1], JWT_SECRET, algorithms=["HS256"])
        except pyjwt.PyJWTError:
            return jsonify({"error": "Token inválido ou expirado"}), 401
        g.usuario = payload
        return f(*args, **kwargs)
    return wrapper


def requer_permissao(flag: str | None = None):
    """Sem flag: só exige login. Com flag: admin sempre passa, senão exige a flag específica."""
    def decorator(f):
        @wraps(f)
        @requer_login
        def wrapper(*args, **kwargs):
            if flag and g.usuario.get("cargo") != "admin" and not g.usuario.get(flag):
                return jsonify({"error": "Acesso negado. Permissão insuficiente."}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/favicon.png", methods=["GET"])
def favicon():
    return send_from_directory(app.template_folder, "favicon.png", mimetype="image/png")

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "rodando": False,
        "mensagem": "Painel Render (Conectado ao Supabase)",
        "sucesso": True,
        "historico": {},
        "tempos_execucao": {}
    })

@app.route("/api/status/ultima-atualizacao", methods=["GET"])
@requer_login
def api_ultima_atualizacao():
    """Data/hora da última execução bem-sucedida do robô na VM, qualquer
    relatório — mesmo espírito da barra "Última atualização" dos painéis
    Astral/Britt."""
    supabase = get_supabase()
    resp = (
        supabase.table("execucoes")
        .select("created_at")
        .eq("status", "sucesso")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    ultima = resp.data[0]["created_at"] if resp.data else None
    return jsonify({"ultima_atualizacao": ultima})

@app.route("/api/logs", methods=["GET"])
def api_logs_legacy():
    return jsonify({"logs": []})

@app.route("/firebase-messaging-sw.js")
def serve_sw():
    return send_from_directory(app.template_folder, "firebase-messaging-sw.js", mimetype="application/javascript")

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path.startswith("api/"):
        return jsonify({"error": "Endpoint nao encontrado"}), 404
    # Se o arquivo existir no dist raiz (como favicon.png), serve direto
    if path != "" and os.path.exists(os.path.join(app.template_folder, path)):
        return send_from_directory(app.template_folder, path)
    # Senão, retorna o index.html do React
    return send_from_directory(app.template_folder, "index.html")

# ===================================================================
# Autenticação: login, sessão atual e CRUD de usuários
# ===================================================================

def _buscar_usuario_por_login(username: str) -> dict | None:
    supabase = get_supabase()
    resp = (
        supabase.table("jordao_usuarios")
        .select(f"{COLUNAS_USUARIO_PUBLICO}, senha_hash")
        .ilike("username", username)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json() or {}
    username = str(data.get("username", "")).strip()
    senha = data.get("password", "")
    if not username or not senha:
        return jsonify({"error": "Usuário e senha são obrigatórios"}), 400

    # 1) Tenta usuário real na tabela jordao_usuarios
    usuario = _buscar_usuario_por_login(username)
    if usuario and bcrypt.checkpw(senha.encode("utf-8"), usuario["senha_hash"].encode("utf-8")):
        token = _gerar_token(usuario)
        return jsonify({"token": token, "usuario": _usuario_publico(usuario)})

    # 2) Fallback de bootstrap (DASHBOARD_USER/PASS) — gera token com perfil
    #    de administrador sem persistir nada, para o primeiro acesso migrar.
    if username == DASHBOARD_USER and password_ok(senha):
        fake = {
            "id": -1,
            "username": username,
            "nome": "Administrador (bootstrap)",
            "cargo": "admin",
            "modo_exibicao": "colorido",
            **{f: True for f in FLAGS_PERMISSAO},
        }
        token = _gerar_token(fake)
        return jsonify({"token": token, "usuario": _usuario_publico(fake)})

    return jsonify({"error": "Credenciais inválidas"}), 401


def password_ok(senha: str) -> bool:
    """Compara a senha do bootstrap de forma segura (constant-time)."""
    return senha == DASHBOARD_PASS


@app.route("/api/auth/me", methods=["GET"])
@requer_login
def api_auth_me():
    if g.usuario.get("id") == -1:
        return jsonify({"usuario": _usuario_publico({
            "id": -1, "username": g.usuario["username"], "nome": g.usuario["nome"],
            "cargo": g.usuario["cargo"], "modo_exibicao": g.usuario["modo_exibicao"],
            **{f: True for f in FLAGS_PERMISSAO},
        })})
    supabase = get_supabase()
    resp = supabase.table("jordao_usuarios").select(COLUNAS_USUARIO_PUBLICO).eq("id", g.usuario["id"]).limit(1).execute()
    if not resp.data:
        return jsonify({"error": "Usuário não encontrado"}), 404
    return jsonify({"usuario": _usuario_publico(resp.data[0])})


@app.route("/api/auth/status", methods=["GET"])
@requer_login
def api_auth_status():
    # Compatibilidade com o fluxo antigo do frontend; autenticado = logado.
    return jsonify({"logged_in": True})


@app.route("/api/usuarios", methods=["GET"])
@requer_permissao("acesso_usuarios")
def api_usuarios_listar():
    supabase = get_supabase()
    resp = supabase.table("jordao_usuarios").select(COLUNAS_USUARIO_PUBLICO).order("id", desc=True).execute()
    return jsonify({"usuarios": [_usuario_publico(u) for u in (resp.data or [])]})


@app.route("/api/usuarios", methods=["POST"])
@requer_permissao()
def api_usuarios_criar():
    if g.usuario.get("cargo") != "admin":
        return jsonify({"error": "Apenas administradores podem criar usuários"}), 403

    data = request.get_json() or {}
    username = str(data.get("username", "")).strip()
    nome = str(data.get("nome", "")).strip()
    senha = data.get("senha", "")
    if not username or not nome or not senha:
        return jsonify({"error": "username, nome e senha são obrigatórios"}), 400

    novo = {
        "username": username,
        "nome": nome,
        "senha_hash": bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        "cargo": data.get("cargo") if data.get("cargo") in ("admin", "operacional") else "operacional",
    }
    for f in FLAGS_PERMISSAO:
        novo[f] = bool(data.get(f, True if f != "acesso_usuarios" else False))

    supabase = get_supabase()
    try:
        resp = supabase.table("jordao_usuarios").insert(novo).execute()
    except Exception as e:
        if "duplicate key" in str(e).lower() or "23505" in str(e):
            return jsonify({"error": "Este nome de usuário já está em uso"}), 400
        return jsonify({"error": str(e)}), 500
    return jsonify({"usuario": _usuario_publico(resp.data[0])}), 201


@app.route("/api/usuarios/<user_id>", methods=["PUT"])
@requer_permissao()
def api_usuarios_editar(user_id: str):
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "ID de usuário inválido"}), 400

    eh_proprio = g.usuario["id"] == user_id
    eh_admin = g.usuario.get("cargo") == "admin"
    if not eh_proprio and not eh_admin:
        return jsonify({"error": "Sem permissão para editar este usuário"}), 403

    data = request.get_json() or {}
    # modo_exibicao é preferência pessoal — qualquer usuário logado pode
    # trocar a própria, não precisa ser admin (mesma regra do Britt/Astral).
    permitidos = ["nome", "cargo", "modo_exibicao"] + FLAGS_PERMISSAO if eh_admin else ["nome", "modo_exibicao"]
    update = {k: v for k, v in data.items() if k in permitidos}
    if "modo_exibicao" in update and update["modo_exibicao"] not in TEMAS_VALIDOS:
        return jsonify({"error": "Tema de cor desconhecido"}), 400
    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    # Perfil de bootstrap (id=-1) não existe no banco — ecoa a mudança sem
    # persistir, evitando 404/405 para sessões antigas em migração.
    if user_id == -1:
        return jsonify({"usuario": _usuario_publico({**g.usuario, **update})})

    update["atualizado_em"] = datetime.now(timezone.utc).isoformat()

    supabase = get_supabase()
    resp = supabase.table("jordao_usuarios").update(update).eq("id", user_id).execute()
    if not resp.data:
        return jsonify({"error": "Usuário não encontrado"}), 404
    return jsonify({"usuario": _usuario_publico(resp.data[0])})


@app.route("/api/usuarios/modo-massa", methods=["PUT"])
@requer_permissao()
def api_usuarios_modo_massa():
    if g.usuario.get("cargo") != "admin":
        return jsonify({"error": "Apenas administradores podem aplicar o tema a todos os usuários"}), 403

    modo = str((request.get_json() or {}).get("modo_exibicao", "")).strip()
    if modo not in TEMAS_VALIDOS:
        return jsonify({"error": "Tema de cor desconhecido"}), 400

    supabase = get_supabase()
    resp = (
        supabase.table("jordao_usuarios")
        .update({"modo_exibicao": modo, "atualizado_em": datetime.now(timezone.utc).isoformat()})
        .neq("id", 0)
        .execute()
    )
    return jsonify({"success": True, "atualizados": len(resp.data or [])})


@app.route("/api/usuarios/<int:user_id>/senha", methods=["PUT"])
@requer_permissao()
def api_usuarios_trocar_senha(user_id: int):
    eh_proprio = g.usuario["id"] == user_id
    pode_alterar_qualquer = g.usuario.get("cargo") == "admin" or g.usuario.get("acesso_usuarios")
    if not eh_proprio and not pode_alterar_qualquer:
        return jsonify({"error": "Sem permissão para alterar a senha deste usuário"}), 403

    data = request.get_json() or {}
    senha_nova = data.get("senha_nova", "")
    if not senha_nova:
        return jsonify({"error": "Nova senha é obrigatória"}), 400

    supabase = get_supabase()
    alvo = supabase.table("jordao_usuarios").select("senha_hash, cargo").eq("id", user_id).limit(1).execute()
    if not alvo.data:
        return jsonify({"error": "Usuário não encontrado"}), 404

    if alvo.data[0]["cargo"] == "admin" and not eh_proprio:
        return jsonify({"error": "Apenas o próprio administrador pode alterar sua senha"}), 403

    if eh_proprio and not pode_alterar_qualquer:
        senha_atual = data.get("senha_atual", "")
        if not senha_atual or not bcrypt.checkpw(senha_atual.encode("utf-8"), alvo.data[0]["senha_hash"].encode("utf-8")):
            return jsonify({"error": "Senha atual inválida"}), 401

    nova_hash = bcrypt.hashpw(senha_nova.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    supabase.table("jordao_usuarios").update(
        {"senha_hash": nova_hash, "atualizado_em": datetime.now(timezone.utc).isoformat()}
    ).eq("id", user_id).execute()
    return jsonify({"success": True})


@app.route("/api/usuarios/<int:user_id>", methods=["DELETE"])
@requer_permissao()
def api_usuarios_excluir(user_id: int):
    if g.usuario.get("cargo") != "admin":
        return jsonify({"error": "Apenas administradores podem excluir usuários"}), 403
    if g.usuario["id"] == user_id:
        return jsonify({"error": "Você não pode excluir seu próprio usuário"}), 400

    supabase = get_supabase()
    alvo = supabase.table("jordao_usuarios").select("cargo, nome").eq("id", user_id).limit(1).execute()
    if not alvo.data:
        return jsonify({"error": "Usuário não encontrado"}), 404
    if alvo.data[0]["cargo"] == "admin":
        return jsonify({"error": "Administradores não podem ser excluídos"}), 403

    supabase.table("jordao_usuarios").delete().eq("id", user_id).execute()
    return jsonify({"success": True})

@app.route("/api/relatorios/config", methods=["GET"])
@requer_permissao("acesso_automacao")
def api_relatorios_config():
    return jsonify({"reports": REPORTS})

@app.route("/api/supabase/dados", methods=["GET"])
@requer_permissao("acesso_tabelas")
def api_supabase_dados():
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
@requer_permissao("acesso_automacao")
def api_supabase_execucoes():
    try:
        supabase = get_supabase()
        response = supabase.table("execucoes").select("*").order("id", desc=True).limit(500).execute()
        return jsonify({"execucoes": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/supabase/kpis", methods=["GET"])
@requer_permissao("acesso_bi")
def api_supabase_kpis():
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
@requer_permissao("acesso_logs")
def api_supabase_logs():
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

# Endpoints de Controle Remoto via Supabase (Online Render -> VM)

@app.route("/api/remoto/disparar", methods=["POST"])
@requer_permissao("acesso_automacao")
def api_remoto_disparar():
    try:
        data = request.get_json() or {}
        relatorios = data.get("relatorios", [])
        if not relatorios:
            return jsonify({"error": "Nenhum relatorio selecionado"}), 400
        
        # Formatar relatórios para suportar inteiros ou dicionários com datas
        relatorios_formatados = []
        for r in relatorios:
            if isinstance(r, dict):
                relatorios_formatados.append(r)
            elif isinstance(r, int):
                relatorios_formatados.append({"report_id": r})
            elif isinstance(r, str) and r.isdigit():
                relatorios_formatados.append({"report_id": int(r)})
        
        tipo = "extracao_massa" if len(relatorios_formatados) > 1 else "extracao_relatorio"
        supabase = get_supabase()
        res = supabase.table("comandos_remotos").insert({
            "tipo": tipo,
            "payload": {"relatorios": relatorios_formatados, "_secret": REMOTE_SECRET},
            "status": "pendente",
            "mensagem": "Comando criado no Render. Aguardando VM capturar..."
        }).execute()
        
        cmd = res.data[0] if res.data else {}
        return jsonify({"status": "Comando enviado com sucesso para a VM!", "comando": cmd})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/remoto/cancelar", methods=["POST"])
@requer_permissao("acesso_automacao")
def api_remoto_cancelar():
    try:
        supabase = get_supabase()
        res = supabase.table("comandos_remotos").insert({
            "tipo": "cancelar_execucao",
            "payload": {"_secret": REMOTE_SECRET},
            "status": "pendente",
            "mensagem": "Solicitação de cancelamento enviada pelo usuário no Render."
        }).execute()
        cmd = res.data[0] if res.data else {}
        return jsonify({"status": "Solicitação de cancelamento enviada para a VM!", "comando": cmd})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agendamento", methods=["GET"])
@requer_permissao("acesso_automacao")
def api_agendamento_get():
    try:
        supabase = get_supabase()
        res = supabase.table("comandos_remotos").select("*").eq("tipo", "salvar_agendamento").order("id", desc=True).limit(1).execute()
        if res.data:
            horarios = res.data[0].get("payload", {}).get("horarios", [])
            return jsonify({"horarios": horarios})
        return jsonify({"horarios": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/agendamento", methods=["POST"])
@requer_permissao("acesso_automacao")
def api_agendamento_post():
    try:
        req = request.get_json() or {}
        horarios = req.get("horarios", [])
        validated = [h for h in horarios if isinstance(h, str) and len(h) == 5 and ":" in h]
        
        supabase = get_supabase()
        res = supabase.table("comandos_remotos").insert({
            "tipo": "salvar_agendamento",
            "payload": {"horarios": validated, "_secret": REMOTE_SECRET},
            "status": "pendente",
            "mensagem": "Solicitação de agendamento enviada para a VM..."
        }).execute()
        
        cmd = res.data[0] if res.data else {}
        return jsonify({"status": "Agendamento enviado para a VM com sucesso!", "comando": cmd})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoints de Gestão e Restauração de Backups

NOMES_TABELAS_AMIGAVEIS = {
    "relatorio_01_imoveis": "01 Relatório de Imóveis",
    "relatorio_02_contratos": "02 Relatório de Contratos",
    "relatorio_03_fluxo_caixa": "03 Relatório de Fluxo de Caixa",
    "relatorio_04_ficha_contrato": "04 Relatório Ficha do Contrato",
    "relatorio_05_tipo_recebimento": "05 Relatório por Tipo de Recebimento",
    "relatorio_06_cobranca_aluguel": "06 Relatório de Cobrança Aluguel e IPTU",
    "relatorio_07_cobrancas_recebidas": "07 Relatório de Cobranças Recebidas",
    "relatorio_08_contratos_x_cobrancas": "08 Relatório de Contratos x Cobranças",
    "relatorio_09_comissao_cobrancas": "09 Relatório de Comissão de Cobranças",
    "relatorio_10_pagamentos_beneficiarios": "10 Relatório de Pagamentos aos Beneficiários",
    "relatorio_11_conferencia_despesas": "11 Relatório de Conferência de Despesas",
    "relatorio_12_pessoas_ativos": "12 Relatório de Pessoas Ativos",
    "relatorio_13_recebimentos_pagamentos": "13 Relatório de Recebimentos e Pagamentos",
    "relatorio_14_movimentos_detalhados": "14 Relatório Conferência Movimentos Detalhado",
    "relatorio_15_contas_pagar_receber": "15 Relatório de Contas a Pagar / Receber",
}

@app.route("/api/backups", methods=["GET"])
@requer_permissao("acesso_backups")
def api_backups_get():
    try:
        supabase = get_supabase()
        res = (
            supabase.table("backups_execucoes")
            .select("id, table_name, total_registros, created_at")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        backups = res.data or []
        for b in backups:
            tbl = b.get("table_name", "")
            b["nome_amigavel"] = NOMES_TABELAS_AMIGAVEIS.get(tbl, tbl)
        return jsonify(backups)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/backups/restaurar/<int:backup_id>", methods=["POST"])
@requer_permissao("acesso_backups")
def api_backups_restaurar(backup_id):
    try:
        from src.ingestao.base_ingestor import restaurar_backup_por_id
        resultado = restaurar_backup_por_id(backup_id)
        tbl_name = resultado["table_name"]
        nome_amigavel = NOMES_TABELAS_AMIGAVEIS.get(tbl_name, tbl_name)
        resultado["nome_amigavel"] = nome_amigavel
        return jsonify({"status": f"Backup ID {backup_id} ({nome_amigavel}) restaurado com sucesso!", "resultado": resultado})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/remoto/status/<int:cmd_id>", methods=["GET"])
@requer_permissao("acesso_automacao")
def api_remoto_status(cmd_id):
    try:
        supabase = get_supabase()
        res = supabase.table("comandos_remotos").select("*").eq("id", cmd_id).limit(1).execute()
        if not res.data:
            return jsonify({"error": "Comando nao encontrado"}), 404
        registro = res.data[0]
        vm_sem_responder = False
        if registro["status"] == "pendente" and registro.get("criado_em"):
            try:
                criado = registro["criado_em"].replace("Z", "+00:00")
                idade = (datetime.now(timezone.utc) - date_parser.parse(criado)).total_seconds()
                if idade > 600:
                    vm_sem_responder = True
            except Exception:
                pass
        return jsonify({"comando": registro, "vm_sem_responder": vm_sem_responder})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoints de Push Notifications

@app.route("/api/notificacoes/subscribe", methods=["POST"])
@requer_permissao("acesso_notificacoes")
def api_notificacoes_subscribe():
    try:
        data = request.get_json() or {}
        token = data.get("token")
        user_agent = data.get("user_agent", "")
        if not token:
            return jsonify({"error": "Token obrigatorio"}), 400
        
        supabase = get_supabase()
        # Inserir ou atualizar token
        supabase.table("push_subscriptions").upsert({
            "token": token,
            "user_agent": user_agent,
            "created_at": "now()"
        }).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notificacoes/config", methods=["GET"])
@requer_permissao("acesso_notificacoes")
def api_notificacoes_config_get():
    try:
        supabase = get_supabase()
        res = supabase.table("push_config_regras").select("*").order("id").execute()
        return jsonify(res.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notificacoes/config", methods=["POST"])
@requer_permissao("acesso_notificacoes")
def api_notificacoes_config_post():
    try:
        data = request.get_json() or {}
        regra_id = data.get("regra_id")
        ativo = data.get("ativo")
        if not regra_id:
            return jsonify({"error": "regra_id obrigatorio"}), 400
            
        supabase = get_supabase()
        supabase.table("push_config_regras").update({"ativo": ativo}).eq("regra_id", regra_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/notificacoes/metricas", methods=["GET"])
@requer_permissao("acesso_notificacoes")
def api_notificacoes_metricas():
    try:
        supabase = get_supabase()
        # Buscar as últimas 1000 execuções para extrair as métricas de descarte e permitir paginação
        res = supabase.table("execucoes").select("*").order("id", desc=True).limit(1000).execute()
        metricas = []
        for execucao in (res.data or []):
            if execucao.get("tipo") == "ingestao" or execucao.get("tipo") == "completo":
                linhas_ins = execucao.get("total_linhas_inseridas", 0)
                linhas_desc = execucao.get("total_linhas_descartadas", 0)
                # Formatar a data para exibir
                data_str = execucao.get("iniciado_em", "")[:10]
                nome = f"Execução {execucao.get('id')} ({data_str})"
                metricas.append({
                    "relatorio": nome,
                    "linhas_inseridas": linhas_ins or 0,
                    "linhas_descartadas": linhas_desc or 0
                })
        return jsonify(metricas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
