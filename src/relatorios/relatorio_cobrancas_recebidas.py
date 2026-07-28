# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

class SeletoresCobrancasRecebidas:
    MENU_LOCACAO = "text='Locação'"
    MENU_COBRANCAS_PAGAMENTOS = "text='Rel. Cobranças e Pagamentos'"
    MENU_COBRANCAS_RECEBIDAS = "text='Rel. Cobranças recebidas'"
    BTN_GERAR = "button:has-text('Gerar Relatório'):visible"

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE ALUGUÉIS RECEBIDOS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE ALUGUÉIS RECEBIDOS'").is_visible(timeout=2000):
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
    logger.info("Navegando para Rel. Cobranças recebidas via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-alugueisrecebidos"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def mapear_mes(mes_num: str) -> str:
    meses = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    return meses.get(mes_num, "Janeiro")

def preencher_filtros(page: Page, data_inicio: str, data_fim: str) -> None:
    # Formato esperado de data_inicio e data_fim: YYYY-MM
    logger.info(f"Preenchendo os filtros do relatório: Inicio {data_inicio} até Fim {data_fim}")
    fechar_popup_imoalert(page)
    contexto = obter_contexto_pagina(page)
    
    ano_inicio = data_inicio.split("-")[0]
    mes_inicio_texto = mapear_mes(data_inicio.split("-")[1])
    
    ano_fim = data_fim.split("-")[0]
    mes_fim_texto = mapear_mes(data_fim.split("-")[1])
    
    page.wait_for_timeout(2000)
    
    # --- Checkboxes (Cliques Físicos) ---
    logger.info("Marcando os 4 filtros (checkboxes) via clique físico Playwright...")
    checkbox_labels = ['Por período', 'Mostrar Proprietários', 'Mostrar valores de comissão', 'Mostrar movimentos']
    
    for texto in checkbox_labels:
        try:
            # Procura o texto exato na tela
            # Usa "last" porque as vezes existem títulos ou duplicatas escondidas.
            elemento = contexto.locator(f"text='{texto}'").last
            if elemento.is_visible(timeout=3000):
                logger.info(f"Clicando fisicamente no filtro: {texto}")
                elemento.click(timeout=3000)
                page.wait_for_timeout(500) # Pausa pequena entre cada clique humano
            else:
                # Fallback: tentar xpath
                logger.info(f"Elemento 'text={texto}' invisível. Tentando xpath genérico...")
                elemento_xpath = contexto.locator(f"xpath=//*[normalize-space(text())='{texto}']").last
                if elemento_xpath.is_visible(timeout=3000):
                    elemento_xpath.click(timeout=3000)
                    page.wait_for_timeout(500)
        except Exception as e:
            logger.error(f"Erro ao tentar clicar no filtro '{texto}': {e}")
            
    page.wait_for_timeout(1000)
        
    # --- Datas ---
    try:
        # DATA INICIAL
        logger.info(f"Preenchendo Data Inicial: {mes_inicio_texto}/{ano_inicio}")
        # Mês Inicial
        box_mes_inicio = contexto.locator("xpath=//label[contains(text(), 'Mês')]/following-sibling::*").nth(0)
        box_mes_inicio.click(timeout=3000)
        page.wait_for_timeout(500)
        page.locator(f"text='{mes_inicio_texto}'").last.click(timeout=3000)
        
        # Ano Inicial
        box_ano_inicio = contexto.locator("xpath=//label[contains(text(), 'Ano')]/following-sibling::input | //label[contains(text(), 'Ano')]/following-sibling::*//input").nth(0)
        box_ano_inicio.click(timeout=3000)
        box_ano_inicio.fill(ano_inicio)
        box_ano_inicio.press("Tab")
        
        # DATA FINAL
        logger.info(f"Preenchendo Data Final: {mes_fim_texto}/{ano_fim}")
        # Mês Final
        box_mes_fim = contexto.locator("xpath=//label[contains(text(), 'Mês')]/following-sibling::*").nth(1)
        box_mes_fim.click(timeout=3000)
        page.wait_for_timeout(500)
        page.locator(f"text='{mes_fim_texto}'").last.click(timeout=3000)
        
        # Ano Final
        box_ano_fim = contexto.locator("xpath=//label[contains(text(), 'Ano')]/following-sibling::input | //label[contains(text(), 'Ano')]/following-sibling::*//input").nth(1)
        box_ano_fim.click(timeout=3000)
        box_ano_fim.fill(ano_fim)
        box_ano_fim.press("Tab")
        
        logger.info("Filtros de data preenchidos fisicamente com sucesso.")
    except Exception as e:
        logger.warning(f"Falha ao clicar fisicamente nas datas: {e}")
        logger.info("Tentando forçar via JS (Fallback)...")
        contexto.evaluate(f"""
            ([mi, ai, mf, af]) => {{
                const labelsMes = Array.from(document.querySelectorAll('label')).filter(l => l.innerText && l.innerText.includes('Mês'));
                const labelsAno = Array.from(document.querySelectorAll('label')).filter(l => l.innerText && l.innerText.includes('Ano'));
                
                if (labelsMes.length >= 2) {{
                    const s1 = labelsMes[0].parentElement.querySelector('select');
                    if (s1) {{ const opt = Array.from(s1.options).find(o => o.text.trim() === mi); if (opt) {{ s1.value = opt.value; s1.dispatchEvent(new Event('change', {{ bubbles: true }})); }} }}
                    const s2 = labelsMes[1].parentElement.querySelector('select');
                    if (s2) {{ const opt = Array.from(s2.options).find(o => o.text.trim() === mf); if (opt) {{ s2.value = opt.value; s2.dispatchEvent(new Event('change', {{ bubbles: true }})); }} }}
                }}
                
                if (labelsAno.length >= 2) {{
                    const i1 = labelsAno[0].parentElement.querySelector('input[type="text"], input[type="number"]');
                    if (i1) {{ i1.value = ai; i1.dispatchEvent(new Event('input', {{ bubbles: true }})); i1.dispatchEvent(new Event('change', {{ bubbles: true }})); }}
                    const i2 = labelsAno[1].parentElement.querySelector('input[type="text"], input[type="number"]');
                    if (i2) {{ i2.value = af; i2.dispatchEvent(new Event('input', {{ bubbles: true }})); i2.dispatchEvent(new Event('change', {{ bubbles: true }})); }}
                }}
            }}
        """, [mes_inicio_texto, ano_inicio, mes_fim_texto, ano_fim])
    
    page.wait_for_timeout(1000)

def exportar_excel(page: Page, data_inicio: str, data_fim: str) -> Path | None:
    logger.info("Iniciando geração e exportação (07 Rel. Cobranças Recebidas)")
    contexto = obter_contexto_pagina(page)

    try:
        fechar_popup_imoalert(page)
        btn_gerar = contexto.locator(SeletoresCobrancasRecebidas.BTN_GERAR).first
        
        logger.info("Injetando script para interceptar o PDF...")
        page.evaluate("""
            window.blobUrlRoubada = null;
            window.open = function(url) {
                window.blobUrlRoubada = url;
                return null;
            };
        """)
        
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
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_07.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso! Arquivo PDF interceptado e salvo.")
        
        # --- BIFURCAÇÃO: TENTAR CONVERTER PARA EXCEL ---
        from src.utilitarios.conversor_cobrancas_recebidas import converter_para_excel as converter_rel_07
        from src.utils import mover_arquivo_para_destino, gerar_nome_arquivo
        try:
            logger.info("Chamando o conversor para Excel do rel. 07...")
            caminho_excel = converter_rel_07(caminho_temp)
            if caminho_excel:
                logger.info("Movendo o Excel gerado para a pasta de destino...")
                # Padronizando o nome igual ao PDF
                nome_excel = gerar_nome_arquivo(7, "07 Relatório de Cobranças Recebidas", data_inicio, data_fim, ".xlsx")
                mover_arquivo_para_destino(caminho_excel, nome_excel)
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão: {e}")
        # -----------------------------------------------
        
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page, data_inicio, data_fim)
    return exportar_excel(page, data_inicio, data_fim)
