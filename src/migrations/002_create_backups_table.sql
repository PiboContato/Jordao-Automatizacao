-- ============================================
-- Migration 002: Criar tabela de backups
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

CREATE TABLE IF NOT EXISTS backups_execucoes (
    id BIGSERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    dados JSONB NOT NULL,
    total_registros INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para busca eficiente
CREATE INDEX IF NOT EXISTS idx_backups_table ON backups_execucoes (table_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backups_created ON backups_execucoes (created_at DESC);

-- RLS (Row Level Security) — desabilitado para permitir acesso via service role
ALTER TABLE backups_execucoes ENABLE ROW LEVEL SECURITY;

-- Policy para permitir todas as operações via service role
CREATE POLICY "Allow all operations via service role" ON backups_execucoes
    FOR ALL
    USING (true)
    WITH CHECK (true);
