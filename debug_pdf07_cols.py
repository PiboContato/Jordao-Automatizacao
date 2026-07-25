import pdfplumber
import pandas as pd
from pathlib import Path
import re

pdf_path = Path(r'Relatorios\07 Relatorio de Cobranças Recebidas 2026_06 a 2026_06.pdf')

vertical_lines = [
    0,      # Imóvel
    30,     # Venciment
    95,     # Competência (Comp.)
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
    680,    # Comp. Taxa
    715,    # Pagamento
    775,    # Valor pago
    9999
]

nomes_colunas = [
    "Imóvel", "Venciment", "Competência", "Aluguel mês", "IPTU", "Cond.", "IRRF", 
    "Débitos", "Créditos", "Seguro", "Tarifa", "Desconto", "Valor gerado", 
    "Multa", "Juros", "Comp. Taxa", "Pagamento", "Valor pago"
]

dados_extraidos = []

with pdfplumber.open(pdf_path) as pdf:
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
                continue
            if texto_linha.startswith("Proprietário:"):
                continue
            if "Total para pagamento:" in texto_linha:
                continue
                
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
            
            if row[0] and row[0].isdigit():
                if linha_atual:
                    dados_extraidos.append(linha_atual)
                linha_atual = {nomes_colunas[i]: row[i] for i in range(len(nomes_colunas))}
                print(f"\n=== IMÓVEL {row[0]} ===")
                print(f"  Competência (col2): '{row[2]}'")
                print(f"  Aluguel mês (col3): '{row[3]}'")
                print(f"  Comp. Taxa (col15): '{row[15]}'")
                print(f"  Pagamento (col16): '{row[16]}'")
                if len(dados_extraidos) >= 5:
                    break

if linha_atual:
    dados_extraidos.append(linha_atual)

print(f"\n\nTotal extraído: {len(dados_extraidos)} registros")
if dados_extraidos:
    print("\nPrimeiro registro:")
    for k, v in dados_extraidos[0].items():
        print(f"  {k}: {v}")
