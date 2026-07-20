# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path) -> Path | None:
    logger.info("Iniciando a extração inteligente do PDF (Contratos x Cobranças)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Regex padrao: Contrato | Locatario | Total | Pagos | Nao Pagos | [R$ em aberto]
    padrao_linha = re.compile(r'^(\d+)\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(R\$\s*[\d\.,]+))?$')
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto:
                continue
                
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha:
                    continue
                    
                match = padrao_linha.match(linha)
                if match:
                    id_contrato = match.group(1)
                    locatario = match.group(2)
                    total = match.group(3)
                    pagos = match.group(4)
                    nao_pagos = match.group(5)
                    r_aberto = match.group(6) if match.group(6) else "R$ 0,00"
                    
                    dados_extraidos.append({
                        "Contrato": int(id_contrato),
                        "Locatário": locatario,
                        "Total": int(total),
                        "Pagos": int(pagos),
                        "Não pagos": int(nao_pagos),
                        "R$ em aberto": r_aberto
                    })
                    
    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros encontrados.")
    
    df = pd.DataFrame(dados_extraidos)
    
    # Opcional: ajustar tamanho de colunas etc, mas o to_excel padrao ja atende
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    try:
        df.to_excel(caminho_excel, index=False)
        logger.info(f"Excel gerado com sucesso em: {caminho_excel}")
        return caminho_excel
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo Excel: {e}")
        return None
