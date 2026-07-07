"""
base_agente.py — Motor base do robô Astral.

Responsável por:
- Inicializar o Playwright (modo headless/visual)
- Controlar as tentativas de repetição (retry e backoff)
- Efetuar o Login
- Orquestrar a chamada para os extratores específicos de cada relatório
"""

import time
import traceback
import asyncio
from pathlib import Path
from typing import Callable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError
)

from src.config import (
    ASTRAL_URL,
    ASTRAL_USUARIO,
    ASTRAL_SENHA,
    HEADLESS,
    TIMEOUT_NAVEGACAO,
    TENTATIVAS_MAX,
    ESPERA_ENTRE_TENTATIVAS,
)
from src.logger import logger
from src.utils import (
    gerar_nome_arquivo,
    mover_arquivo_para_destino,
    validar_arquivo_excel,
)

# Seletor global de login (só muda se o sistema principal mudar)
class SeletoresLogin:
    CAMPO_USUARIO = 'input[name="username"]'
    CAMPO_SENHA = 'input[name="password"]'
    BOTAO_LOGIN = 'input[type="submit"]'


def fazer_login(page: Page) -> None:
    """Realiza login padrão no sistema Astral."""
    logger.info(f"Acessando URL: {ASTRAL_URL}")

    try:
        page.goto(ASTRAL_URL, timeout=TIMEOUT_NAVEGACAO, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        raise Exception(f"Timeout ao carregar a página de login ({TIMEOUT_NAVEGACAO}ms).")



    try:
        page.wait_for_selector(SeletoresLogin.CAMPO_USUARIO, timeout=TIMEOUT_NAVEGACAO)
    except PlaywrightTimeoutError:
        raise Exception("Campo de usuário não encontrado na página de login.")

    logger.info("Preenchendo credenciais de login")
    page.fill(SeletoresLogin.CAMPO_USUARIO, ASTRAL_USUARIO)
    page.fill(SeletoresLogin.CAMPO_SENHA, ASTRAL_SENHA)
    page.click(SeletoresLogin.BOTAO_LOGIN)

    try:
        page.wait_for_url(lambda url: "login" not in url.lower(), timeout=TIMEOUT_NAVEGACAO)
        logger.info("Login realizado com sucesso")
    except PlaywrightTimeoutError:
        raise Exception("Timeout aguardando redirecionamento pós-login.")


def executar_com_retry(
    funcao_extracao: Callable[[Page, str, str], Path],
    report_id: int,
    report_name: str,
    data_inicio: str = None,
    data_fim: str = None,
    on_browser_start: Callable = None,
    is_cancelled: Callable[[], bool] = None
) -> bool:
    """
    Motor principal que gerencia as tentativas de extração.
    
    Args:
        funcao_extracao: Função que recebe (Page, data_inicio, data_fim) e retorna o Path do arquivo baixado.
        report_id: ID do relatório.
        report_name: Nome do relatório.
        data_inicio: str "YYYY-MM-DD"
        data_fim: str "YYYY-MM-DD"
        on_browser_start: Callback para permitir UI cancelar o navegador.
        is_cancelled: Função que checa se o usuário cancelou via painel.
    """

    for tentativa in range(1, TENTATIVAS_MAX + 1):
        if is_cancelled and is_cancelled():
            logger.warning("Execução cancelada antes de iniciar nova tentativa.")
            return False
            
        logger.info(f"=== Tentativa {tentativa}/{TENTATIVAS_MAX} ===")

        try:
            # Bugfix: Forçar um event loop completamente limpo para o Playwright Sync não conflitar com threads/Flask
            asyncio.set_event_loop(asyncio.new_event_loop())
            
            with sync_playwright() as p:
                browser: Browser = p.chromium.launch(headless=HEADLESS)
                
                if on_browser_start:
                    on_browser_start(browser)
                    
                context: BrowserContext = browser.new_context(
                    accept_downloads=True,
                    locale="pt-BR",
                )
                page: Page = context.new_page()
                page.set_default_timeout(TIMEOUT_NAVEGACAO)

                fazer_login(page)
                
                # CHAMA O EXTRATOR ESPECÍFICO DO RELATÓRIO
                arquivo_temp = funcao_extracao(page, data_inicio, data_fim)
                
                browser.close()

            if arquivo_temp is None:
                raise Exception("A função de extração retornou None sem lançar exceção.")

            if not validar_arquivo_excel(arquivo_temp):
                raise Exception(f"Arquivo baixado falhou na validação de integridade: {arquivo_temp}")

            nome_arquivo = gerar_nome_arquivo(report_id, report_name, data_inicio, data_fim, arquivo_temp.suffix)
            arquivo_final = mover_arquivo_para_destino(arquivo_temp, nome_arquivo)
            caminho_absoluto = arquivo_final.absolute()
            logger.info("==================================================")
            logger.info("✅ EXPORTAÇÃO CONCLUÍDA COM SUCESSO!")
            logger.info(f"📁 ARQUIVO SALVO EM: {caminho_absoluto}")
            logger.info("==================================================")
            return True

        except PlaywrightError as pe:
            if is_cancelled and is_cancelled():
                logger.error("Execução CANCELADA pelo usuário (Interrompida).")
                return False
            if "Target closed" in str(pe) or "Browser closed" in str(pe):
                logger.error("Navegador fechado inesperadamente.")
                return False
            else:
                erro_detalhe = traceback.format_exc()
                logger.error(f"Tentativa {tentativa} falhou (PlaywrightError): {pe}\n{erro_detalhe}")
                _aguardar_tentativa(tentativa, is_cancelled)
        except Exception as e:
            if is_cancelled and is_cancelled():
                logger.error("Execução CANCELADA pelo usuário (Interrompida).")
                return False
                
            erro_detalhe = traceback.format_exc()
            logger.error(f"Tentativa {tentativa} falhou: {e}\n{erro_detalhe}")
            _aguardar_tentativa(tentativa, is_cancelled)
        finally:
            # Bugfix: Playwright sync_playwright() deixa o event loop preso na thread atual.
            # Ao executar em bloco (vários relatórios seguidos na mesma thread), 
            # ele crashea alegando já estar dentro do asyncio loop.
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

    return False


def _aguardar_tentativa(tentativa: int, is_cancelled: Callable[[], bool]) -> None:
    if tentativa < TENTATIVAS_MAX:
        espera = ESPERA_ENTRE_TENTATIVAS * tentativa
        logger.info(f"Aguardando {espera}s antes da próxima tentativa...")
        for _ in range(espera):
            if is_cancelled and is_cancelled():
                logger.error("Execução CANCELADA pelo usuário durante a espera.")
                return
            time.sleep(1)
    else:
        logger.critical("Todas as tentativas esgotadas. Disparando alerta de falha.")
        from src.alertas import alertar_falha
        alertar_falha(etapa="fluxo_completo", detalhes="Todas tentativas falharam.")
