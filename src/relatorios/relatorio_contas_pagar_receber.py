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

        if '-' in data_inicio:
            ano_i, mes_i, dia_i = data_inicio.split('-')
        else:
            dia_i, mes_i, ano_i = data_inicio.split('/')

        data_js = f"new Date({ano_i}, {int(mes_i)-1}, {dia_i})"

        if data_fim:
            if '-' in data_fim:
                ano_f, mes_f, dia_f = data_fim.split('-')
            else:
                dia_f, mes_f, ano_f = data_fim.split('/')
            data_fim_js = f"new Date({ano_f}, {int(mes_f)-1}, {dia_f})"
        else:
            data_fim_js = data_js

        logger.info(f"Configurando datas via Angular scope: {data_inicio} até {data_fim}")

        page.evaluate(f"""
            () => {{
                const el = document.querySelector('[ng-controller]') || document.querySelector('.ng-scope');
                if (el && window.angular) {{
                    const scope = window.angular.element(el).scope();
                    if (scope && scope.relatorio) {{
                        scope.relatorio.datainicial = {data_js};
                        scope.relatorio.datafinal = {data_fim_js};
                        scope.$apply();
                        console.log('[Rel15] Datas configuradas no scope:', scope.relatorio.datainicial, scope.relatorio.datafinal);
                    }} else {{
                        console.error('[Rel15] scope.relatorio não encontrado');
                    }}
                }} else {{
                    console.error('[Rel15] Angular ou ng-controller não encontrado');
                }}
            }}
        """)

        logger.info("Interceptores e clique via Angular scope.gerar()...")

        from src.utilitarios.blob_interceptor import instalar_interceptores, aguardar_blob, baixar_pdf_da_blob

        instalar_interceptores(page)

        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_15.pdf"

        result = page.evaluate("""
            () => {
                try {
                    if (!window.angular) return 'angular not found';
                    const gerarFunc = document.querySelector('[ng-click="gerarRelatorioTransacoes()"]');
                    if (!gerarFunc) return 'ng-click element not found';
                    const scope = window.angular.element(gerarFunc).scope();
                    if (!scope) return 'scope not found';
                    if (scope.gerar) { scope.gerar(); return 'scope.gerar() called'; }
                    if (scope.gerarRelatorioTransacoes) { scope.gerarRelatorioTransacoes(); return 'scope.gerarRelatorioTransacoes() called'; }
                    const keys = Object.keys(scope).filter(k => !k.startsWith('$') && typeof scope[k] === 'function');
                    return 'no gerar func. Scope funcs: ' + keys.join(', ');
                } catch(e) {
                    return 'error: ' + e.message;
                }
            }
        """)
        logger.info(f"Resultado da chamada Angular: {result}")

        if 'called' not in result:
            logger.warning("Falha ao chamar scope.gerar(). Tentando fallback via botão...")
            contexto = obter_contexto_pagina(page)
            btn_gerar = contexto.locator("button:has-text('Gerar Relat')").first
            btn_gerar.click(timeout=5000)

        url_pdf = aguardar_blob(page, timeout_s=90)

        if not url_pdf:
            logger.info("Blob não encontrado. Tentando capturar de nova janela...")
            from src.utilitarios.blob_interceptor import tentar_capturar_blob_nova_janela
            url_pdf = tentar_capturar_blob_nova_janela(page, timeout_s=30)

        if not url_pdf:
            raise Exception("Não foi possível capturar a URL do PDF (Blob).")

        logger.info(f"URL do Blob capturada: {url_pdf}")

        pdf_bytes = baixar_pdf_da_blob(page, url_pdf)
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
