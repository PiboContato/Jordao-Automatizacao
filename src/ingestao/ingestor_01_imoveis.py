from src.ingestao.base_ingestor import BaseIngestor

class Ingestor01Imoveis(BaseIngestor):
    report_id = 1
    table_name = "relatorio_01_imoveis"
    min_colunas = 8
