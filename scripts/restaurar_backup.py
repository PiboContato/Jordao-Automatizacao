"""
restaurar_backup.py — Restaura dados a partir de backups_execucoes no Supabase.

Uso:
    python scripts/restaurar_backup.py --tabela relatorio_01_imoveis
    python scripts/restaurar_backup.py --tabela relatorio_01_imoveis --exportar backup.json
    python scripts/restaurar_backup.py --listar
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.supabase_client import get_supabase
from src.ingestao.base_ingestor import TABELA_BACKUPS


def listar_backups():
    """Lista todos os backups disponíveis no Supabase."""
    supabase = get_supabase()
    resp = (
        supabase.table(TABELA_BACKUPS)
        .select("id, table_name, total_registros, created_at")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not resp.data:
        print("Nenhum backup encontrado.")
        return

    print(f"\n{'ID':>5} | {'Tabela':<35} | {'Registros':>10} | {'Data':<20}")
    print("-" * 80)
    for b in resp.data:
        print(
            f"{b['id']:>5} | {b['table_name']:<35} | "
            f"{b['total_registros']:>10} | {b['created_at'][:19]}"
        )
    print()


def restaurar_backup(table_name: str, exportar: str = None):
    """Restaura os dados de um backup para a tabela original."""
    supabase = get_supabase()

    resp = (
        supabase.table(TABELA_BACKUPS)
        .select("id, dados, total_registros, created_at")
        .eq("table_name", table_name)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        print(f"Nenhum backup encontrado para {table_name}.")
        return

    backup = resp.data[0]
    dados = backup["dados"]
    total = backup["total_registros"]
    data_backup = backup["created_at"][:19]

    print(f"\nBackup encontrado:")
    print(f"  Tabela: {table_name}")
    print(f"  Registros: {total}")
    print(f"  Data do backup: {data_backup}")

    if exportar:
        caminho = Path(exportar)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        print(f"  Exportado para: {caminho} ({caminho.stat().st_size:,} bytes)")
        return

    confirmacao = input(f"\nConfirmar restauração de {total} registros para {table_name}? (s/N): ")
    if confirmacao.lower() != "s":
        print("Restauração cancelada.")
        return

    print(f"Limpando tabela {table_name}...")
    supabase.table(table_name).delete().gte("id", 0).execute()

    print(f"Inserindo {total} registros...")
    lote = []
    inseridos = 0
    for reg in dados:
        lote.append({
            "dados": reg.get("dados", {}),
            "data_extracao": reg.get("data_extracao", ""),
        })
        if len(lote) >= 100:
            supabase.table(table_name).insert(lote).execute()
            inseridos += len(lote)
            lote = []

    if lote:
        supabase.table(table_name).insert(lote).execute()
        inseridos += len(lote)

    print(f"Restauração concluída: {inseridos} registros inseridos em {table_name}")


def main():
    parser = argparse.ArgumentParser(description="Restaurar backup do Supabase")
    parser.add_argument("--listar", action="store_true", help="Listar backups disponíveis")
    parser.add_argument("--tabela", help="Nome da tabela para restaurar")
    parser.add_argument("--exportar", help="Exportar backup para arquivo JSON (sem restaurar)")
    args = parser.parse_args()

    if args.listar:
        listar_backups()
    elif args.tabela:
        restaurar_backup(args.tabela, args.exportar)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
