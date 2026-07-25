from src.ingestao.base_ingestor import BaseIngestor

class Ingestor12PessoasAtivos(BaseIngestor):
    report_id = 12
    table_name = "relatorio_12_pessoas_ativos"
    min_colunas = 8
