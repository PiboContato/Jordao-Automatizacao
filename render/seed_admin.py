"""
seed_admin.py — Cria/atualiza o usuário administrador inicial do painel Jordão.

Uso (no Render ou local, com SUPABASE_URL/SUPABASE_KEY no ambiente):
    python seed_admin.py
    JORDAO_ADMIN_USER=admin JORDAO_ADMIN_PASS=sua_senha python seed_admin.py

Padrões: usuario "Marcio Faro"; senha de JORDAO_ADMIN_PASS ou DASHBOARD_PASS
(fallback do .env antigo). Senha sempre gravada com hash bcrypt.
"""

import os

import bcrypt
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
TABELA = "jordao_usuarios"

FLAGS_POR_PADRAO = {
    "acesso_automacao": True,
    "acesso_bi": True,
    "acesso_tabelas": True,
    "acesso_auditoria": True,
    "acesso_backups": True,
    "acesso_logs": True,
    "acesso_notificacoes": True,
    "acesso_usuarios": True,
}


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    username = os.getenv("JORDAO_ADMIN_USER", "Marcio Faro").strip()
    senha = os.getenv("JORDAO_ADMIN_PASS") or os.getenv("DASHBOARD_PASS") or "admin"
    if not senha:
        raise SystemExit("Defina JORDAO_ADMIN_PASS (ou DASHBOARD_PASS) para o admin inicial.")

    nome = os.getenv("JORDAO_ADMIN_NOME", "Marcio Faro").strip()
    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Upsert manual: busca por username e insere/atualiza.
    resp = supabase.table(TABELA).select("id").ilike("username", username).limit(1).execute()
    registro = {
        "username": username,
        "nome": nome,
        "senha_hash": senha_hash,
        "cargo": "admin",
        "modo_exibicao": "colorido",
        **FLAGS_POR_PADRAO,
    }

    if resp.data:
        supabase.table(TABELA).update(registro).eq("id", resp.data[0]["id"]).execute()
        print(f"Admin '{username}' atualizado (id={resp.data[0]['id']}).")
    else:
        novo = supabase.table(TABELA).insert(registro).execute()
        print(f"Admin '{username}' criado (id={novo.data[0]['id']}).")


if __name__ == "__main__":
    main()
