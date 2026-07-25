"""
Script para limpar todos os dados antigos (estrutura velha) do relatorio_07 do Supabase
e re-ingeri-los a partir do Excel já gerado pelo conversor corrigido.
Execute: python limpar_e_reingerir_07.py
"""
import sys
import os
sys.path.insert(0, '.')

from pathlib import Path
from src.supabase_client import get_supabase
from src.logger import logger

def limpar_tabela_07():
    supabase = get_supabase()
    logger.info("Limpando TODOS os registros antigos da tabela relatorio_07_cobrancas_recebidas...")
    
    # Busca todos os IDs existentes
    res = supabase.table("relatorio_07_cobrancas_recebidas").select("id").execute()
    ids = [r["id"] for r in res.data]
    logger.info(f"Total de registros a remover: {len(ids)}")
    
    if ids:
        # Deleta em lotes de 50
        for i in range(0, len(ids), 50):
            lote_ids = ids[i:i+50]
            supabase.table("relatorio_07_cobrancas_recebidas").delete().in_("id", lote_ids).execute()
            logger.info(f"Deletados registros {i+1} a {i+len(lote_ids)}...")
    
    logger.info("Tabela limpa com sucesso!")

if __name__ == "__main__":
    limpar_tabela_07()
    logger.info("Agora rode o Relatório 07 pelo painel para reinserir com a estrutura nova (Competência = 06/2026).")
