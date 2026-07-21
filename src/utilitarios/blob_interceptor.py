# -*- coding: utf-8 -*-
"""
Interceptador compartilhado de PDFs via blob/window.open.
Usa múltiplas estratégias: window.open override + popup event do Playwright + monitoramento de DOM.
"""
from playwright.sync_api import Page
from src.logger import logger
import base64
import time


def instalar_interceptores(page: Page) -> None:
    """Instala os interceptores JS na página ANTES de clicar no botão de gerar."""
    logger.info("Instalando interceptores de blob (window.open + DOM links)...")
    page.evaluate("""
        window.blobUrlRoubada = null;
        window._origWindowOpen = window.open;
        window.open = function(url) {
            window.blobUrlRoubada = url;
            return null;
        };
    """)
    page.wait_for_timeout(500)


def aguardar_blob(page: Page, timeout_s: int = 60) -> str | None:
    """Aguarda a captura de uma URL de blob via polling. Retorna a URL ou None."""
    logger.info(f"Aguardando blob por até {timeout_s}s...")

    url_pdf = page.evaluate(f"""
        new Promise((resolve) => {{
            let t = 0;
            let max = {timeout_s * 10};
            let check = setInterval(() => {{
                if (window.blobUrlRoubada) {{ 
                    clearInterval(check); 
                    resolve(window.blobUrlRoubada); 
                }}
                const links = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'));
                if (links.length > 0) {{
                    clearInterval(check); 
                    resolve(links[0].href || links[0].src);
                }}
                if (t++ > max) {{ 
                    clearInterval(check); 
                    resolve(null); 
                }}
            }}, 100);
        }})
    """)
    return url_pdf


def baixar_pdf_da_blob(page: Page, url_pdf: str) -> bytes:
    """Baixa o conteúdo de um blob URL e retorna os bytes do PDF."""
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

    base64_data = pdf_base64_url.split(",")[1]
    return base64.b64decode(base64_data)


def tentar_capturar_blob_nova_janela(page: Page, timeout_s: int = 30) -> str | None:
    """
    Tenta capturar o blob de uma nova janela/popup que possa ter sido aberta.
    Retorna a URL do blob ou None.
    """
    logger.info(f"Verificando se há nova janela/popup aberta...")
    try:
        with page.context.expect_page(timeout=timeout_s * 1000) as new_page_info:
            pass
        new_page = new_page_info.value
        logger.info(f"Nova janela detectada: {new_page.url}")

        if new_page.url.startswith("blob:"):
            logger.info(f"URL da nova janela É um blob: {new_page.url}")
            return new_page.url

        url_pdf = new_page.evaluate("""
            new Promise((resolve) => {
                let t = 0;
                let check = setInterval(() => {
                    const links = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'));
                    if (links.length > 0) {
                        clearInterval(check);
                        resolve(links[0].href || links[0].src);
                    }
                    if (window.location.href.startsWith('blob:')) {
                        clearInterval(check);
                        resolve(window.location.href);
                    }
                    if (t++ > 200) {
                        clearInterval(check);
                        resolve(null);
                    }
                }, 100);
            })
        """)
        return url_pdf
    except Exception:
        logger.info("Nenhuma nova janela/popup detectado.")
        return None


def gerar_e_capturar_pdf(
    page: Page,
    contexto,
    btn_gerar_locator,
    caminho_temp,
    timeout_blob_s: int = 60,
) -> bool:
    """
    Fluxo completo:
    1. Instala interceptores
    2. Clica no botão (com fallback JS)
    3. Aguarda blob via polling
    4. Se não encontrar, tenta capturar de nova janela/popup
    5. Baixa o PDF e salva em caminho_temp
    Retorna True se sucesso, False se falhou.
    """
    instalar_interceptores(page)

    logger.info("Clicando no botão 'Gerar Relatório'...")
    try:
        btn_gerar_locator.click(timeout=5000)
    except Exception as e:
        logger.warning(f"Clique normal falhou. Tentando via JS: {e}")
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

    url_pdf = aguardar_blob(page, timeout_blob_s)

    if not url_pdf:
        logger.info("Blob não encontrado via polling. Tentando capturar de nova janela...")
        url_pdf = tentar_capturar_blob_nova_janela(page, timeout_s=30)

    if not url_pdf:
        logger.error("Nenhum blob encontrado em nenhuma estratégia.")
        return False

    logger.info(f"URL do Blob capturada: {url_pdf}")

    pdf_bytes = baixar_pdf_da_blob(page, url_pdf)
    with open(caminho_temp, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"Sucesso! Arquivo PDF salvo em {caminho_temp}")
    return True
