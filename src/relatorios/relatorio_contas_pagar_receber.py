# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='Gerar Relatório'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='Gerar Relatório'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    return page

def fechar_popup_imoalert(page: Page) -> None:
    logger.info("Verificando popup...")
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
    page.wait_for_timeout(1000)

def navegar(page: Page) -> None:
    logger.info("Navegando para Contas a Pagar / Receber")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("caixa-reltransacoes"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_datas(page: Page, data_inicio: str, data_fim: str) -> None:
    # Formatar datas para DD/MM/YYYY se não estiverem
    if '-' in data_inicio:
        ano, mes, dia = data_inicio.split('-')
        data_inicio = f"{dia}/{mes}/{ano}"
    if data_fim and '-' in data_fim:
        ano, mes, dia = data_fim.split('-')
        data_fim = f"{dia}/{mes}/{ano}"
        
    contexto = obter_contexto_pagina(page)
    
    try:
        # Tenta por placeholder ou input adjacente
        input_inicio = contexto.locator("xpath=(//*[contains(text(), 'Período inicial')]//following::input)[1]")
        input_inicio.click(timeout=3000)
        input_inicio.clear()
        input_inicio.press_sequentially(data_inicio, delay=50)
        page.wait_for_timeout(500)
        
        if data_fim:
            input_fim = contexto.locator("xpath=(//*[contains(text(), 'Período Final') or contains(text(), 'Período final')]//following::input)[1]")
            input_fim.click(timeout=3000)
            input_fim.clear()
            input_fim.press_sequentially(data_fim, delay=50)
            page.wait_for_timeout(500)
            
    except Exception as e:
        logger.warning(f"Aviso ao preencher datas (Relatório 15): {e}")

def exportar_pdf(page: Page, data_inicio: str, data_fim: str = None) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório 15)")
    contexto = obter_contexto_pagina(page)

    try:
        fechar_popup_imoalert(page)
        contexto = obter_contexto_pagina(page)
        btn_gerar = contexto.locator("button:has-text('Gerar Relat')").first
        
        logger.info("Injetando script ninja para interceptar o PDF (Headless Safe)...")
        page.evaluate("""
            window.blobUrlRoubada = null;
            window.open = function(url) {
                window.blobUrlRoubada = url;
                return null; 
            };
        """)
        
        try:
            btn_gerar.click(timeout=5000)
        except:
            js_code = """
                () => {
                    let btns = document.querySelectorAll('button, a, div.btn');
                    for (let b of btns) {
                        if ((b.innerText || "").toLowerCase().includes('gerar relat')) {
                            b.click(); return;
                        }
                    }
                }
            """
            if hasattr(contexto, 'evaluate'):
                contexto.evaluate(js_code)
            else:
                contexto.locator(':root').evaluate(js_code)
        
        url_pdf = page.evaluate("""
            new Promise((resolve) => {
                let t = 0;
                let check = setInterval(() => {
                    if (window.blobUrlRoubada) { 
                        clearInterval(check); 
                        resolve(window.blobUrlRoubada); 
                    }
                    const links = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'));
                    if (links.length > 0) {
                        clearInterval(check); 
                        resolve(links[0].href || links[0].src);
                    }
                    if (t++ > 300) { 
                        clearInterval(check); 
                        resolve(null); 
                    }
                }, 100);
            })
        """)
        
        if not url_pdf:
            raise Exception("Não foi possível capturar a URL do PDF (Blob).")
            
        pdf_base64_url = page.evaluate("""
            async (blobUrl) => {
                const response = await fetch(blobUrl);
                const blob = await response.blob();
                return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });
            }
        """, url_pdf)
        
        import base64
        base64_data = pdf_base64_url.split(",")[1]
        pdf_bytes = base64.b64decode(base64_data)
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_15.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo PDF interceptado.")
        
        from src.utilitarios.conversor_contas_pagar_receber import converter_para_excel
        from src.utils import gerar_nome_arquivo, mover_arquivo_para_destino
        
        try:
            logger.info("Iniciando conversão PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp)
            if caminho_excel:
                logger.info("Movendo o Excel gerado...")
                nome_excel = gerar_nome_arquivo(15, "15 Relatório de Contas a Pagar / Receber", data_inicio, data_fim, ".xlsx")
                mover_arquivo_para_destino(caminho_excel, nome_excel)
        except Exception as e:
            logger.error(f"Erro no módulo de conversão do relatório 15: {e}")
            
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_datas(page, data_inicio, data_fim)
    return exportar_pdf(page, data_inicio, data_fim)
