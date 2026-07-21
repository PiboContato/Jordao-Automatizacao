# -*- coding: utf-8 -*-
import time
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, TIMEOUT_NAVEGACAO, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresFluxoCaixa:
    MENU_CAIXA = "text='Caixa'"
    MENU_REL_CAIXA = "text='Relatórios Caixa'"
    MENU_REL_FLUXO_CAIXA = "text='Rel. Fluxo Caixa'"

def obter_contexto_pagina(page: Page):
    """Retorna o locator correto (página principal ou iframe) onde o formulário está."""
    try:
        if page.locator("text='RELATÓRIO DE FLUXO DE CAIXA'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE FLUXO DE CAIXA'").is_visible(timeout=2000):
            return iframe
    except:
        pass
    return page

def navegar(page: Page) -> None:
    logger.info("Navegando para Relatório de Fluxo de Caixa via URL direta")
    try:
        page.goto(montar_url("rel-fluxo-caixa"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page, data_inicio: str, data_fim: str) -> None:
    logger.info(f"Preenchendo os filtros do relatório: Período ({data_inicio} até {data_fim})")
    contexto = obter_contexto_pagina(page)
    
    try:
        # Passo 4: Marcar Período (clicando diretamente no texto)
        periodo_txt = contexto.locator("text='Período'").first
        periodo_txt.click(timeout=5000)
        logger.info("Filtro Período selecionado com sucesso.")
    except Exception as e:
        logger.warning(f"Falhou ao clicar no texto Período: {e}")
        
    page.wait_for_timeout(500)
    
    if not data_inicio or not data_fim:
        raise Exception("FALHA CRÍTICA: Data de início e data de fim são obrigatórias para o Relatório de Fluxo de Caixa.")
        
    # Formatação de datas
    # Se o input for tipo "date", o playwright exige YYYY-MM-DD (que já é o padrão recebido).
    # Se for uma máscara customizada de texto, precisamos preencher como DD/MM/YYYY.
    # Vamos converter a data YYYY-MM-DD para DDMMYYYY e DD/MM/YYYY para garantir
    parts_i = data_inicio.split('-')
    parts_f = data_fim.split('-')
    data_inicio_br = f"{parts_i[2]}{parts_i[1]}{parts_i[0]}" # ddmmyyyy
    data_fim_br = f"{parts_f[2]}{parts_f[1]}{parts_f[0]}"    # ddmmyyyy
    
    try:
        # Passo 5: Preencher Data Inicial e Data Final
        # Conforme analisado nas imagens, os campos são inputs de data nativos do navegador
        # A interface provavelmente não liga a <label> ao <input> com o atributo 'for',
        # o que faz o get_by_label nativo falhar por não achar a conexão.
        # Vamos usar um XPath robusto que diz: "Ache o texto 'Data inicial' e pegue o primeiro input logo depois dele"
        input_inicio = contexto.locator("xpath=(//*[contains(text(), 'Data inicial')]//following::input)[1]")
        input_fim = contexto.locator("xpath=(//*[contains(text(), 'Data final')]//following::input)[1]")
        
        # Limpar e preencher Data Início
        input_inicio.click(timeout=5000)
        input_inicio.clear()
        # Se for type="date", fill exige YYYY-MM-DD. Se for texto com máscara DD/MM/YYYY, o fill limpo de YYYY-MM-DD pode falhar
        # Para ser seguro e simples: digitamos o formato brasileiro (DDMMYYYY) como se o usuário estivesse digitando.
        input_inicio.press_sequentially(data_inicio_br, delay=50)
        
        # Limpar e preencher Data Fim
        input_fim.click(timeout=5000)
        input_fim.clear()
        input_fim.press_sequentially(data_fim_br, delay=50)
        
        logger.info("Datas preenchidas com sucesso.")
            
    except Exception as e:
        raise Exception(f"FALHA CRÍTICA: Não foi possível preencher as datas no relatório de Fluxo de Caixa. Erro: {e}")
            
    page.wait_for_timeout(1000)
    
    try:
        # Passo 5.1: Selecionar a Carteira (obrigatório para habilitar o botão de Excel)
        logger.info("Selecionando a carteira (Ativa)...")
        
        # 1. Clicar para abrir o dropdown da Carteira
        caixa_carteira = contexto.locator("text='Selecionar carteiras'").first
        if caixa_carteira.is_visible(timeout=3000):
            caixa_carteira.click()
        else:
            contexto.locator("xpath=(//*[contains(text(), 'Carteira')]//following::div)[1]").click()
            
        # 2. Como a digitação de filtro não funciona, vamos usar um ataque direto no elemento da lista.
        # Componentes complexos (como selects do Angular/React) muitas vezes ignoram um simples .click()
        # Eles precisam que o mouse "pressione" (mousedown) e "solte" (mouseup) para registrar a escolha.
        sucesso_clique = page.evaluate("""
            () => {
                // Procura todos os elementos na tela
                let elements = Array.from(document.querySelectorAll('*'));
                // Filtra os que estão visíveis e contêm '(Ativa)'
                let targets = elements.filter(el => 
                    el.innerText && 
                    el.innerText.includes('(Ativa)') && 
                    el.offsetParent !== null && // está visível
                    el.children.length === 0 // pega o texto lá no fundo da árvore (o elemento mais interno)
                );
                
                if (targets.length > 0) {
                    // Pega o último (geralmente o que acabou de abrir no popup)
                    let target = targets[targets.length - 1];
                    // Tenta subir para a linha completa (li ou div option)
                    let clickable = target.closest('li') || target.closest('div[class*="option"]') || target;
                    
                    clickable.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, view: window}));
                    clickable.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, view: window}));
                    clickable.click();
                    return true;
                }
                return false;
            }
        """)
        
        if sucesso_clique:
            logger.info("Carteira selecionada com sucesso via JS (mousedown/click).")
        else:
            logger.warning("Não encontrou o elemento (Ativa) para clicar via JS.")
    except Exception as e:
        logger.warning(f"Aviso: Não foi possível selecionar a carteira. O botão de Excel pode não habilitar. Erro: {e}")
        
    page.wait_for_timeout(1000)

def exportar_excel(page: Page) -> Path | None:
    logger.info("Iniciando exportação Excel (Relatório de Fluxo de Caixa)")
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
    """Função principal de extração."""
    navegar(page)
    preencher_filtros(page, data_inicio, data_fim)
    return exportar_excel(page)
