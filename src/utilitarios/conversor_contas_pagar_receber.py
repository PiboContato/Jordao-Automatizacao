# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path) -> Path | None:
    logger.info("Iniciando a extração do PDF (Contas a Pagar/Receber)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        pessoa_atual = "-"
        ultima_linha_texto = ""
        
        # Variáveis temporárias para a linha atual
        reg = {}
        
        estado = 0 # 0: Procurando inicio, 1: Pegar Data 1, 2: Pegar Data 2
        
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            lines = text.split('\n')
            for raw_line in lines:
                linha = raw_line.strip()
                if not linha:
                    continue
                    
                if "JORDÃO GESTÃO DE IMÓVEIS" in linha or "Relatórios de Contas a Pagar" in linha:
                    continue
                if "CPF/CNPJ:" in linha or "Telefone:" in linha:
                    continue
                if "Página" in linha and "de" in linha:
                    continue
                    
                if "Documento" in linha and "Tipo" in linha and "Origem" in linha:
                    # A linha ANTERIOR a essa (que não foi ignorada) é o nome da pessoa!
                    if ultima_linha_texto and not ultima_linha_texto.startswith("Descrição"):
                        pessoa_atual = ultima_linha_texto
                    
                    reg = {
                        "Nome / Pessoa": pessoa_atual,
                        "Nº Documento": "-",
                        "Tipo": "-",
                        "Origem": "-",
                        "Conta Origem": "-",
                        "Conta Destino": "-",
                        "Centro de custo": "-",
                        "Plano de contas": "-",
                        "Vencimento": "-",
                        "Valor Lançado": "-",
                        "Juros": "-",
                        "Multa": "-",
                        "Desconto": "-",
                        "Forma Pag.": "-",
                        "Pagamento": "-",
                        "Valor Pago": "-",
                        "Descrição": "-"
                    }
                    estado = 1
                    continue
                    
                if estado == 1:
                    if linha.startswith("Vencimento") and "Valor lançado" in linha:
                        estado = 2
                        continue
                    
                    # Linha de dados 1 (Tipo, Origem, etc)
                    # Separamos por 2 ou mais espaços
                    partes = re.split(r'\s{2,}', linha)
                    # Ex: ['Entrada', 'locacao', '-', '99469/Banco Itaú', 'ALUGUEIS A RECEBER']
                    # Como faltam colunas (Nº Doc vazio, Centro vazio), tentamos adivinhar por posição/palavra
                    
                    if len(partes) > 0:
                        # Se tem a palavra Entrada ou Saida, sabemos onde começa
                        idx_tipo = -1
                        for i, p in enumerate(partes):
                            if p in ["Entrada", "Saída", "Saida"]:
                                idx_tipo = i
                                break
                        
                        if idx_tipo != -1:
                            reg["Tipo"] = partes[idx_tipo]
                            if idx_tipo > 0:
                                reg["Nº Documento"] = partes[0]
                                
                            if len(partes) > idx_tipo + 1: reg["Origem"] = partes[idx_tipo + 1]
                            if len(partes) > idx_tipo + 2: reg["Conta Origem"] = partes[idx_tipo + 2]
                            if len(partes) > idx_tipo + 3: reg["Conta Destino"] = partes[idx_tipo + 3]
                            if len(partes) > idx_tipo + 4:
                                # O último costuma ser Plano de Contas. Se tiver 6 itens apos o tipo
                                if len(partes) - idx_tipo == 6:
                                    reg["Centro de custo"] = partes[idx_tipo + 4]
                                    reg["Plano de contas"] = partes[idx_tipo + 5]
                                else:
                                    reg["Plano de contas"] = partes[-1]
                    continue
                    
                if estado == 2:
                    if "Descri" in linha:
                        # Extrai a descricao
                        desc = re.sub(r'^.*?Descri[^\s]*\s+', '', linha).strip()
                        reg["Descrição"] = desc
                        # Salva o registro e reseta
                        dados_extraidos.append(reg)
                        estado = 0
                        continue
                    
                    # Linha de dados 2 (Vencimento, Valor, etc)
                    # Ex: ['10/07/2026', '1.755,00', '0,00', '0,00', 'BOLETO', '08/07/2026', '1.755,00']
                    partes = re.split(r'\s{2,}', linha)
                    
                    datas = re.findall(r'\d{2}/\d{2}/\d{4}', linha)
                    valores = re.findall(r'-?[\d.]*,\d{2}', linha)
                    
                    if len(datas) > 0:
                        reg["Vencimento"] = datas[0]
                    if len(datas) > 1:
                        reg["Pagamento"] = datas[1]
                        
                    if len(valores) > 0: reg["Valor Lançado"] = valores[0]
                    if len(valores) > 1: reg["Juros"] = valores[1]
                    if len(valores) > 2: reg["Multa"] = valores[2]
                    if len(valores) > 3: reg["Desconto"] = valores[3]
                    if len(valores) > 4: reg["Valor Pago"] = valores[4]
                    
                    # Forma de Pagamento (geralmente uma palavra sem numeros logo antes da data de pag ou no meio)
                    # Procurar palavras como BOLETO, DINHEIRO, PIX, TRANSFERENCIA
                    formas_pag = [p for p in partes if p.isalpha() and p not in ["-"]]
                    if formas_pag:
                        reg["Forma Pag."] = formas_pag[0]
                        
                    continue

                ultima_linha_texto = linha

    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF (Relatório 15).")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} contas extraídas. Gerando Excel...")
    
    colunas_finais = [
        "Nome / Pessoa", "Nº Documento", "Tipo", "Origem", "Conta Origem", 
        "Conta Destino", "Centro de custo", "Plano de contas", "Vencimento", 
        "Valor Lançado", "Juros", "Multa", "Desconto", "Forma Pag.", 
        "Pagamento", "Valor Pago", "Descrição"
    ]
    df = pd.DataFrame(dados_extraidos, columns=colunas_finais)
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo temporariamente em: {caminho_excel}")
    return caminho_excel
