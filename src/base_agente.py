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
    BOTAO_LOGIN = 'button[type="submit"], input[type="submit"], button:has-text("Login")'


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

    logger.info("Verificando se há popup de alerta inicial (aguardando até 15s)...")
    try:
        alerta = page.locator("text='Alerta do sistema Imoalert!'").first
        alerta.wait_for(state="visible", timeout=15000)
        logger.info("Popup de alerta detectado! Tentando fechar...")
        
        try:
            # Injetamos um script direto no navegador para procurar todos os botões/links
            # e clicar à força no que tiver escrito "Fechar", ignorando qualquer barreira visual.
            fechou_via_js = page.evaluate("""
            () => {
                let els = Array.from(document.querySelectorAll('button, a, .btn'));
                let success = false;
                for (let el of els) {
                    if (el.innerText && el.innerText.trim().toLowerCase() === 'fechar') {
                        el.click();
                        success = true;
                    }
                }
                return success;
            }
            """)
            
            if fechou_via_js:
                logger.info("Botão Fechar clicado com sucesso via injeção de JS puro.")
            else:
                logger.warning("Botão Fechar não foi encontrado na página via JS.")
                page.keyboard.press("Escape")
                logger.info("Tentativa de fechar via tecla Escape enviada.")
                    
            # Tempo para aguardar a animação do modal desaparecendo
            page.wait_for_timeout(2000)
            
            # Validação Crítica: Garantir que o popup realmente sumiu
            if alerta.is_visible():
                raise Exception("FALHA CRÍTICA: O popup Imoalert não pôde ser fechado. Execução abortada para proteger a integridade dos passos seguintes.")
                
            logger.info("Popup fechado e validado com sucesso. Tela limpa para navegação.")
            
        except Exception as e:
            # Qualquer erro aqui deve ser fatal
            if "FALHA CRÍTICA" in str(e):
                raise e
            raise Exception(f"FALHA CRÍTICA ao lidar com o popup: {e}")
            
    except PlaywrightTimeoutError:
        logger.info("Nenhum popup bloqueante detectado.")
    except Exception as e:
        if "FALHA CRÍTICA" in str(e):
            raise e
        logger.warning(f"Erro inesperado na verificação do popup: {e}")


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

