import sys
import glob
sys.path.insert(0, '.')

from pathlib import Path
from src.logger import logger
from src.ingestao import INGESTORES

def ingerir_06():
    files = sorted(glob.glob('Relatorios/06*.xlsx'))
    logger.info(f"Excel encontrados para ingestão (Relatório 06): {len(files)}")

    for f in files:
        p = Path(f)
        logger.info(f"Ingerindo: {p.name}")
        try:
            ingestor_cls = INGESTORES[6]
            ingestor = ingestor_cls()
            res = ingestor.executar(p)
            logger.info(f"  -> Inseridos: {res['inseridos']} | Duplicados: {res['duplicados']}")
            if res.get('data_min') and res.get('data_max'):
                logger.info(f"  -> Período: {res['data_min']} até {res['data_max']}")
        except Exception as e:
            logger.error(f"  -> ERRO: {e}")

if __name__ == '__main__':
    ingerir_06()
