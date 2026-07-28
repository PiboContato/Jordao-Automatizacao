# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresFichaContrato:
    MENU_LOCACAO = "text='Locação'"
    MENU_REL_DIVERSOS = "text='Rel. Diversos'"
    MENU_FICHA_CONTRATO = "text='Rel. Ficha do contrato'"
    RADIO_ATIVOS = "text='Ativos'"
    BTN_GERAR = "button:has-text('Gerar relatório'):visible"
    BTN_BAIXAR = "button:has-text('Baixar Relatório'):visible"

def obter_contexto_pagina(page: Page):
    """Retorna o locator correto (página principal ou iframe) onde o formulário está."""
    try:
        if page.locator("text='FICHA DO CONTRATO'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='FICHA DO CONTRATO'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    return page

def fechar_popup_imoalert(page: Page) -> None:
    """Função robusta para fechar o popup chato da Imoalert antes de navegar."""
    logger.info("Verificando se o popup da Imoalert está bloqueando a tela...")
    page.wait_for_timeout(2000)
    closed = False
    
    # 1. Tenta fechar no X
    for selector in ["button[aria-label*='close']", "button:has-text('×')", "button[class*='close']"]:
        try:
            page.locator(selector).first.click(timeout=1000)
            closed = True
            logger.info("Popup fechado no 'X'.")
            break
        except:
            pass
            
    # 2. Tenta fechar nos botões de texto
    if not closed:
        for txt in ["Ver depois", "Marcar como lido", "OK", "Fechar"]:
            try:
                page.locator(f"button:has-text('{txt}')").first.click(timeout=1000)
                closed = True
                logger.info(f"Popup fechado no botão '{txt}'.")
                break
            except:
                pass
                
    # 3. Força Bruta via JS
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
    logger.info("Navegando para Relatório Ficha do Contrato via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-fichacontrato"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page) -> None:
    logger.info("Preenchendo os filtros do relatório: Ativos")
    contexto = obter_contexto_pagina(page)
    
    try:
        page.wait_for_timeout(2000)
        # Clica via JS para garantir que o rádio seja marcado mesmo se houver div invisível
        contexto.evaluate("""
            () => {
                const els = Array.from(document.querySelectorAll('*'));
                const label = els.find(el => el.innerText && el.innerText.trim() === 'Ativos');
                if (label) { 
                    label.click(); 
                    const radio = label.querySelector('input[type="radio"]');
                    if(radio) radio.checked = true;
                }
            }
        """)
        logger.info("Filtro 'Ativos' selecionado com sucesso (via JS forçado).")
    except Exception as e:
        raise Exception(f"FALHA CRÍTICA: Falhou ao clicar no texto Ativos: {e}")
        
    page.wait_for_timeout(1000)

def exportar_excel(page: Page) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório Ficha do Contrato)")
    contexto = obter_contexto_pagina(page)

    try:
        # Passo 5: Clicar em Gerar relatório
        btn_gerar = contexto.locator("button:has-text('Gerar relatório'):visible").first
        btn_gerar.evaluate("node => node.click()")
        logger.info("Botão 'Gerar relatório' acionado. A página começou a carregar...")
        
        # ESTRATÉGIA MISTA (Sugerida pelo usuário):
        # 1. Respiro forçado de 5 segundos para a tela "entender" que está carregando 
        # e apagar eventuais botões antigos.
        logger.info("Pausa forçada de 5 segundos para o sistema iniciar o processamento...")
        page.wait_for_timeout(5000)
        
        # Passo 6: Monitorar ativamente o botão Baixar APARECER na tela
        logger.info("Monitorando a tela: Aguardando o botão 'Baixar Relatório' ficar pronto...")
        
        btn_baixar = contexto.locator("button:has-text('Baixar Relatório'):visible").first
        
        # 2. Inteligência do Playwright: ficar olhando a tela até 60s
        btn_baixar.wait_for(state="visible", timeout=60000)
        logger.info("O botão 'Baixar Relatório' APARECEU! O relatório está pronto.")
        
        # Estabilização extra: Garante que a tela de "Loading" cinza não esteja em cima do botão
        page.wait_for_timeout(2000)
        
        # Passo 7: Capturar o PDF
        logger.info("Injetando script ninja para capturar o Blob na raiz (Headless Safe)...")
        
        # A MÁGICA: Em vez de abrir uma nova aba (que o Chrome Headless odeia com PDFs),
        # nós achamos a URL do Blob que a própria página gerou quando o botão apareceu.
        url_pdf = page.evaluate("""
            () => {
                // Procura qualquer tag <a> ou <iframe> que tenha o blob
                const links = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'));
                if (links.length > 0) {
                    return links[0].href || links[0].src;
                }
                return null;
            }
        """)
        
        if not url_pdf:
            # Fallback supremo: interceptar window.open
            logger.info("Blob não encontrado no DOM. Sequestrando window.open e clicando...")
            page.evaluate("""
                window.blobUrlRoubada = null;
                window.open = function(url) {
                    window.blobUrlRoubada = url;
                    return null; // Bloqueia a aba real
                };
            """)
            btn_baixar.evaluate("node => node.click()")
            url_pdf = page.evaluate("""
                new Promise((resolve) => {
                    let t = 0;
                    let check = setInterval(() => {
                        if (window.blobUrlRoubada) { clearInterval(check); resolve(window.blobUrlRoubada); }
                        if (t++ > 50) { clearInterval(check); resolve(null); }
                    }, 100);
                })
            """)
            
        if not url_pdf:
            raise Exception("Não foi possível capturar a URL do PDF (Blob) no modo Headless.")
            
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
        
        # O script retorna algo como: 'data:application/pdf;base64,JVBERi0xLjQK...'
        import base64
        base64_data = pdf_base64_url.split(",")[1]
        pdf_bytes = base64.b64decode(base64_data)
        
        # Salvamos o arquivo sólido no computador
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo 'fantasma' materializado e salvo em PDF.")
        
        # --- BIFURCAÇÃO (VERSÃO 2.0) ---
        # Mantemos o PDF seguro e tentamos gerar o Excel de forma totalmente isolada.
        from src.utilitarios.conversor_ficha import converter_para_excel
        from src.utils import mover_arquivo_para_destino
        from datetime import datetime
        try:
            logger.info("Iniciando conversão experimental PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp)
            if caminho_excel:
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão isolado: {e}")
        # -------------------------------
        
        return caminho_temp

    except PlaywrightTimeoutError as pte:
        raise Exception(f"FALHA CRÍTICA: Tempo esgotado aguardando elemento na tela. Detalhes: {pte}")
    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    """Função principal de extração."""
    navegar(page)
    preencher_filtros(page)
    return exportar_excel(page)
