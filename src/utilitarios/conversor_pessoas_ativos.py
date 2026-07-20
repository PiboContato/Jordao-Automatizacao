# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def extrair_campo(texto, regex):
    match = re.search(regex, texto)
    return match.group(1).strip() if match else ""

def converter_para_excel(caminho_pdf: Path, data_filtro: str = None) -> Path | None:
    logger.info("Iniciando a extração do PDF (Pessoas Ativos)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Vamos ler o PDF com layout=True para garantir que campos que ficam na mesma linha 
    # possam ser isolados facilmente, ou podemos apenas usar expressões regulares fortes
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            # Cada pessoa inicia com uma caixa cinza contendo "Nome:"
            # Vamos quebrar o texto da página usando "Nome:" como delimitador de bloco
            # Como a primeira página tem um cabeçalho, a primeira quebra pode não ter dados válidos
            
            blocos = text.split("Nome:")
            
            for bloco in blocos[1:]: # Ignora o que vem antes do primeiro "Nome:"
                if not bloco.strip():
                    continue
                    
                # Reconstruindo a palavra "Nome:" para facilitar o regex
                bloco_texto = "Nome:" + bloco
                
                # Vamos remover quebras de linha duplas ou espaçamentos gigantes para normalizar
                linhas = [linha.strip() for linha in bloco_texto.split('\n') if linha.strip()]
                texto_normalizado = "  ".join(linhas)
                
                # Como usamos layout=True, os espaços entre colunas são mantidos
                # Exemplo: Nome:    ADALBERTO FERREIRA DA GAMA  Endereço:  Rua Quarenta e Três  N° S/N...
                
                nome = extrair_campo(texto_normalizado, r'Nome:\s*(.*?)(?:Endereço:|$)')
                endereco = extrair_campo(texto_normalizado, r'Endereço:\s*(.*?)(?:Nº|N°|Bairro:|$)')
                numero = extrair_campo(texto_normalizado, r'(?:Nº|N°)\s*(.*?)(?:Bairro:|$)')
                
                bairro = extrair_campo(texto_normalizado, r'Bairro:\s*(.*?)(?:Cidade:|$)')
                cidade = extrair_campo(texto_normalizado, r'Cidade:\s*(.*?)(?:Estado:|$)')
                estado = extrair_campo(texto_normalizado, r'Estado:\s*(.*?)(?:CEP:|$)')
                cep = extrair_campo(texto_normalizado, r'CEP:\s*(.*?)(?:Informações|CPF/CNPJ:|$)')
                
                cpf_cnpj = extrair_campo(texto_normalizado, r'CPF/CNPJ:\s*(.*?)(?:Telefone:|RG\s*/\s*Insc|$)')
                telefone = extrair_campo(texto_normalizado, r'Telefone:\s*(.*?)(?:RG\s*/\s*Insc|E-mail:|$)')
                
                rg = extrair_campo(texto_normalizado, r'RG\s*/\s*Insc\.\s*Municipal:\s*(.*?)(?:E-mail:|Data de nascimento:|$)')
                email = extrair_campo(texto_normalizado, r'E-mail:\s*(.*?)(?:Data de nascimento:|Estado civil:|$)')
                
                data_nascimento = extrair_campo(texto_normalizado, r'Data de nascimento:\s*(.*?)(?:Estado civil:|$)')
                estado_civil = extrair_campo(texto_normalizado, r'Estado civil:\s*(.*?)(?:Profissão:|$)')
                
                # Limpeza final em campos que podem engolir trechos indesejados devido à quebra de linha visual
                # Vamos limpar possíveis resíduos de colunas da direita que caíram na regex da esquerda
                if "  " in numero:
                    numero = numero.split("  ")[0].strip()
                if "  " in endereco:
                    endereco = " ".join(endereco.split()).strip()
                if "  " in cpf_cnpj:
                    cpf_cnpj = cpf_cnpj.split("  ")[0].strip()
                if "  " in rg:
                    rg = rg.split("  ")[0].strip()
                    
                # Substituir vazios por "-"
                def limpar(valor):
                    v = valor.strip()
                    return v if v else "-"

                registro = {
                    "Nome": limpar(nome),
                    "Endereço": limpar(endereco),
                    "Número / Complemento": limpar(numero),
                    "Bairro": limpar(bairro),
                    "Cidade": limpar(cidade),
                    "Estado": limpar(estado),
                    "CEP": limpar(cep),
                    "CPF/CNPJ": limpar(cpf_cnpj),
                    "RG / Insc. Municipal": limpar(rg),
                    "Data de Nascimento": limpar(data_nascimento),
                    "Estado Civil": limpar(estado_civil),
                    "Telefone": limpar(telefone),
                    "E-mail": limpar(email)
                }
                
                # Só adiciona se capturou um nome real
                if nome and len(nome) > 1:
                    dados_extraidos.append(registro)

    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter para Excel.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} registros de pessoas extraídos. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)
    
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo temporariamente em: {caminho_excel}")
    
    return caminho_excel
