import os
import firebase_admin
from firebase_admin import credentials, messaging
from src.supabase_client import get_supabase_client
from src.logger import get_logger

logger = get_logger("PushService")

# Inicializa o Firebase Admin (singleton)
# ATENÇÃO: Requer o arquivo serviceAccountKey.json do Firebase na raiz
def init_firebase():
    if not firebase_admin._apps:
        try:
            key_path = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin inicializado com sucesso.")
            else:
                logger.warning(f"Arquivo de credenciais do Firebase ({key_path}) não encontrado. Pushes não serão enviados.")
        except Exception as e:
            logger.error(f"Erro ao inicializar Firebase Admin: {e}")

def enviar_notificacao_push(titulo: str, corpo: str, regra_necessaria: str = None):
    """
    Envia uma notificação push para todos os tokens cadastrados,
    desde que a regra `regra_necessaria` esteja ativa.
    Se `regra_necessaria` for None, envia sempre.
    """
    supabase = get_supabase_client()
    
    # 1. Checar se a regra permite o envio
    if regra_necessaria:
        try:
            res = supabase.table("push_config_regras").select("ativo").eq("regra_id", regra_necessaria).limit(1).execute()
            if res.data:
                is_ativo = res.data[0].get("ativo", False)
                if not is_ativo:
                    logger.info(f"Regra de push '{regra_necessaria}' está desativada. Notificação não enviada.")
                    return
        except Exception as e:
            logger.error(f"Erro ao verificar regra de push: {e}")
            
    # 2. Buscar tokens
    try:
        res = supabase.table("push_subscriptions").select("token").execute()
        tokens = [row["token"] for row in (res.data or []) if "token" in row]
    except Exception as e:
        logger.error(f"Erro ao buscar tokens no Supabase: {e}")
        return

    if not tokens:
        logger.info("Nenhum dispositivo cadastrado para receber Push.")
        return

    # 3. Enviar Push via Firebase
    init_firebase()
    if not firebase_admin._apps:
        return

    message = messaging.MulticastMessage(
        data={
            "title": titulo,
            "body": corpo,
            "tag": "jordao-automacao"
        },
        tokens=tokens
    )

    try:
        response = messaging.send_multicast(message)
        logger.info(f"Push enviado: {response.success_count} sucessos, {response.failure_count} falhas.")
    except Exception as e:
        logger.error(f"Falha ao enviar Push: {e}")
