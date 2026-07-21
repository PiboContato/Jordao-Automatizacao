# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresTipoRecebimento:
    MENU_LOCACAO = "text='Locação'"
    MENU_REL_CONFERENCIA = "text='Rel. Conferência'"
    MENU_TIPO_RECEBIMENTO = "text='Rel. por tipo de recebimento'"
    CHECKBOX_ATIVOS = "text='Apenas prop. com contrato ativos'"
    BTN_GERAR = "button:has-text('Gerar relatório'):visible"

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='REL. TIPOS DE RECEBIMENTOS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='REL. TIPOS DE RECEBIMENTOS'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    return page

def fechar_popup_imoalert(page: Page) -> None:
    """Função robusta para fechar o popup chato da Imoalert antes de navegar."""
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
    logger.info("Navegando para Relatório por tipo de recebimento via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-recebimento"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page) -> None:
    logger.info("Preenchendo os filtros do relatório: Apenas ativos")
    contexto = obter_contexto_pagina(page)
    
    try:
        page.wait_for_timeout(2000)
        # Força o clique no checkbox via JS para máxima estabilidade
        contexto.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('*'));
                const label = els.find(el => el.innerText && el.innerText.trim() === 'Apenas prop. com contrato ativos');
                if (label) { 
                    label.click();
                    const checkbox = label.querySelector('input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) { checkbox.checked = true; }
                } else {
                    // Fallback tenta achar direto o checkbox
                    const boxes = document.querySelectorAll('input[type="checkbox"]');
                    if(boxes.length > 0) { boxes[boxes.length-1].checked = true; }
                }
            }
        """)
        logger.info("Filtro 'Apenas prop. com contrato ativos' selecionado com sucesso.")
    except Exception as e:
        logger.error(f"Aviso ao clicar no filtro: {e}")
        
    page.wait_for_timeout(1000)

def exportar_excel(page: Page) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório Tipo Recebimento)")
    contexto = obter_contexto_pagina(page)

    try:
        btn_gerar = contexto.locator(SeletoresTipoRecebimento.BTN_GERAR).first
        
        # INJEÇÃO MESTRA (Modo Headless Seguro)
        # Diferente do rel. 04, este aqui já abre o PDF direto ao clicar em Gerar.
        # Então sequestramos o window.open ANTES de clicar!
        logger.info("Injetando script ninja para interceptar o PDF...")
        page.evaluate("""
            window.blobUrlRoubada = null;
            window.open = function(url) {
                window.blobUrlRoubada = url;
                return null; // Bloqueia a abertura de abas invisíveis
            };
        """)
        
        logger.info("Botão 'Gerar relatório' acionado. Aguardando o PDF...")
        btn_gerar.click(timeout=5000)
        
        url_pdf = page.evaluate("""
            new Promise((resolve) => {
                let t = 0;
                let check = setInterval(() => {
                    // 1. Tenta achar pelo roubo do window.open
                    if (window.blobUrlRoubada) { 
                        clearInterval(check); 
                        resolve(window.blobUrlRoubada); 
                    }
                    // 2. Tenta achar no DOM se foi injetado (igual ao rel. 04)
                    const links = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'));
                    if (links.length > 0) {
                        clearInterval(check); 
                        resolve(links[0].href || links[0].src);
                    }
                    if (t++ > 300) { // Espera até 30 segundos! (300 * 100ms)
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
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_05.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo PDF interceptado e salvo.")
        
        # --- BIFURCAÇÃO: TENTAR CONVERTER PARA EXCEL ---
        from src.utilitarios.conversor_recebimento import converter_para_excel
        from src.utils import mover_arquivo_para_destino
        from datetime import datetime
        try:
            logger.info("Iniciando conversão experimental PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp)
            if caminho_excel:
                logger.info("Movendo o Excel gerado para a pasta de destino...")
                data_hoje = datetime.now().strftime("%Y_%m_%d")
                nome_excel = f"05 Relatório por tipo de recebimento {data_hoje}.xlsx"
                mover_arquivo_para_destino(caminho_excel, nome_excel)
        except Exception as e:
            logger.error(f"Erro no módulo de conversão isolado: {e}")
        # -----------------------------------------------
        
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page)
    return exportar_excel(page)
