# -*- coding: utf-8 -*-
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import montar_url, PASTA_DOWNLOADS_SO
from src.logger import logger
import json

def obter_contexto_pagina(page: Page):
    try:
        if page.locator("text='RELATÓRIO DE ENTRADAS E SAÍDAS'").is_visible(timeout=2000):
            return page
    except:
        pass
    try:
        iframe = page.frame_locator("iframe").first
        if iframe.locator("text='RELATÓRIO DE ENTRADAS E SAÍDAS'").is_visible(timeout=2000):
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
    logger.info("Navegando para Relatório de Recebimentos e Pagamentos via URL direta")
    fechar_popup_imoalert(page)
    
    try:
        page.goto(montar_url("rel-entradassaidas"), timeout=15000)
        page.wait_for_load_state("networkidle")
        logger.info("Navegação direta concluída.")
    except Exception as e:
        logger.warning(f"Navegação direta falhou. Erro: {e}")
        raise

def preencher_filtros(page: Page, data_inicio: str, data_fim: str) -> None:
    logger.info(f"Preenchendo os filtros: {data_inicio} até {data_fim}")
    contexto = obter_contexto_pagina(page)
    
    parts_i = data_inicio.split('-')
    parts_f = data_fim.split('-')
    data_inicio_br = f"{parts_i[2]}{parts_i[1]}{parts_i[0]}" # ddmmyyyy
    data_fim_br = f"{parts_f[2]}{parts_f[1]}{parts_f[0]}"    # ddmmyyyy
    
    try:
        input_inicio = contexto.locator("xpath=(//*[contains(text(), 'Data incio')]//following::input)[1]")
        input_fim = contexto.locator("xpath=(//*[contains(text(), 'Data fim')]//following::input)[1]")
        
        # O placeholder da Jordão pode ser diferente ou exigir clique/limpeza
        input_inicio.click(timeout=5000)
        input_inicio.clear()
        input_inicio.press_sequentially(data_inicio_br, delay=50)
        
        input_fim.click(timeout=5000)
        input_fim.clear()
        input_fim.press_sequentially(data_fim_br, delay=50)
        
        logger.info("Datas preenchidas com sucesso.")
    except Exception as e:
        raise Exception(f"FALHA CRÍTICA: Não foi possível preencher as datas no relatório 13. Erro: {e}")
        
    page.wait_for_timeout(1000)

def exportar_pdf(page: Page, data_inicio: str, data_fim: str) -> Path | None:
    logger.info("Iniciando geração e exportação (Relatório 13)")

    try:
        fechar_popup_imoalert(page)

        from src.utilitarios.blob_interceptor import instalar_interceptores, aguardar_blob, baixar_pdf_da_blob

        if '-' in data_inicio:
            ano_i, mes_i, dia_i = data_inicio.split('-')
        else:
            dia_i, mes_i, ano_i = data_inicio.split('/')

        if data_fim:
            if '-' in data_fim:
                ano_f, mes_f, dia_f = data_fim.split('-')
            else:
                dia_f, mes_f, ano_f = data_fim.split('/')
        else:
            ano_f, mes_f, dia_f = ano_i, mes_i, dia_i

        dt_inicio_iso = f"{ano_i}-{mes_i.zfill(2)}-{dia_i.zfill(2)}T00:00:00.000Z"
        dt_fim_iso = f"{ano_f}-{mes_f.zfill(2)}-{dia_f.zfill(2)}T23:59:59.999Z"

        logger.info(f"Datas para o POST: inicio={dt_inicio_iso}, fim={dt_fim_iso}")

        post_body_injetado = {
            "inicio": dt_inicio_iso,
            "fim": dt_fim_iso,
        }

        def injetar_datas(route):
            request = route.request
            try:
                body = json.loads(request.post_data) if request.post_data else {}
            except Exception:
                body = {}
            body.update(post_body_injetado)
            new_body = json.dumps(body, ensure_ascii=False)
            logger.info(f"Route intercept: injetando datas no POST. Body final: {new_body[:500]}")
            route.continue_(post_data=new_body)
            try:
                page.unroute("**/rel-entradassaidas/*", injetar_datas)
            except Exception:
                pass

        page.route("**/rel-entradassaidas/*", injetar_datas)

        instalar_interceptores(page)

        caminho_temp = Path(PASTA_DOWNLOADS_SO) / "relatorio_temporario_13.pdf"

        logger.info("Chamando scope.gerar() via Angular...")
        result = page.evaluate("""
            () => {
                try {
                    if (!window.angular) return 'angular not found';
                    const el = document.querySelector('.btn-primary');
                    if (!el) return 'btn-primary not found';
                    const scope = window.angular.element(el).scope();
                    if (!scope) return 'scope not found';
                    if (!scope.gerar) return 'no gerar func';

                    var fakeForm = {$valid: true, $error: {required: {}}};
                    scope.gerar(fakeForm);
                    return 'scope.gerar() called';
                } catch(e) {
                    return 'error: ' + e.message;
                }
            }
        """)
        logger.info(f"Resultado Angular: {result}")

        if 'called' not in result:
            logger.warning("Falha Angular. Tentando fallback via clique...")
            try:
                page.unroute("**/rel-entradassaidas/*", injetar_datas)
            except Exception:
                pass
            page.route("**/rel-entradassaidas/*", injetar_datas)
            contexto = obter_contexto_pagina(page)
            btn_gerar = contexto.locator("button:has-text('Gerar relat')").first
            btn_gerar.click(timeout=5000)

        url_pdf = aguardar_blob(page, timeout_s=90)

        if not url_pdf:
            logger.info("Blob não encontrado. Tentando nova janela...")
            from src.utilitarios.blob_interceptor import tentar_capturar_blob_nova_janela
            url_pdf = tentar_capturar_blob_nova_janela(page, timeout_s=30)

        if not url_pdf:
            raise Exception("Não foi possível capturar a URL do PDF (Blob).")

        logger.info(f"URL do Blob capturada: {url_pdf}")

        pdf_bytes = baixar_pdf_da_blob(page, url_pdf)
        with open(caminho_temp, "wb") as f:
            f.write(pdf_bytes)

        logger.info("Sucesso Total! Arquivo PDF interceptado.")

        from src.utilitarios.conversor_recebimentos_pagamentos import converter_para_excel
        from src.utils import gerar_nome_arquivo, mover_arquivo_para_destino

        try:
            logger.info("Iniciando conversão PDF -> Excel...")
            caminho_excel = converter_para_excel(caminho_temp, data_inicio, data_fim)
            if caminho_excel:
                return caminho_excel
        except Exception as e:
            logger.error(f"Erro no módulo de conversão do relatório 13: {e}")

        return caminho_temp

    except Exception as e:
        raise Exception(f"FALHA CRÍTICA na exportação: {e}")

def extrair(page: Page, data_inicio: str = None, data_fim: str = None) -> Path:
    navegar(page)
    preencher_filtros(page, data_inicio, data_fim)
    return exportar_pdf(page, data_inicio, data_fim)