def processar_fila_em_massa(
    fila: list,
    status_robo: dict,
    on_browser_start: Callable = None,
    is_cancelled: Callable[[], bool] = None
) -> None:
    import importlib
    
    MAPA_EXTRATORES = {
        1: "src.relatorios.relatorio_imoveis",
        2: "src.relatorios.relatorio_contratos",
        3: "src.relatorios.relatorio_fluxo_caixa",
        4: "src.relatorios.relatorio_ficha_contrato",
        5: "src.relatorios.relatorio_tipo_recebimento",
        6: "src.relatorios.relatorio_cobranca_aluguel",
        7: "src.relatorios.relatorio_cobrancas_recebidas",
        8: "src.relatorios.relatorio_contratos_x_cobrancas",
        9: "src.relatorios.relatorio_comissao_cobrancas",
        10: "src.relatorios.relatorio_pagamentos_beneficiarios",
        11: "src.relatorios.relatorio_conferencia_despesas",
        12: "src.relatorios.relatorio_pessoas_ativos",
        13: "src.relatorios.relatorio_recebimentos_pagamentos",
        14: "src.relatorios.relatorio_movimentos_detalhados",
        15: "src.relatorios.relatorio_contas_pagar_receber"
    }

    try:
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

            tamanho_fila = len(fila)
            if tamanho_fila > 1:
                logger.info(f"INICIANDO SESSÃO ÚNICA PARA PROCESSAMENTO EM MASSA ({tamanho_fila} relatórios)")
            else:
                logger.info("INICIANDO SESSÃO ÚNICA PARA PROCESSAMENTO DE RELATÓRIO INDIVIDUAL")
            fazer_login(page)
            
            while len(fila) > 0:
                if is_cancelled and is_cancelled():
                    logger.warning("Fila cancelada pelo usuário durante o lote.")
                    break
                    
                item = fila.pop(0)
                report_id = item["report_id"]
                report_name = item.get("report_name", f"Relatório {report_id}")
                data_inicio = item.get("data_inicio")
                data_fim = item.get("data_fim")
                
                status_robo["relatorio_atual"] = report_id
                status_robo["tempo_inicio"] = time.time()
                status_robo["historico"][str(report_id)] = "rodando"
                
                logger.info(f">>> PROCESSANDO: {report_name} <<<")
                
                if report_id not in MAPA_EXTRATORES:
                    logger.error(f"Relatório não mapeado: {report_id}")
                    status_robo["historico"][str(report_id)] = "falha"
                    continue
                    
                modulo_caminho = MAPA_EXTRATORES[report_id]
                try:
                    modulo = importlib.import_module(modulo_caminho)
                    extrator = getattr(modulo, "extrair")
                    
                    sucesso_item = False
                    
                    for tentativa in range(1, TENTATIVAS_MAX + 1):
                        if is_cancelled and is_cancelled():
                            break
                        try:
                            arquivo_temp = extrator(page, data_inicio, data_fim)
                            
                            if arquivo_temp is None:
                                raise Exception("A função de extração retornou None.")
                                
                            if not validar_arquivo_excel(arquivo_temp):
                                raise Exception("Falha na validação de integridade do arquivo.")
                                
                            nome_arquivo = gerar_nome_arquivo(report_id, report_name, data_inicio, data_fim, arquivo_temp.suffix)
                            arquivo_final = mover_arquivo_para_destino(arquivo_temp, nome_arquivo)
                            logger.info(f"✅ EXPORTAÇÃO CONCLUÍDA: {arquivo_final.name}")
                            sucesso_item = True
                            break
                            
                        except PlaywrightError as pe:
                            logger.error(f"Tentativa {tentativa} falhou (PlaywrightError) no {report_name}: {pe}")
                            if "Target closed" in str(pe) or "Browser closed" in str(pe):
                                raise pe # Propaga falha crítica
                        except Exception as e:
                            logger.error(f"Tentativa {tentativa} falhou no {report_name}: {e}")
                            
                        if tentativa < TENTATIVAS_MAX:
                            logger.info("Recarregando a página e tentando novamente...")
                            page.goto(ASTRAL_URL, timeout=TIMEOUT_NAVEGACAO)
                            page.wait_for_timeout(3000)
                    
                    if sucesso_item:
                        status_robo["historico"][str(report_id)] = "sucesso"
                    else:
                        status_robo["historico"][str(report_id)] = "falha"
                        logger.error(f"Todas as tentativas falharam para {report_name}.")
                        
                except Exception as e_critico:
                    logger.error(f"Falha crítica no {report_name}: {e_critico}. Pulando para o próximo relatório.")
                    status_robo["historico"][str(report_id)] = "falha"
                    
                    
                finally:
                    if status_robo["tempo_inicio"] is not None:
                        status_robo["tempos_execucao"][str(report_id)] = int(time.time() - status_robo["tempo_inicio"])
                        status_robo["tempo_inicio"] = None
            
            logger.info("Finalizando Sessão Única e fechando o navegador.")
            browser.close()

            historico = status_robo.get("historico", {})
            sucessos = [rid for rid, st in historico.items() if st == "sucesso"]
            falhas = [rid for rid, st in historico.items() if st == "falha"]
            logger.info(f"RESUMO MASSA: {len(sucessos)} sucesso, {len(falhas)} falha de {len(historico)} total")
            if sucessos:
                logger.info(f"  Sucesso: IDs {sucessos}")
            if falhas:
                logger.warning(f"  Falha/pulados: IDs {falhas}")
            
    except Exception as e_global:
        logger.error(f"Erro global no processamento em massa: {e_global}")
    finally:
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass
