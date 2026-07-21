# -*- coding: utf-8 -*-
"""
Interceptador compartilhado de PDFs via blob/window.open.
Usa múltiplas estratégias: window.open override + popup event do Playwright + monitoramento de DOM.
Inclui suporte a debug com screenshots e logging de estado da página.
"""
from playwright.sync_api import Page
from src.logger import logger
from pathlib import Path
from datetime import datetime
import base64
import json
import os


PASTA_DEBUG = Path(os.environ.get("PASTA_DEBUG", "/home/ubuntu/Jordao-Automatizacao/logs/debug"))


def _pasta_debug_atual() -> Path:
    """Cria e retorna a pasta de debug com timestamp."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta = PASTA_DEBUG / ts
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def salvar_screenshot(page: Page, nome: str, pasta: Path) -> None:
    """Salva um screenshot full_page da página atual."""
    try:
        caminho = pasta / f"{nome}.png"
        page.screenshot(path=str(caminho), full_page=True)
        logger.info(f"Screenshot salvo: {caminho}")
    except Exception as e:
        logger.warning(f"Falha ao salvar screenshot '{nome}': {e}")


def logar_estado_pagina(page: Page, label: str, pasta: Path) -> None:
    """Salva informações detalhadas do estado da página em JSON."""
    try:
        estado = page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                const modals = document.querySelectorAll('.modal, [class*="modal"]');
                const overlays = document.querySelectorAll('.modal-backdrop, [class*="overlay"]');
                const blobRoubada = window.blobUrlRoubada || null;
                const blobLinks = Array.from(document.querySelectorAll('a[href^="blob:"], iframe[src^="blob:"]'))
                    .map(l => l.href || l.src);
                const gerarBtns = Array.from(document.querySelectorAll('button'))
                    .filter(b => b.innerText && b.innerText.toLowerCase().includes('gerar'))
                    .map(b => ({text: b.innerText.trim(), visible: b.offsetParent !== null, disabled: b.disabled}));

                return {
                    url: window.location.href,
                    title: document.title,
                    iframeCount: iframes.length,
                    iframeSrcs: Array.from(iframes).map(f => f.src).slice(0, 5),
                    modalCount: modals.length,
                    overlayCount: overlays.length,
                    blobRoubada: blobRoubada,
                    blobLinks: blobLinks,
                    gerarButtons: gerarBtns,
                    bodyTextPreview: document.body ? document.body.innerText.substring(0, 2000) : 'N/A'
                };
            }
        """)
        caminho = pasta / f"estado_{label}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        logger.info(f"Estado da página salvo: {caminho}")
        logger.info(f"  URL: {estado['url']}")
        logger.info(f"  Iframes: {estado['iframeCount']}, Modals: {estado['modalCount']}, Overlays: {estado['overlayCount']}")
        logger.info(f"  blobUrlRoubada: {estado['blobRoubada']}")
        logger.info(f"  Blob links no DOM: {estado['blobLinks']}")
        logger.info(f"  Botões 'Gerar': {estado['gerarButtons']}")
    except Exception as e:
        logger.warning(f"Falha ao logar estado da página: {e}")


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


def diagnosticar_botao(page: Page, pasta: Path) -> None:
    """Diagnóstico profundo do botão: verifica Angular bindings, overlay stack, etc."""
    try:
        info = page.evaluate("""
            () => {
                const gerarBtns = Array.from(document.querySelectorAll('button')).filter(
                    b => b.innerText && b.innerText.includes('Gerar Relat')
                );
                const results = gerarBtns.map(b => {
                    const rect = b.getBoundingClientRect();
                    const el = document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2);
                    return {
                        text: b.innerText.trim().substring(0, 50),
                        visible: b.offsetParent !== null,
                        hasNgClick: b.hasAttribute('ng-click'),
                        hasOnClick: b.hasAttribute('onclick'),
                        hasAngularClick: b.hasAttribute('(click)') || b.hasAttribute('on-click'),
                        ngClickValue: b.getAttribute('ng-click') || '',
                        angularVersion: window.angular ? (window.angular.version ? window.angular.version.full : 'unknown') : 'not loaded',
                        angularScope: (() => {
                            try {
                                if (window.angular && window.angular.element) {
                                    const scope = window.angular.element(b).scope();
                                    return scope ? Object.keys(scope).filter(k => !k.startsWith('$')).slice(0, 20) : 'no scope';
                                }
                            } catch(e) {}
                            return 'error';
                        })(),
                        elementAtPoint: el ? {tag: el.tagName, class: (el.className||'').toString().substring(0,80)} : null,
                        isBlocked: el ? (el !== b && !b.contains(el)) : false,
                        eventListeners: (() => {
                            try {
                                const evts = getEventListeners ? getEventListeners(b) : null;
                                return evts ? Object.keys(evts) : 'getEventListeners not available';
                            } catch(e) { return 'error'; }
                        })()
                    };
                });

                const blockUI = document.querySelectorAll('.block-ui-container, .block-ui-overlay, .block-ui-message-container');
                const blockUIDetails = Array.from(blockUI).map(e => ({
                    class: (e.className||'').toString().substring(0,100),
                    opacity: getComputedStyle(e).opacity,
                    height: getComputedStyle(e).height,
                    width: getComputedStyle(e).width,
                    zIndex: getComputedStyle(e).zIndex,
                    pointerEvents: getComputedStyle(e).pointerEvents
                }));

                return {
                    buttons: results,
                    blockUIElements: blockUIDetails,
                    hasAngular: !!window.angular,
                    documentReady: document.readyState
                };
            }
        """)
        import json
        caminho = pasta / "diagnostico_botao.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        logger.info(f"Diagnóstico do botão salvo: {caminho}")

        for b in info.get('buttons', []):
            logger.info(f"  Botão: '{b['text']}' | ng-click={b.get('ngClickValue','')} | angular={b.get('angularVersion','?')}")
            logger.info(f"    Angular scope keys: {b.get('angularScope','?')}")
            logger.info(f"    elementAtPoint: {b.get('elementAtPoint','?')} | blocked={b.get('isBlocked','?')}")
        for bui in info.get('blockUIElements', []):
            logger.info(f"  BlockUI: {bui['class'][:60]} opacity={bui['opacity']} size={bui['width']}x{bui['height']} z={bui['zIndex']}")
    except Exception as e:
        logger.warning(f"Falha no diagnóstico do botão: {e}")


def interceptar_requests(page: Page) -> list:
    """Instala um listener que captura requests HTTP feitas após o clique."""
    requests_info = []

    def on_request(req):
        requests_info.append({"url": req.url[:200], "method": req.method})

    page.on("request", on_request)
    return requests_info


def gerar_e_capturar_pdf(
    page: Page,
    contexto,
    btn_gerar_locator,
    caminho_temp,
    timeout_blob_s: int = 60,
    debug: bool = True,
) -> bool:
    """
    Fluxo completo com debug aprofundado:
    1. Cria pasta de debug e salva estado ANTES do clique
    2. Diagnóstico do botão Angular (bindings, overlays)
    3. Instala interceptores + monitor de requests
    4. Clica no botão (com múltiplas estratégias)
    5. Aguarda blob via polling
    6. Se não encontrar, tenta capturar de nova janela/popup
    7. Baixa o PDF e salva em caminho_temp
    Retorna True se sucesso, False se falhou.
    """
    pasta = _pasta_debug_atual() if debug else None

    if debug and pasta:
        logar_estado_pagina(page, "01_antes_instalar_interceptores", pasta)
        diagnosticar_botao(page, pasta)
        salvar_screenshot(page, "01_antes_instalar_interceptores", pasta)

    instalar_interceptores(page)

    if debug and pasta:
        logar_estado_pagina(page, "02_depois_interceptores_antes_clique", pasta)

    requests_monitor = interceptar_requests(page) if debug else []

    logger.info("Clicando no botão 'Gerar Relatório'...")
    click_ok = False
    try:
        btn_gerar_locator.click(timeout=5000)
        logger.info("Clique no botão executado com sucesso.")
        click_ok = True
    except Exception as e:
        logger.warning(f"Clique normal falhou: {e}")

    if not click_ok:
        logger.info("Tentando via JS...")
        js_code = """
            () => {
                const btns = Array.from(document.querySelectorAll('button, a, div.btn, span.btn'));
                const gerar = btns.find(b => {
                    const t = (b.innerText || '').toLowerCase();
                    return t.includes('gerar relat') && b.offsetParent !== null;
                });
                if (gerar) {
                    gerar.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    return 'dispatched on: ' + gerar.tagName + ' ' + gerar.innerText.trim().substring(0, 30);
                }
                return 'not found';
            }
        """
        if hasattr(contexto, 'evaluate'):
            result = contexto.evaluate(js_code)
        else:
            result = page.evaluate(js_code)
        logger.info(f"Clique via JS resultado: {result}")
        click_ok = result != 'not found'

    if not click_ok:
        logger.info("Tentando via Angular scope...")
        angular_result = page.evaluate("""
            () => {
                try {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const gerar = btns.find(b => b.innerText && b.innerText.includes('Gerar Relat') && b.offsetParent !== null);
                    if (gerar && window.angular && window.angular.element) {
                        const scope = window.angular.element(gerar).scope();
                        if (scope && scope.gerarRelatorio) {
                            scope.gerarRelatorio();
                            return 'called gerarRelatorio() via Angular scope';
                        }
                        if (scope) {
                            const scopeKeys = Object.keys(scope).filter(k => !k.startsWith('$') && typeof scope[k] === 'function');
                            return 'scope functions: ' + scopeKeys.join(', ');
                        }
                        return 'no scope found';
                    }
                    return 'angular not available';
                } catch(e) {
                    return 'error: ' + e.message;
                }
            }
        """)
        logger.info(f"Angular scope resultado: {angular_result}")

    if debug and pasta:
        logger.info(f"Requests monitoradas até agora: {len(requests_monitor)}")
        for r in requests_monitor[-5:]:
            logger.info(f"  {r['method']} {r['url'][:120]}")

    url_pdf = aguardar_blob(page, timeout_blob_s)

    if debug and pasta:
        logger.info(f"Requests totais após clique (15s): {len(requests_monitor)}")
        for r in requests_monitor:
            if any(kw in r['url'].lower() for kw in ['api', 'relatorio', 'report', 'pdf', 'export', 'caixa', 'gerar']):
                logger.info(f"  RELEVANTE: {r['method']} {r['url'][:150]}")
        logar_estado_pagina(page, "03_depois_aguardar_blob", pasta)
        salvar_screenshot(page, "03_depois_aguardar_blob", pasta)

    if not url_pdf:
        logger.info("Blob não encontrado via polling. Tentando capturar de nova janela...")
        url_pdf = tentar_capturar_blob_nova_janela(page, timeout_s=30)

    if not url_pdf:
        logger.error("Nenhum blob encontrado em nenhuma estratégia.")
        if debug and pasta:
            salvar_screenshot(page, "05_falha_final", pasta)
        return False

    logger.info(f"URL do Blob capturada: {url_pdf}")

    pdf_bytes = baixar_pdf_da_blob(page, url_pdf)
    with open(caminho_temp, "wb") as f:
        f.write(pdf_bytes)

    logger.info(f"Sucesso! Arquivo PDF salvo em {caminho_temp}")
    if debug and pasta:
        salvar_screenshot(page, "06_sucesso", pasta)
    return True
