# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE COMISSÃO DAS COBRANÇAS RECEBIDAS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE COMISSÃO DAS COBRANÇAS RECEBIDAS'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    return page

def fechar_popup_imoalert(page: Page) -> None:
    logger.info("Verificando se o popup da Imoalert está bloqueando a tela...")
    page.wait_for_timeout(2000)
    closed = False
    
    for selector in ["button[aria-label*='close']", "button:has-text('×')", "button[class*='close']"]:
        try:
            page.locator(selector).first.click(timeout=1000)
            closed = True
            break
        except:
            pass
            
    if not closed:
        for txt in ["Ver depois", "Marcar como lido", "OK", "Fechar"]:
            try:
                page.locator(f"button:has-text('{txt}')").first.click(timeout=1000)
                closed = True
                break
            except:
                pass
                
    if not closed:
        try:
            page.evaluate("""
                () => {
                    const modal = document.getElementById('modalAlerta');
                    if (modal) { modal.remove(); }
                    const overlay = document.querySelector('.modal-backdrop');
                    if (overlay) { overlay.remove(); }
                }
            """)
        except:
            pass
    page.wait_for_timeout(1000)

def navegar(page: Page) -> None:
    logger.info("Navegando para 09 Relatório de Comissão das Cobranças Recebidas via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-comcobrec"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page, data_inicio: str, data_fim: str) -> None:
    logger.info(f"Preenchendo os filtros do relatório: Inicio {data_inicio} até Fim {data_fim}")
    contexto = obter_contexto_pagina(page)
    
    page.wait_for_timeout(1000)
    
    try:
        # Garantir que a opção "Por data de pagamento" esteja marcada
        logger.info("Selecionando filtro 'Por data de pagamento'")
        radio_pagamento = contexto.locator("text='Por data de pagamento'").first
        if radio_pagamento.is_visible(timeout=3000):
            radio_pagamento.click()
            page.wait_for_timeout(500)
    except Exception as e:
        logger.warning(f"Aviso ao tentar marcar radio 'Por data de pagamento': {e}")
        
    if not data_inicio or not data_fim:
        raise Exception("FALHA CRÍTICA: Data de início e data de fim são obrigatórias.")
        
    parts_i = data_inicio.split('-')
    parts_f = data_fim.split('-')
    data_inicio_br = f"{parts_i[2]}{parts_i[1]}{parts_i[0]}" # ddmmyyyy
    data_fim_br = f"{parts_f[2]}{parts_f[1]}{parts_f[0]}"    # ddmmyyyy
    
    try:
        # O print tem "Data incio" e "Data fim"
        input_inicio = contexto.locator("xpath=(//*[contains(text(), 'Data incio') or contains(text(), 'Data inicio') or contains(text(), 'Data início')]//following::input)[1]")
        input_fim = contexto.locator("xpath=(//*[contains(text(), 'Data fim')]//following::input)[1]")
        
        input_inicio.click(timeout=5000)
        input_inicio.clear()
        input_inicio.press_sequentially(data_inicio_br, delay=50)
        
        input_fim.click(timeout=5000)
        input_fim.clear()
        input_fim.press_sequentially(data_fim_br, delay=50)
        
        logger.info("Datas preenchidas com sucesso.")
    except Exception as e:
        raise Exception(f"FALHA CRÍTICA: Não foi possível preencher as datas. Erro: {e}")
        
    page.wait_for_timeout(1000)

def exportar_pdf(page: Page, data_inicio: str, data_fim: str) -> Path | None:
    logger.info("Iniciando geração do PDF (Rel. 09)")
    contexto = obter_contexto_pagina(page)

    try:
        fechar_popup_imoalert(page)
        contexto = obter_contexto_pagina(page)
        btn_gerar = contexto.locator("button:has-text('Gerar Relatório'):visible").first

        from src.utilitarios.blob_interceptor import gerar_e_capturar_pdf
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_09.pdf"

        if not gerar_e_capturar_pdf(page, contexto, btn_gerar, caminho_temp, timeout_blob_s=90):
            raise Exception("Não foi possível capturar a URL do PDF (Blob) no modo Headless.")

        from src.utilitarios.conversor_comissao_cobrancas import converter_para_excel as converter_rel_09
        from src.utils import mover_arquivo_para_destino, gerar_nome_arquivo
        try:
            logger.info("Chamando o conversor para Excel do rel. 09...")
            caminho_excel = converter_rel_09(caminho_temp)
            if caminho_excel:
                logger.info("Movendo o Excel gerado para a pasta de destino...")
                nome_excel = gerar_nome_arquivo(9, "09 Relatório de Comissão das Cobranças Recebidas", data_inicio, data_fim, ".xlsx")
                mover_arquivo_para_destino(caminho_excel, nome_excel)
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão: {e}")

        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page, data_inicio, data_fim)
    return exportar_pdf(page, data_inicio, data_fim)
