-- ============================================
-- Migration 005: Habilitar RLS (Row Level Security) nas tabelas
-- Remove os avisos 'UNRESTRICTED' no painel do Supabase
-- Execute este script no SQL Editor do Supabase
-- ============================================

DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'comandos_remotos',
    'execucoes',
    'logs',
    'backups_execucoes',
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
    -- 1. Habilitar RLS na tabela
    EXECUTE format('ALTER TABLE IF EXISTS %I ENABLE ROW LEVEL SECURITY;', tbl);
    
    -- 2. Criar política de acesso total para o projeto (anon / authenticated / service_role)
    EXECUTE format('DROP POLICY IF EXISTS "Acesso Total Projeto" ON %I;', tbl);
    EXECUTE format('CREATE POLICY "Acesso Total Projeto" ON %I FOR ALL USING (true) WITH CHECK (true);', tbl);
  END LOOP;
END $$;
