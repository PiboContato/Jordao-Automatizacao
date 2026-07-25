from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from src.logger import logger
import time

_supabase: Client | None = None

MAX_TENTATIVAS_CONEXAO = 3
ESPERA_RECONEXAO = 5

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Conexão com Supabase estabelecida")
    return _supabase

def reset_conexao() -> None:
    global _supabase
    _supabase = None
    logger.info("Conexão com Supabase resetada")

def testar_conexao() -> bool:
    try:
        client = get_supabase()
        client.table("execucoes").select("id").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Conexão com Supabase falhou: {e}")
        reset_conexao()
        return False

def executar_com_retry(operacao, descricao: str = "operação"):
    """Executa uma operação no Supabase com retry e re-conexão automática.

    Args:
        operacao: callable que recebe (supabase_client) e retorna o resultado
        descricao: nome descritivo da operação para logs

    Returns:
        resultado da operação

    Raises:
        Exception: se todas as tentativas falharem
    """
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS_CONEXAO + 1):
        try:
            supabase = get_supabase()
            return operacao(supabase)
        except Exception as e:
            ultimo_erro = e
            logger.warning(
                f"Tentativa {tentativa}/{MAX_TENTATIVAS_CONEXAO} falhou para {descricao}: {e}"
            )
            if tentativa < MAX_TENTATIVAS_CONEXAO:
                reset_conexao()
                time.sleep(ESPERA_RECONEXAO)

    raise RuntimeError(
        f"Todas as {MAX_TENTATIVAS_CONEXAO} tentativas falharam para {descricao}: {ultimo_erro}"
    )
