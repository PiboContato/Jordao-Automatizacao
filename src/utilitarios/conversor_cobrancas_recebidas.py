# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path) -> Path | None:
    logger.info("Iniciando a extração inteligente do PDF (Cobranças Recebidas)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Coordenadas X exatas mapeadas a partir do PDF
    vertical_lines = [
        0,      # Imóvel
        30,     # Venciment
        95,     # Comp.
        145,    # Aluguel mês
        205,    # IPTU
        245,    # Cond.
        285,    # IRRF
        320,    # Débitos
        370,    # Créditos
        415,    # Seguro
        455,    # Tarifa
        495,    # Desconto
        540,    # Valor gerado
        595,    # Multa
        635,    # Juros
        680,    # Comp. Pag.
        715,    # Pagamento
        775,    # Valor pago
        9999
    ]
    
    nomes_colunas = [
        "Imóvel", "Venciment", "Competência", "Aluguel mês", "IPTU", "Cond.", "IRRF", 
        "Débitos", "Créditos", "Seguro", "Tarifa", "Desconto", "Valor gerado", 
        "Multa", "Juros", "Comp. Taxa", "Pagamento", "Valor pago"
    ]
    
    with pdfplumber.open(caminho_pdf) as pdf:
        linha_atual = None
        
        for page in pdf.pages:
            words = page.extract_words()
            linhas_visuais = {}
            for w in words:
                top = round(w['top'] / 3) * 3
                if top not in linhas_visuais:
                    linhas_visuais[top] = []
                linhas_visuais[top].append(w)
                
            for top in sorted(linhas_visuais.keys()):
                line_words = linhas_visuais[top]
                
                # Juntar as palavras no texto plano pra identificar o tipo de linha
                texto_linha = " ".join([w['text'] for w in sorted(line_words, key=lambda w: w['x0'])])
                
                if not texto_linha.strip():
                    continue
                    
                if "JORDÃO GESTÃO" in texto_linha or "Relatório de Cobranças" in texto_linha or "Página" in texto_linha:
                    continue
                if "Período" in texto_linha or "Data" in texto_linha or "CPF/CNPJ" in texto_linha:
                    continue
                if texto_linha.startswith("Imóvel"):
                    continue
                if texto_linha.startswith("Histórico"):
                    continue
                if texto_linha.startswith("TAXA DE ADMINISTRAÇÃO"):
                    match = re.search(r'R\$\s*([\d.,]+)', texto_linha)
                    if linha_atual and match:
                        linha_atual["Taxa de Administração"] = match.group(1)
                    continue
                if texto_linha.startswith("Proprietário:"):
                    if linha_atual:
                        linha_atual["Proprietário"] = texto_linha.replace("Proprietário:", "").strip()
                    continue
                if "Total para pagamento:" in texto_linha:
                    continue
                    
                # Extração baseada nas colunas verticais detectadas
                row = [""] * len(nomes_colunas)
                for w in line_words:
                    x0 = w['x0']
                    text = w['text']
                    col_idx = len(nomes_colunas) - 1
                    for i in range(len(nomes_colunas)):
                        if vertical_lines[i] <= x0 < vertical_lines[i+1]:
                            col_idx = i
                            break
                            
                    if row[col_idx]:
                        row[col_idx] += " " + text
                    else:
                        row[col_idx] = text
                        
                row = [c.strip() for c in row]
                
                # Vamos logar as primeiras 20 linhas para debug
                if len(dados_extraidos) < 20:
                    logger.info(f"Linha parseada: {row}")
                
                # Se a linha começa com um número e tem mais campos preenchidos, é a linha principal de dados
                if row[0] and row[0].isdigit(): # Imóvel
                    if linha_atual:
                        dados_extraidos.append(linha_atual)
                    
                    linha_atual = {nomes_colunas[i]: row[i] for i in range(len(nomes_colunas))}
                    linha_atual["Imóvel"] = int(row[0])
                    
                    # Formatar a Competência no formato MM/YYYY se necessário (ex: 6/2026 -> 06/2026)
                    comp_val = str(linha_atual.get("Competência", "")).strip()
                    if comp_val and "/" in comp_val:
                        parts = comp_val.split("/")
                        if len(parts) == 2:
                            linha_atual["Competência"] = f"{parts[0].zfill(2)}/{parts[1]}"

                    linha_atual["Locatário"] = "" # Será preenchido na linha anterior ou corrigido
                    linha_atual["Proprietário"] = ""
                    linha_atual["Taxa de Administração"] = ""
                    linha_atual["Detalhes Histórico"] = ""
                    
                # Se não começa com número, pode ser o Locatário (linha isolada) ou linha de Histórico
                else:
                    if len(line_words) > 0:
                        primeira_palavra = line_words[0]['text']
                        # Se não tem números e é longo, pode ser o nome do locatário
                        if not any(char.isdigit() for char in texto_linha) and "R$" not in texto_linha and len(texto_linha) > 5 and len(line_words) < 10:
                            # Se ja temos uma linha atual preenchida, não é locatário (pois ele vem ANTES da linha de dados)
                            # Então usamos uma variável temporária ou simplesmente deduzimos que o texto anterior à linha de dados era o locatário
                            pass 
                        
                        # Histórico geralmente tem as colunas Histórico, Descrição, D/C, Valor
                        if "R$" in texto_linha and (" C " in texto_linha or " D " in texto_linha or texto_linha.endswith(" C") or texto_linha.endswith(" D")):
                            if linha_atual:
                                if linha_atual["Detalhes Histórico"]:
                                    linha_atual["Detalhes Histórico"] += " | " + texto_linha
                                else:
                                    linha_atual["Detalhes Histórico"] = texto_linha
                                    
        if linha_atual:
            dados_extraidos.append(linha_atual)
            
    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros encontrados.")
    
    # Preencher locatários que ficam soltos no PDF (linha solitária antes do código do imóvel)
    # Como as vezes eles se separam, a estratégia mais inteligente é buscar no PDF novamente
    # Mas uma gambiarra aceitável é ler as linhas em ordem e guardar o locatário pendente
    with pdfplumber.open(caminho_pdf) as pdf:
        texto_completo = "\n".join([page.extract_text(layout=True) for page in pdf.pages])
        linhas_texto = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        
        locatario_pendente = ""
        for i in range(len(linhas_texto)):
            linha = linhas_texto[i]
            # Se é um nome (letras) e a PRÓXIMA linha começar com o Imóvel (ex: 75 01/07/2026)
            if re.match(r'^[A-Za-z]', linha) and "Proprietário" not in linha and "TAXA" not in linha and "Histórico" not in linha:
                if i+1 < len(linhas_texto) and re.match(r'^\d+\s+\d{2}/\d{2}/\d{4}', linhas_texto[i+1]):
                    # Achamos o locatário da próxima linha!
                    imovel_id = linhas_texto[i+1].split()[0]
                    # Encontrar no dicionário extraído
                    for d in dados_extraidos:
                        if str(d["Imóvel"]) == imovel_id and not d["Locatário"]:
                            d["Locatário"] = linha
                            break
                            
    # Reordenar as colunas
    colunas_finais = ["Imóvel", "Locatário", "Proprietário"] + nomes_colunas[1:] + ["Taxa de Administração", "Detalhes Histórico"]
    
    df = pd.DataFrame(dados_extraidos)
    df = df.reindex(columns=colunas_finais)
    
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    logger.info(f"Arquivo Excel salvo em: {caminho_excel}")
    
    return caminho_excel
