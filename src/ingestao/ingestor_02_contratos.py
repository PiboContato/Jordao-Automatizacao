from src.ingestao.base_ingestor import BaseIngestor

class Ingestor02Contratos(BaseIngestor):
    report_id = 2
    table_name = "relatorio_02_contratos"
    min_colunas = 8
