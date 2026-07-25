-- Migration 003: Criar tabela de logs no Supabase
-- A VM grava logs aqui, o dashboard Render le deste local.

CREATE TABLE IF NOT EXISTS logs (
  id BIGSERIAL PRIMARY KEY,
  nivel TEXT NOT NULL,
  modulo TEXT,
  mensagem TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_nivel ON logs (nivel);
