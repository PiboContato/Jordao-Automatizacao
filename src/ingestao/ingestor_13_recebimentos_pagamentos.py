from src.ingestao.base_ingestor import BaseIngestor

class Ingestor13RecebimentosPagamentos(BaseIngestor):
    report_id = 13
    table_name = "relatorio_13_recebimentos_pagamentos"
    min_colunas = 5
