# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
import re
from pathlib import Path
from src.logger import logger

def converter_para_excel(caminho_pdf: Path) -> Path | None:
    """
    Lê o PDF "Relatório por tipo de recebimento" e exporta para Excel.
    Ignora cabeçalhos e trata quebras de linha no nome do Proprietário.
    """
    logger.info("Iniciando a extração inteligente do PDF (Tipo Recebimento)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Regex projetada para capturar: Código, Proprietário, Imóvel, Beneficiário, Forma
    # Ex: "776 ALDAIR ANTUNES DE SOUZA 641 Proprietário-Beneficiário Pessoalmente"
    regex_linha = re.compile(r'^(\d+)\s+(.+?)\s+(\d+)\s+(Proprietário-Beneficiário|\S+)\s+(.+)$', re.IGNORECASE)
    
    linha_atual = None
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            texto = page.extract_text()
            if not texto:
                continue
                
            for linha in texto.split('\n'):
                linha = linha.strip()
                if not linha:
                    continue
                    
                # Filtra os cabeçalhos das páginas
                if ("JORDÃO GESTÃO" in linha or 
                    "CNPJ" in linha or 
                    "Rua Antônio" in linha or 
                    "Telefone" in linha or 
                    "Relatório por tipo" in linha or
                    (linha.startswith("Código") and "Proprietário" in linha)):
                    continue
                    
                match = regex_linha.match(linha)
                
                if match:
                    # Salva a linha anterior se existir
                    if linha_atual:
                        dados_extraidos.append(linha_atual)
                        
                    codigo, prop, imovel, benef, forma = match.groups()
                    linha_atual = {
                        "Código": int(codigo),
                        "Proprietário": prop.strip(),
                        "Imóvel": int(imovel),
                        "Beneficiário": benef.strip(),
                        "Forma": forma.strip()
                    }
                else:
                    # Se não deu match, é uma quebra de linha de uma coluna longa (ex: Proprietário)
                    if linha_atual:
                        linha_atual["Proprietário"] += f" {linha.strip()}"
                        
    # Adiciona a última linha que ficou no buffer
    if linha_atual:
        dados_extraidos.append(linha_atual)
        
    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros encontrados. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    
    # Exporta o Excel bonitinho, sem gerar coluna de index inútil
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo em: {caminho_excel}")
    
    return caminho_excel
