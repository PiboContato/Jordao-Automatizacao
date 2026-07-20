from src.ingestao.ingestor_01_imoveis import Ingestor01Imoveis
from src.ingestao.ingestor_02_contratos import Ingestor02Contratos
from src.ingestao.ingestor_03_fluxo_caixa import Ingestor03FluxoCaixa
from src.ingestao.ingestor_04_ficha_contrato import Ingestor04FichaContrato
from src.ingestao.ingestor_05_tipo_recebimento import Ingestor05TipoRecebimento
from src.ingestao.ingestor_06_cobranca_aluguel import Ingestor06CobrancaAluguel
from src.ingestao.ingestor_07_cobrancas_recebidas import Ingestor07CobrancasRecebidas
from src.ingestao.ingestor_08_contratos_x_cobrancas import Ingestor08ContratosXCobrancas
from src.ingestao.ingestor_09_comissao_cobrancas import Ingestor09ComissaoCobrancas
from src.ingestao.ingestor_10_pagamentos_beneficiarios import Ingestor10PagamentosBeneficiarios
from src.ingestao.ingestor_11_conferencia_despesas import Ingestor11ConferenciaDespesas
from src.ingestao.ingestor_12_pessoas_ativos import Ingestor12PessoasAtivos
from src.ingestao.ingestor_13_recebimentos_pagamentos import Ingestor13RecebimentosPagamentos
from src.ingestao.ingestor_14_movimentos_detalhados import Ingestor14MovimentosDetalhados
from src.ingestao.ingestor_15_contas_pagar_receber import Ingestor15ContasPagarReceber

INGESTORES = {
    1: Ingestor01Imoveis,
    2: Ingestor02Contratos,
    3: Ingestor03FluxoCaixa,
    4: Ingestor04FichaContrato,
    5: Ingestor05TipoRecebimento,
    6: Ingestor06CobrancaAluguel,
    7: Ingestor07CobrancasRecebidas,
    8: Ingestor08ContratosXCobrancas,
    9: Ingestor09ComissaoCobrancas,
    10: Ingestor10PagamentosBeneficiarios,
    11: Ingestor11ConferenciaDespesas,
    12: Ingestor12PessoasAtivos,
    13: Ingestor13RecebimentosPagamentos,
    14: Ingestor14MovimentosDetalhados,
    15: Ingestor15ContasPagarReceber,
}
