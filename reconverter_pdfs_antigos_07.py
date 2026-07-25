"""
Reconverte os PDFs antigos do Relatorio 07 para Excel com a nova estrutura de colunas.
Substitui os Excel antigos (com Comp. duplicado) pelos novos (com Competência e Comp. Taxa).
Execute: python reconverter_pdfs_antigos_07.py
"""
import sys
import os
sys.path.insert(0, '.')

import glob
from pathlib import Path
from src.logger import logger
from src.utilitarios.conversor_cobrancas_recebidas import converter_para_excel

# Encontrar todos os PDFs do relatorio 07
pdfs = sorted(glob.glob('Relatorios/07 Relatorio*.pdf'))
print(f"PDFs encontrados: {len(pdfs)}")

for pdf_path in pdfs:
    pdf = Path(pdf_path)
    excel_esperado = pdf.with_suffix('.xlsx')
    
    # Verifica se o Excel correspondente existe
    if not excel_esperado.exists():
        # Tenta variação com acento
        alternativas = list(pdf.parent.glob(f"07 Relat*{pdf.stem[25:]}.xlsx"))
        if alternativas:
            excel_esperado = alternativas[0]
    
    logger.info(f"Reconvertendo: {pdf.name}")
    novo_excel = converter_para_excel(pdf)
    
    if novo_excel:
        # Renomear para o nome do Excel existente correspondente (sobrescreve o antigo)
        nome_destino = pdf.with_suffix('.xlsx')
        if novo_excel != nome_destino:
            import shutil
            shutil.move(str(novo_excel), str(nome_destino))
        logger.info(f"  -> Excel atualizado: {nome_destino.name}")
    else:
        logger.warning(f"  -> FALHA ao converter: {pdf.name}")

logger.info("Reconversão concluída! Todos os Excel do Rel. 07 agora têm 'Competência' como coluna.")
