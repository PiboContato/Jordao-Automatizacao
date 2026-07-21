# -*- coding: utf-8 -*-
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.config import montar_url, TIMEOUT_NAVEGACAO, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresContratos:
    MENU_LOCACAO = "text=Locação"
    MENU_REL_DIVERSOS = "text=Rel. Diversos"
    MENU_REL_CONTRATOS = "text=Rel. Contratos"

def obter_contexto_pagina(page: Page):
    """Retorna o locator correto (página principal ou iframe) onde o formulário está."""
    try:
        # Tenta procurar pelo título para saber se achou a página certa (mesma lógica que imóveis, usando o título)
        if page.locator("text='RELATÓRIO DE CONTRATOS'").is_visible(timeout=2000):
            return page
    except:
        pass
        
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE CONTRATOS'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    
    # Se não validou ainda, assume a página principal
    return page

def navegar(page: Page) -> None:
    logger.info("Navegando para Relatório de Contratos via URL direta")
    try:
        page.goto(montar_url("rel-contrato"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page) -> None:
    logger.info("Preenchendo os filtros do relatório: Modelo 2 e Todos os contratos ativos")
    contexto = obter_contexto_pagina(page)
    
    try:
        # Passo 4: Marcar Modelo 2 (clicando diretamente no texto conforme orientação)
        modelo2_txt = contexto.locator("text='Modelo 2'").first
        modelo2_txt.click(timeout=5000)
        logger.info("Filtro Modelo 2 selecionado com sucesso.")
    except Exception as e:
        logger.warning(f"Falhou ao clicar no texto Modelo 2: {e}")
        
    page.wait_for_timeout(500)
    
    try:
        # Passo 5: Marcar Todos os contratos ativos (clicando diretamente no texto)
        ativos_txt = contexto.locator("text='Todos os contratos ativos'").first
        ativos_txt.click(timeout=5000)
        logger.info("Filtro Todos os contratos ativos selecionado com sucesso.")
    except Exception as e:
        logger.warning(f"Falhou ao clicar no texto Todos os contratos ativos: {e}")
            
    page.wait_for_timeout(1000)

def exportar_excel(page: Page) -> Path | None:
    logger.info("Iniciando exportação Excel (Relatório de Contratos)")
    contexto = obter_contexto_pagina(page)

    try:
        with page.expect_download(timeout=120000) as download_info:
            try:
                # Passo 6: Exportar para Excel
                btn = contexto.locator("button:has-text('Exportar para Excel'), a:has-text('Exportar para Excel')").first
                if btn.is_visible():
                    btn.click(timeout=5000)
                else:
                    raise Exception("Botão não está visível")
            except Exception as e:
                logger.warning(f"Falha ao clicar no botão pelo seletor, tentando via JS: {e}")
                js_code = """
                    () => {
                        let btns = document.querySelectorAll('button, a, div.btn');
                        for (let b of btns) {
                            if ((b.innerText || "").toLowerCase().includes('exportar para excel')) {
                                b.click(); return;
                            }
                        }
                    }
                """
                if hasattr(contexto, 'evaluate'):
                    contexto.evaluate(js_code)
                else:
                    contexto.locator(':root').evaluate(js_code)
                
        download = download_info.value
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / download.suggested_filename
        download.save_as(str(caminho_temp))

        logger.info(f"Download capturado: {download.suggested_filename} -> {caminho_temp}")
        return caminho_temp

    except PlaywrightTimeoutError:
        raise Exception("Timeout aguardando o download iniciar.")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    """Função principal de extração chamada pelo base_agente."""
    navegar(page)
    preencher_filtros(page)
    return exportar_excel(page)
