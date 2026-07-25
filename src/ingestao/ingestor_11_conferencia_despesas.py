from src.ingestao.base_ingestor import BaseIngestor

class Ingestor11ConferenciaDespesas(BaseIngestor):
    report_id = 11
    table_name = "relatorio_11_conferencia_despesas"
    min_colunas = 5
