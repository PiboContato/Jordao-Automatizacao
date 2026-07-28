# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE PESSOAS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE PESSOAS'").is_visible(timeout=2000):
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
    logger.info("Navegando para Relatório de Pessoas Ativos via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-pessoa"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def exportar_pdf(page: Page, data_inicio: str, data_fim: str = None) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório Pessoas Ativos)")
    contexto = obter_contexto_pagina(page)

    try:
        btn_gerar = contexto.locator("button:has-text('Gerar Relat')").first
        
        logger.info("Injetando script ninja para interceptar o PDF (Headless Safe)...")
        page.evaluate("""
            window.blobUrlRoubada = null;
            window.open = function(url) {
                window.blobUrlRoubada = url;
                return null; 
            };
        """)
        
        logger.info("Botão 'Gerar Relatório' acionado. Aguardando o PDF...")
        try:
            btn_gerar.click(timeout=5000)
        except Exception as e:
            logger.warning(f"Clique normal falhou (provável popup bloqueando a tela). Tentando via injeção de JS ninja: {e}")
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
            raise Exception("Não foi possível capturar a URL do PDF (Blob) no modo Headless. O tempo esgotou.")
            
        logger.info(f"URL do Blob capturada diretamente: {url_pdf}")
        
        logger.info("Transformando Blob em Base64 na página principal...")
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
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_12.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo PDF interceptado e salvo.")
        
        from src.utilitarios.conversor_pessoas_ativos import converter_para_excel
        from src.utils import gerar_nome_arquivo, mover_arquivo_para_destino
        
        try:
            logger.info("Iniciando conversão inteligente PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp, data_inicio)
            if caminho_excel:
                logger.info("Movendo o Excel gerado para a pasta de destino...")
                nome_excel = gerar_nome_arquivo(12, "12 Relatório de Pessoas Ativos", data_inicio, data_fim, ".xlsx")
                mover_arquivo_para_destino(caminho_excel, nome_excel)
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão do relatório 12: {e}")
            
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    # Não há preenchimento de filtros necessário conforme a regra de negócio
    return exportar_pdf(page, data_inicio, data_fim)
