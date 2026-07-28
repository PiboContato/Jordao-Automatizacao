# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresCobranca:
    MENU_LOCACAO = "text='Locação'"
    MENU_PROCESSO_FINANCEIRO = "text='Rel. Processo financeiro'"
    MENU_COBRANCA = "text='Rel. Cobranças Aluguel e IPTU'"
    BTN_GERAR = "button:has-text('Gerar Relatório'):visible"

MESES_PT = {
    "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
    "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
    "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
}

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE COBRANÇA'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE COBRANÇA'").is_visible(timeout=2000):
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
    logger.info("Navegando para Relatório de Cobrança de Aluguel e IPTU via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-cobranca"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page, data_inicio: str) -> None:
    """
    Preenche os filtros de Mês e Ano.
    data_inicio vem no formato YYYY-MM
    """
    logger.info(f"Preenchendo filtros de data: {data_inicio}")
    contexto = obter_contexto_pagina(page)
    page.wait_for_timeout(2000)
    
    if not data_inicio or len(data_inicio) < 7:
        logger.error("Data de início inválida. O relatório será gerado com o mês padrão da tela.")
        return
        
    ano = data_inicio[:4]
    mes_num = data_inicio[5:7]
    mes_nome = MESES_PT.get(mes_num, "Janeiro")
    
    try:
        # A estratégia agora é simular um humano lidando com um dropdown customizado (ex: ng-select)
        try:
            # --- MÊS ---
            logger.info(f"Tentando selecionar o mês: {mes_nome}")
            # Clica no container logo abaixo/depois da label Mês para abrir o dropdown customizado
            box_mes = contexto.locator("xpath=//label[contains(text(), 'Mês')]/following-sibling::*").first
            box_mes.click(timeout=3000)
            page.wait_for_timeout(500) # Pequena pausa para a animação do dropdown
            
            # Clica na opção da lista que acabou de aparecer (procura no DOM inteiro pois modais ficam no fim do body)
            opcao_mes = page.locator(f"text='{mes_nome}'").last
            opcao_mes.click(timeout=3000)
            
            # --- ANO ---
            logger.info(f"Tentando preencher o ano: {ano}")
            box_ano = contexto.locator("xpath=//label[contains(text(), 'Ano')]/following-sibling::input | //label[contains(text(), 'Ano')]/following-sibling::*//input").first
            box_ano.click(timeout=3000)
            box_ano.fill(ano)
            box_ano.press("Tab")
            
            logger.info(f"Filtros de Mês ({mes_nome}) e Ano ({ano}) preenchidos fisicamente com sucesso!")
        except Exception as fallback_e:
            logger.warning(f"Falhou ao clicar fisicamente no dropdown/input: {fallback_e}")
            logger.info("Tentando forçar valor via JS no input escondido...")
            contexto.evaluate("""
                ([mesStr, anoStr]) => {
                    const labels = Array.from(document.querySelectorAll('label'));
                    
                    // --- Preencher Mês ---
                    const mesLabel = labels.find(l => l.innerText && l.innerText.includes('Mês'));
                    if (mesLabel) {
                        const parent = mesLabel.parentElement;
                        const select = parent.querySelector('select');
                        if (select) {
                            const option = Array.from(select.options).find(o => o.text.trim() === mesStr);
                            if (option) {
                                select.value = option.value;
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    }
                    
                    // --- Preencher Ano ---
                    const anoLabel = labels.find(l => l.innerText && l.innerText.includes('Ano'));
                    if (anoLabel) {
                        const parent = anoLabel.parentElement;
                        const input = parent.querySelector('input[type="text"], input[type="number"]');
                        if (input) {
                            input.value = anoStr;
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    }
                }
            """, [mes_nome, ano])
            logger.info(f"Filtros de Mês ({mes_nome}) e Ano ({ano}) preenchidos via JS (Fallback).")
    except Exception as e:
        logger.error(f"Aviso ao preencher filtros: {e}")
        
    page.wait_for_timeout(1000)

def exportar_excel(page: Page, data_inicio: str, data_fim: str) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório Cobrança)")
    contexto = obter_contexto_pagina(page)

    try:
        # Pega a referência correta para o botão (trata maiúsculo e minúsculo com pseudo selector)
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
        btn_gerar.click(timeout=5000)
        
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
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_06.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo PDF interceptado e salvo.")
        
        # --- EXPORTAÇÃO PARA EXCEL ---
        from src.utilitarios.conversor_cobranca import converter_para_excel
        from src.utils import mover_arquivo_para_destino, gerar_nome_arquivo
        try:
            logger.info("Iniciando conversão visual PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp)
            if caminho_excel:
                logger.info("Movendo o Excel gerado para a pasta de destino...")
                # Padronizando o nome igual ao PDF
                nome_excel = gerar_nome_arquivo(6, "06 Relatório de Cobrança de Aluguel e IPTU", data_inicio, data_fim, ".xlsx")
                mover_arquivo_para_destino(caminho_excel, nome_excel)
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão: {e}")
        
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page, data_inicio)
    return exportar_excel(page, data_inicio, data_fim)
