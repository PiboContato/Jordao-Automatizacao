# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path, data_inicio: str = None, data_fim: str = None) -> Path | None:
    logger.info("Iniciando a extração do PDF (Recebimentos e Pagamentos)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Regex projetada para ler as colunas da direita para a esquerda ancorando os tipos
    # [Nome] [Mes / Ano] [Vencimento] [Pagamento] [Tipo] [Operação] [Valor]
    regex_linha = r'^(.*?)\s+(\d{1,2}\s*/\s*\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(entrada|saida)\s+(R\$\s*-?[\d.,]+)$'
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                linha_limpa = line.strip()
                if not linha_limpa:
                    continue
                    
                # Ignorar cabeçalhos e afins
                if "JORDÃO GESTÃO DE IMÓVEIS" in linha_limpa or "Recebimentos e Pagamentos em:" in linha_limpa:
                    continue
                if "CPF/CNPJ:" in linha_limpa or "Telefone:" in linha_limpa:
                    continue
                if "Mês / Ano" in linha_limpa and "Vencimento" in linha_limpa and "Pagamento" in linha_limpa:
                    continue
                if "Página" in linha_limpa and "de" in linha_limpa:
                    continue
                    
                match = re.search(regex_linha, linha_limpa)
                if match:
                    nome = match.group(1).strip()
                    mes_ano = match.group(2).replace(" ", "") # Tira possíveis espaços "5 / 2026" -> "5/2026"
                    vencimento = match.group(3).strip()
                    pagamento = match.group(4).strip()
                    tipo = match.group(5).strip()
                    operacao = match.group(6).strip()
                    valor = match.group(7).strip()
                    
                    registro = {
                        "Nome": nome if nome else "-",
                        "Mês / Ano": mes_ano,
                        "Vencimento": vencimento,
                        "Pagamento": pagamento,
                        "Tipo": tipo if tipo else "-",
                        "Operação": operacao,
                        "Valor": valor
                    }
                    dados_extraidos.append(registro)
                else:
                    # Pode ser a linha de Totalizadores ou alguma que não bateu
                    if "R$" in linha_limpa and re.search(r'\d{2}/\d{2}/\d{4}', linha_limpa):
                         logger.warning(f"Linha ignorada (formato inesperado para regex): {linha_limpa}")

    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter para Excel.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros extraídos. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)
    
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo temporariamente em: {caminho_excel}")
    
    return caminho_excel
