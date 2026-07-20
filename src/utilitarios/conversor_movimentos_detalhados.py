# -*- coding: utf-8 -*-
import pdfplumber
import pandas as pd
from pathlib import Path
from src.logger import logger
import re

def converter_para_excel(caminho_pdf: Path, data_inicio: str = None) -> Path | None:
    logger.info("Iniciando a extração do PDF (Movimentos Detalhados)...")
    
    if not caminho_pdf.exists():
        logger.error(f"Arquivo PDF não encontrado: {caminho_pdf}")
        return None
        
    dados_extraidos = []
    
    # Extrair mês e ano do nome/filtro
    mes_ano_ref = "-"
    if data_inicio:
        p = data_inicio.split('-')
        mes_ano_ref = f"{p[1]}/{p[0]}"
    
    with pdfplumber.open(caminho_pdf) as pdf:
        contrato_atual = "-"
        locatario_atual = "-"
        endereco_atual = "-"
        gera_boleto_atual = "-"
        
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                linha_limpa = line.strip()
                if not linha_limpa:
                    continue
                    
                # Ignorar cabeçalhos de página
                if "JORDÃO GESTÃO DE IMÓVEIS" in linha_limpa or "Relatório de conferência de movimentos" in linha_limpa:
                    continue
                if "CPF/CNPJ:" in linha_limpa or "Telefone:" in linha_limpa:
                    continue
                if "Histórico" in linha_limpa and "Descrição" in linha_limpa and "Valor" in linha_limpa:
                    continue
                if "Total para pagamento:" in linha_limpa:
                    continue
                if "Página" in linha_limpa and "de" in linha_limpa:
                    continue
                    
                # Detectar novo bloco de contrato
                match_contrato = re.search(r'Contrato:\s*(\d+)\s+Locatário:\s*(.*)', linha_limpa)
                if match_contrato:
                    contrato_atual = match_contrato.group(1).strip()
                    locatario_atual = match_contrato.group(2).strip()
                    # Reseta endereço porque é na próxima linha
                    endereco_atual = "-"
                    gera_boleto_atual = "-"
                    continue
                    
                # Detectar linha de endereço (geralmente logo abaixo do contrato)
                match_endereco = re.search(r'Endereço:\s*(.*?)(?:\s{2,}(Gera boleto|Não gera boleto))?$', linha_limpa)
                if match_endereco:
                    endereco_atual = match_endereco.group(1).strip()
                    if match_endereco.group(2):
                        gera_boleto_atual = match_endereco.group(2).strip()
                    continue
                    
                # Se não for nada acima, pode ser uma linha de tabela de valores
                # Exemplo: ALUGUEL         Ref.30 dias do mes 7/2026         D      R$ 1.450,00
                # Vamos ancorar a direita onde tem D/C e R$ Valor
                match_linha = re.search(r'^(.*?)\s{2,}(.*?)\s+(D|C)\s+(R\$\s*-?[\d.,]+)$', linha_limpa)
                if match_linha:
                    historico = match_linha.group(1).strip()
                    descricao = match_linha.group(2).strip()
                    operacao = match_linha.group(3).strip()
                    valor = match_linha.group(4).strip()
                    
                    registro = {
                        "Mês/Ano": mes_ano_ref,
                        "Contrato": contrato_atual,
                        "Locatário": locatario_atual,
                        "Endereço": endereco_atual,
                        "Gera Boleto?": gera_boleto_atual,
                        "Histórico": historico if historico else "-",
                        "Descrição": descricao if descricao else "-",
                        "Operação": operacao,
                        "Valor": valor
                    }
                    dados_extraidos.append(registro)
                else:
                    # Tenta fallback para caso o histórico ou descrição estejam muito grudados (só 1 espaço)
                    match_fallback = re.search(r'^(.*?)\s+(D|C)\s+(R\$\s*-?[\d.,]+)$', linha_limpa)
                    if match_fallback:
                        # Aqui o grupo 1 tem Histórico + Descrição tudo misturado
                        mistura = match_fallback.group(1).strip()
                        # Vamos quebrar pelo primeiro espaço pra separar Histórico da Descrição
                        partes = mistura.split(' ', 1)
                        historico = partes[0] if len(partes) > 0 else "-"
                        descricao = partes[1] if len(partes) > 1 else "-"
                        
                        operacao = match_fallback.group(2).strip()
                        valor = match_fallback.group(3).strip()
                        
                        registro = {
                            "Mês/Ano": mes_ano_ref,
                            "Contrato": contrato_atual,
                            "Locatário": locatario_atual,
                            "Endereço": endereco_atual,
                            "Gera Boleto?": gera_boleto_atual,
                            "Histórico": historico,
                            "Descrição": descricao,
                            "Operação": operacao,
                            "Valor": valor
                        }
                        dados_extraidos.append(registro)

    if not dados_extraidos:
        logger.warning("Nenhum dado encontrado no PDF para converter para Excel.")
        return None
        
    logger.info(f"Sucesso! {len(dados_extraidos)} linhas de despesas extraídas. Gerando Excel...")
    
    df = pd.DataFrame(dados_extraidos)
    caminho_excel = caminho_pdf.with_suffix('.xlsx')
    df.to_excel(caminho_excel, index=False)
    
    logger.info(f"Arquivo Excel salvo temporariamente em: {caminho_excel}")
    return caminho_excel
