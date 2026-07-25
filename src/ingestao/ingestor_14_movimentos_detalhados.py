from src.ingestao.base_ingestor import BaseIngestor

class Ingestor14MovimentosDetalhados(BaseIngestor):
    report_id = 14
    table_name = "relatorio_14_movimentos_detalhados"
    min_colunas = 5
