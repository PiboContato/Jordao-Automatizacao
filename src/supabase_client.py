from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.logger import logger

_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Conexão com Supabase estabelecida")
    return _supabase

def testar_conexao() -> bool:
    try:
        client = get_supabase()
        client.table("execucoes").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Conexão com Supabase falhou: {e}")
        return False

def reset_conexao() -> None:
    global _supabase
    _supabase = None
    logger.info("Conexão com Supabase resetada")
