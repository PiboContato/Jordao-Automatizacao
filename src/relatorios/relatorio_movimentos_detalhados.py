# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE MOVIMENTOS DETALHADOS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE MOVIMENTOS DETALHADOS'").is_visible(timeout=2000):
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
    logger.info("Navegando para Relatório de Movimentos Detalhados")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-movimentosdetalhados"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page, data_inicio: str) -> None:
    # data_inicio vem no formato YYYY-MM-DD
    partes = data_inicio.split('-')
    ano = partes[0]
    mes = partes[1]
    
    meses_pt = {
        "01": "Janeiro", "02": "Fevereiro", "03": "Março", "04": "Abril",
        "05": "Maio", "06": "Junho", "07": "Julho", "08": "Agosto",
        "09": "Setembro", "10": "Outubro", "11": "Novembro", "12": "Dezembro"
    }
    
    mes_str = meses_pt.get(mes, "Janeiro")
    logger.info(f"Preenchendo Mês: {mes_str} e Ano: {ano}")
    
    contexto = obter_contexto_pagina(page)
    
    try:
        # Tenta achar a caixa do mês (que fica logo abaixo da label * Mês) e clica nela para abrir a lista
        logger.info("Abrindo dropdown de Mês...")
        
        # 1. Localiza qualquer div ou botão clicável logo após a palavra 'Mês'
        caixa_mes = contexto.locator("xpath=(//*[contains(text(), 'Mês')]//following::*[self::div or self::button or self::input])[1]")
        caixa_mes.click(timeout=5000)
        page.wait_for_timeout(1000) # Espera a animação da lista suspensa
        
        # 2. Clica na opção desejada de forma forçada
        logger.info(f"Clicando na opção {mes_str}...")
        
        # Como o dropdown pode ser renderizado no final do <body>, avaliamos no page principal também
        opcao = page.locator(f"text='{mes_str}'").last
        if opcao.is_visible():
            opcao.click(timeout=3000)
        else:
            # Fallback JavaScript (ninja click)
            page.evaluate(f"""
                () => {{
                    let elements = Array.from(document.querySelectorAll('*'));
                    let targets = elements.filter(el => 
                        el.innerText && 
                        el.innerText.trim() === '{mes_str}' && 
                        el.children.length === 0
                    );
                    if (targets.length > 0) {{
                        let target = targets[targets.length - 1];
                        target.click();
                    }}
                }}
            """)
        page.wait_for_timeout(500)
    except Exception as e:
        logger.warning(f"Aviso ao preencher mês: {e}")
        
    try:
        # Preencher Ano
        input_ano = contexto.locator("xpath=(//*[contains(text(), 'Ano')]//following::input)[1]")
        input_ano.click(timeout=2000)
        input_ano.clear()
        input_ano.press_sequentially(ano, delay=50)
    except Exception as e:
        logger.warning(f"Falha ao preencher ano: {e}")
        
    page.wait_for_timeout(1000)

def exportar_pdf(page: Page, data_inicio: str, data_fim: str = None) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório 14)")
    contexto = obter_contexto_pagina(page)

    try:
        btn_gerar = contexto.locator("button:has-text('Gerar relat')").first
        
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
        
        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_14.pdf"
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)
            
        logger.info("Sucesso Total! Arquivo PDF interceptado.")
        
        from src.utilitarios.conversor_movimentos_detalhados import converter_para_excel
        from src.utils import gerar_nome_arquivo, mover_arquivo_para_destino
        
        try:
            logger.info("Iniciando conversão PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp, data_inicio)
            if caminho_excel:
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão do relatório 14: {e}")
            
        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page, data_inicio)
    return exportar_pdf(page, data_inicio, data_fim)
