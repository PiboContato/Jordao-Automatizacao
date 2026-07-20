-- ============================================
-- Migration 001: Criar tabelas dos 15 relatórios
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

-- Helper: função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Helper: função para criar tabela de relatório com estrutura padrão
DO $$
DECLARE
  table_name TEXT;
  sql_text TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'relatorio_01_imoveis',
    'relatorio_02_contratos',
    'relatorio_03_fluxo_caixa',
    'relatorio_04_ficha_contrato',
    'relatorio_05_tipo_recebimento',
    'relatorio_06_cobranca_aluguel',
    'relatorio_07_cobrancas_recebidas',
    'relatorio_08_contratos_x_cobrancas',
    'relatorio_09_comissao_cobrancas',
    'relatorio_10_pagamentos_beneficiarios',
    'relatorio_11_conferencia_despesas',
    'relatorio_12_pessoas_ativos',
    'relatorio_13_recebimentos_pagamentos',
    'relatorio_14_movimentos_detalhados',
    'relatorio_15_contas_pagar_receber'
  ] LOOP
    sql_text := format(
      'CREATE TABLE IF NOT EXISTS %I (
        id BIGSERIAL PRIMARY KEY,
        dados JSONB NOT NULL DEFAULT ''{}''::jsonb,
        data_extracao DATE NOT NULL DEFAULT CURRENT_DATE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );',
      table_name
    );
    EXECUTE sql_text;

    -- Índice para busca por data de extração
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_%I_data ON %I (data_extracao DESC);',
      table_name, table_name
    );

    -- Índice GIN para busca em JSONB
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_%I_dados ON %I USING GIN (dados);',
      table_name, table_name
    );

    -- Trigger para updated_at automático
    EXECUTE format(
      'CREATE TRIGGER trg_%I_updated_at
        BEFORE UPDATE ON %I
        FOR EACH ROW
        EXECUTE FUNCTION trigger_set_updated_at();',
      table_name, table_name
    );
  END LOOP;
END;
$$;

-- ============================================
-- Tabela de auditoria de execuções
-- ============================================
CREATE TABLE IF NOT EXISTS execucoes (
    id BIGSERIAL PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('extracao', 'ingestao', 'completo')),
    status TEXT NOT NULL CHECK (status IN ('iniciou', 'sucesso', 'falha')),
    relatorios_processados INT DEFAULT 0,
    relatorios_sucesso INT DEFAULT 0,
    relatorios_falha INT DEFAULT 0,
    total_linhas_inseridas INT DEFAULT 0,
    mensagem TEXT,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_execucoes_tipo ON execucoes (tipo, status);
CREATE INDEX IF NOT EXISTS idx_execucoes_inicio ON execucoes (iniciado_em DESC);
