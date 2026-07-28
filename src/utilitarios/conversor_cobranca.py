# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path, data_inicio: str = None) -> Path | None:
    logger.info("Iniciando a extração inteligente do PDF (Cobrança)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Linhas verticais exatas (x-coordinates) do PDF para separar colunas com precisão milimétrica.
    vertical_lines = [
        0,    # Início
        37,   # Imóvel
        210,  # Locatário
        270,  # Vencimento
        317,  # Aluguel
        382,  # Aluguel mês
        429,  # Periodo
        496,  # Condomínio
        532,  # IRRF
        568,  # Seguro
        605,  # IPTU
        657,  # Créditos
        703,  # Débitos
        737,  # Tarifa
        783,  # Desconto
        950   # Valor gerado
    ]
    
    colunas_nomes = [
        "Imóvel", "Locatário", "Vencimento", "Aluguel", "Aluguel mês",
        "Periodo", "Condomínio", "IRRF", "Seguro", "IPTU",
        "Créditos", "Débitos", "Tarifa", "Desconto", "Valor gerado"
    ]
    
    with pdfplumber.open(caminho_pdf) as pdf:
        linha_atual = None
        
        for page in pdf.pages:
            words = page.extract_words()
            
            # Agrupar palavras por linha (usando a coordenada Y com tolerância de 3 pixels)
            linhas_visuais = {}
            for w in words:
                top = round(w['top'] / 3) * 3
                if top not in linhas_visuais:
                    linhas_visuais[top] = []
                linhas_visuais[top].append(w)
                
            # Processar cada linha visual de cima para baixo
            for top in sorted(linhas_visuais.keys()):
                line_words = linhas_visuais[top]
                
                # Iniciar array vazio com 15 posições
                row = [""] * 15
                
                for w in line_words:
                    x0 = w['x0']
                    text = w['text']
                    
                    # Encontrar a qual coluna esta palavra pertence
                    col_idx = 14
                    for i in range(15):
                        if vertical_lines[i] <= x0 < vertical_lines[i+1]:
                            col_idx = i
                            break
                            
                    if row[col_idx]:
                        row[col_idx] += " " + text
                    else:
                        row[col_idx] = text
                        
                # Limpar textos
                row = [c.strip() for c in row]
                
                # Pular linhas completamente vazias
                if not any(row):
                    continue
                    
                imovel_str = row[0]
                locatario_str = row[1]
                
                # Ignorar cabeçalhos
                if "JORDÃO GESTÃO" in locatario_str or "Imóvel" in imovel_str or "móvel" in imovel_str or "Página" in locatario_str:
                    continue
                if "CNPJ" in locatario_str or "Telefone" in locatario_str:
                    continue
                if "Cobrança de Aluguel" in row[6] or "Cobrança de Aluguel" in row[5] or (data_inicio and len(data_inicio) >= 7 and f"{int(data_inicio[5:7])} / {data_inicio[:4]}" in row[5]):
                    continue
                    
                # Ignorar a linha de TOTAIS (geralmente tem Imóvel preenchido com o total de itens, mas Locatário vazio, e Valor Gerado gigante)
                if imovel_str and not locatario_str and row[14]:
                    continue
                
                if imovel_str.isdigit():
                    # Salvando a linha anterior, se existir
                    if linha_atual:
                        dados_extraidos.append(linha_atual)
                        
                    # Criando nova linha
                    linha_atual = {colunas_nomes[i]: row[i] for i in range(15)}
                    linha_atual["Imóvel"] = int(imovel_str)
                else:
                    # É uma continuação (ex: nome do locatário quebrou linha)
                    if linha_atual and locatario_str:
                        linha_atual["Locatário"] += f" {locatario_str}"
                        
        # Salvar a última linha processada
        if linha_atual:
            dados_extraidos.append(linha_atual)
            
    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros encontrados. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)

    if data_inicio and len(data_inicio) >= 7:
        mes = data_inicio[5:7]
        ano = data_inicio[:4]
        df.insert(0, 'Competência', f'{mes}/{ano}')
        logger.info(f"Coluna Competência injetada: {mes}/{ano} (data_inicio={data_inicio})")

    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo em: {caminho_excel}")
    
    return caminho_excel
