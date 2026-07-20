# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path) -> Path | None:
    logger.info("Iniciando a extração inteligente do PDF (Rel. 09 - Comissão de Cobranças Recebidas)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Grupos Pagamento:
    # 1: Contrato
    # 2: Imovel
    # 3: Locatario
    # 4: Vencimento (dd/mm/yyyy)
    # 5: Aluguel Mês (R$...)
    # 6: IPTU (opcional)
    # 7: Valor gerado
    # 8: Pagamento (dd/mm/yyyy)
    # 9: Valor pago
    padrao_pagamento = re.compile(r'^(\d+)\s+(\d+)\s+(.+?)\s+(\d{2}/\d{2}/\d{4})\s+(R\$\s*[\d\.,]+)\s+(?:([\d\.,]+)\s+)?([\d\.,]+)\s+(\d{2}/\d{2}/\d{4})\s+([\d\.,]+)$')
    
    # Grupos Taxa:
    # 1: Código
    # 2: Mês
    # 3: Ano
    # 4: Valor Taxa
    padrao_taxa = re.compile(r'^(\d+)\s+TAXA DE ADMINISTRA\w+\s+(\d+)\s+(\d+)\s+(R\$\s*[\d\.,]+)$')
    
    linha_atual = None
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            texto = page.extract_text()
            if not texto:
                continue
                
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha:
                    continue
                    
                match_pag = padrao_pagamento.match(linha)
                if match_pag:
                    if linha_atual:
                        dados_extraidos.append(linha_atual)
                        
                    linha_atual = {
                        "Contrato": int(match_pag.group(1)),
                        "Imóvel": int(match_pag.group(2)),
                        "Locatário": match_pag.group(3),
                        "Vencimento": match_pag.group(4),
                        "Aluguel Mês": match_pag.group(5),
                        "IPTU": match_pag.group(6) if match_pag.group(6) else "",
                        "Valor Gerado": match_pag.group(7),
                        "Pagamento": match_pag.group(8),
                        "Valor Pago": match_pag.group(9),
                        "Taxa Adm Mês": "",
                        "Taxa Adm Ano": "",
                        "Taxa Adm Valor": ""
                    }
                    continue
                    
                match_taxa = padrao_taxa.match(linha)
                if match_taxa and linha_atual:
                    linha_atual["Taxa Adm Mês"] = match_taxa.group(2)
                    linha_atual["Taxa Adm Ano"] = match_taxa.group(3)
                    linha_atual["Taxa Adm Valor"] = match_taxa.group(4)
                    
        # Salva a última linha se existir
        if linha_atual:
            dados_extraidos.append(linha_atual)
            
    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros extraídos do Relatório 09.")
    
    df = pd.DataFrame(dados_extraidos)
    
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    try:
        df.to_excel(caminho_excel, index=False)
        logger.info(f"Excel gerado com sucesso em: {caminho_excel}")
        return caminho_excel
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo Excel: {e}")
        return None
