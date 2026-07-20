# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path, data_filtro: str = None) -> Path | None:
    logger.info("Iniciando a extração do PDF (Conferência de Despesas)...")
    
    mes_ano = ""
    if data_filtro and len(data_filtro) >= 7:
        mes_ano = f"{data_filtro[5:7]}/{data_filtro[0:4]}"
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    contexto = {
        "Locador": "",
        "Locatário": "",
        "Imovel": "",
        "Contrato": ""
    }
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            # extract_text com layout=True mantém o alinhamento visual com espaços
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                    
                # Ignorar cabeçalhos de página e irrelevantes
                if "JORDÃO GESTÃO DE IMÓVEIS" in line or "RELATÓRIO DE CONFERÊNCIA" in line:
                    continue
                if "Telefone:" in line or "CPF/CNPJ:" in line or re.match(r'^\s*\d+\s+/\s+\d+\s*$', line):
                    continue
                    
                # Ignorar cabeçalho da tabela
                if "Histórico" in line and "Descrição" in line and "Operação" in line:
                    continue
                    
                # Identificar bloco de Locador e Imóvel
                # Exemplo: Locador:      ALEXANDRE PEREIRA DE SOUSA                    Imóvel:   495
                if "Locador:" in line and "Imóvel:" in line:
                    # Quebrar pelo nome do campo
                    parte1, parte2 = line.split("Imóvel:")
                    locador = parte1.replace("Locador:", "").strip()
                    imovel = parte2.strip()
                    contexto["Locador"] = locador
                    contexto["Imovel"] = imovel
                    continue
                    
                # Identificar bloco de Locatário e Contrato
                # Exemplo: Locatário:    JOÃO VITOR DA SILVA JOAQUIM                   Contrato: 231
                if "Locatário:" in line and "Contrato:" in line:
                    parte1, parte2 = line.split("Contrato:")
                    locatario = parte1.replace("Locatário:", "").strip()
                    contrato = parte2.strip()
                    contexto["Locatário"] = locatario
                    contexto["Contrato"] = contrato
                    continue
                    
                # Processar as linhas de dados (Tabela) usando Regex robusto para o final da linha
                if re.search(r'\d{2}/\d{2}/\d{4}', line):
                    # O final da linha tem um formato muito padronizado: [Operação] [Data Inicio] [Data Fim] [Valor]
                    # Exemplo Operação: LOCATÁRIO > IMOBILIÁRIA, LOCADOR > LOCATÁRIO, etc.
                    # Exemplo Data Fim: Indeterminado ou 31/07/2026
                    regex = r'^(.*?)\s+(LOCATÁRIO > LOCADOR|LOCADOR > IMOBILIÁRIA|LOCADOR > LOCATÁRIO|IMOBILIÁRIA > LOCADOR|LOCATÁRIO > IMOBILIÁRIA)\s+(\d{2}/\d{2}/\d{4})\s+(Indeterminado|\d{2}/\d{2}/\d{4})\s+([\d.,]+)$'
                    match = re.search(regex, line.strip())
                    
                    if match:
                        textos_iniciais = match.group(1).strip()
                        operacao = match.group(2).strip()
                        data_inicio = match.group(3).strip()
                        data_fim = match.group(4).strip()
                        valor = match.group(5).strip()
                        
                        # Tentar separar Histórico e Descrição por 2 ou mais espaços
                        partes_texto = re.split(r'\s{2,}', textos_iniciais)
                        if len(partes_texto) >= 2:
                            historico = partes_texto[0].strip()
                            descricao = " ".join(partes_texto[1:]).strip()
                        else:
                            # Se não tiver espaço duplo claro, coloca no Histórico e deixa a Descrição vazia ou similar
                            # Baseado no PDF, normalmente a primeira palavra ou primeiras palavras são o Histórico
                            historico = textos_iniciais
                            descricao = ""
                            
                        registro = {
                            "Locador": contexto["Locador"],
                            "Locatário": contexto["Locatário"],
                            "Imovel": contexto["Imovel"],
                            "Contrato": contexto["Contrato"],
                            "Histórico": historico,
                            "Descrição": descricao,
                            "Operação": operacao,
                            "Data inicio": data_inicio,
                            "Data Fim": data_fim,
                            "Valor": valor,
                            "Data Despesa": mes_ano
                        }
                        dados_extraidos.append(registro)
                    else:
                        logger.warning(f"Linha de dados ignorada (formato inesperado para regex): {line.strip()}")

    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter para Excel.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros extraídos. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)
    
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo temporariamente em: {caminho_excel}")
    
    return caminho_excel
