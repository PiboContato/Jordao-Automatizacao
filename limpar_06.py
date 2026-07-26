import sys
sys.path.insert(0, '.')
from src.supabase_client import get_supabase
from src.logger import logger

def limpar_tabela_06():
    logger.info("Limpando a tabela relatorio_06_cobranca_aluguel...")
    supabase = get_supabase()
    # Apenas como precaução, limpa tudo para re-ingerir limpo
    res = supabase.table("relatorio_06_cobranca_aluguel").select("id").execute()
    ids = [r['id'] for r in res.data]
    if not ids:
        logger.info("Tabela já está vazia.")
        return
        
    # Limpa em lotes de 50
    for i in range(0, len(ids), 50):
        lote_ids = ids[i:i+50]
        supabase.table("relatorio_06_cobranca_aluguel").delete().in_("id", lote_ids).execute()
        logger.info(f"Deletados {len(lote_ids)} registros...")
        
    logger.info("Tabela limpa com sucesso!")

if __name__ == '__main__':
    limpar_tabela_06()
