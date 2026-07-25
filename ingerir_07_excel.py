"""
Ingere todos os Excel do Relatorio 07 com a nova estrutura (Competência).
Execute: python ingerir_07_excel.py
"""
import sys
import glob
sys.path.insert(0, '.')

from pathlib import Path
from src.logger import logger
from src.ingestao import INGESTORES

files = sorted(glob.glob('Relatorios/07 Relatorio*.xlsx'))
logger.info(f"Excel encontrados para ingestão: {len(files)}")

for f in files:
    p = Path(f)
    logger.info(f"Ingerindo: {p.name}")
    try:
        ingestor_cls = INGESTORES[7]
        ingestor = ingestor_cls()
        res = ingestor.executar(p)
        logger.info(f"  -> Inseridos: {res['inseridos']} | Duplicados: {res['duplicados']}")
        if res.get('data_min') and res.get('data_max'):
            logger.info(f"  -> Período: {res['data_min']} até {res['data_max']}")
    except Exception as e:
        logger.error(f"  -> ERRO: {e}")

logger.info("Ingestão concluída!")
