import pdfplumber
import pandas as pd
import re
from pathlib import Path
from src.logger import logger

def extrair_dado_regex(padrao: str, texto: str) -> str:
    match = re.search(padrao, texto)
    return match.group(1).strip() if match else ""

def extrair_dados_ficha(texto_contrato: str) -> dict:
    """Extrai os campos chave-valor usando as supra colunas (tuplas)."""
    dados = {}
    
    # --- Dados Completos do Contrato ---
    match_codigo = re.search(r'Código:\s*(\d+)', texto_contrato)
    dados[('Dados Completos do Contrato', 'Código')] = match_codigo.group(1).strip() if match_codigo else ""
    
    match_loc = re.search(r'Locatário:\s*(.*?)(?=\n|CPF)', texto_contrato)
    dados[('Dados Completos do Contrato', 'Locatário')] = match_loc.group(1).strip() if match_loc else ""
    
    match_cpf = re.search(r'CPF / CNPJ:\s*([\d\.\-\/]+)', texto_contrato)
    dados[('Dados Completos do Contrato', 'CPF/CNPJ Locatário')] = match_cpf.group(1).strip() if match_cpf else ""
    
    match_end = re.search(r'Endereço completo:\s*(.*?)(?=\n|Telefone)', texto_contrato)
    dados[('Dados Completos do Contrato', 'Endereço')] = match_end.group(1).strip() if match_end else ""
    
    # --- Informações do Contrato ---
    dados[('Informações do Contrato', 'Data de Início')] = extrair_dado_regex(r'Data de início:\s*([\d/]+)', texto_contrato)
    dados[('Informações do Contrato', 'Data Término')] = extrair_dado_regex(r'Data término:\s*([\d/]+)', texto_contrato)
    dados[('Informações do Contrato', 'Vencimento')] = extrair_dado_regex(r'Vencimento:\s*(\d+)', texto_contrato)
    
    # --- Informação do Imóvel ---
    dados[('Informação do Imóvel', 'Código:')] = extrair_dado_regex(r'Informações do imóvel[\s\S]*?Código:\s*(\d+)', texto_contrato)
    dados[('Informação do Imóvel', 'Finalidade Imóvel')] = extrair_dado_regex(r'Finalidade:\s*([A-Za-z]+)', texto_contrato)
    
    # --- Proprietário ---
    match_prop = re.search(r'Nome:\s*(.*?)(?=\n|CPF)', texto_contrato)
    dados[('Proprietário', 'Nome')] = match_prop.group(1).strip() if match_prop else ""
    
    dados[('Proprietário', 'Taxa de Administração (%)')] = extrair_dado_regex(r'Taxa de administração:\s*%\s*([\d,]+)', texto_contrato)
    dados[('Proprietário', 'Percentual de Iptu')] = extrair_dado_regex(r'Percentual de taxa de iptu:\s*([\d\.,]+)', texto_contrato)
    
    match_conta = re.search(r'Conta bancária:\s*(.*?)(?=\n|$)', texto_contrato)
    dados[('Proprietário', 'Conta Bancaria')] = match_conta.group(1).strip() if match_conta else ""
    
    # Validação Básica: Se não achou Código nem Locatário, a ficha é lixo
    if not dados[('Dados Completos do Contrato', 'Código')] and not dados[('Dados Completos do Contrato', 'Locatário')]:
        return None
        
    return dados

def converter_para_excel(caminho_pdf: Path | str) -> Path | None:
    caminho_pdf = Path(caminho_pdf)
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado para conversão: {caminho_pdf}")
        return None

    logger.info("Iniciando a leitura do PDF via pdfplumber (Módulo Isolado)...")
    try:
        texto_completo = ""
        with pdfplumber.open(caminho_pdf) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
        
        if not texto_completo.strip():
            logger.warning("O PDF está vazio ou não possui texto extraível.")
            return None
            
        logger.info("Texto extraído com sucesso. Fatiando as fichas...")
        
        # Fatiamento Robusto: Corta o texto apenas quando acha o combo: "Código: (número)" seguido de "Locatário:"
        texto_completo = re.sub(r'(Código:\s*\d+[\s\n]+Locatário:)', r'---NOVO_CONTRATO---\1', texto_completo)
        blocos = texto_completo.split('---NOVO_CONTRATO---')
        
        dados_extraidos = []
        for bloco in blocos:
            if "Locatário:" not in bloco:
                continue 
                
            ficha = extrair_dados_ficha(bloco)
            if ficha:
                dados_extraidos.append(ficha)
                
        if not dados_extraidos:
            logger.warning("Nenhum contrato pôde ser montado. O Regex pode precisar de ajustes.")
            return None
            
        # Exportar para Excel via Pandas
        logger.info(f"Sucesso! {len(dados_extraidos)} contratos encontrados. Gerando Excel com Supra Colunas...")
        df = pd.DataFrame(dados_extraidos)
        
        # Ativar Supra Colunas no Excel
        df.columns = pd.MultiIndex.from_tuples(df.columns)
        
        caminho_excel = caminho_pdf.with_suffix('.xlsx')
        
        # Correção Definitiva do Bug do Pandas: 
        # Exportamos com o index inútil (para não dar erro no Pandas)
        df.to_excel(caminho_excel, index=True)
        
        # E usamos o bisturi (openpyxl) para amputar a primeira coluna (o index) cirurgicamente!
        import openpyxl
        wb = openpyxl.load_workbook(caminho_excel)
        ws = wb.active
        ws.delete_cols(1)
        wb.save(caminho_excel)
        
        logger.info(f"Arquivo Excel salvo (formatado perfeitamente) em: {caminho_excel}")
        
        return caminho_excel
        
    except Exception as e:
        logger.error(f"FALHA na conversão de PDF para Excel (o PDF original continua salvo): {e}")
        return None
