-- ============================================
-- Migration 007: Tabelas para Push Notifications
-- Execute este SQL no SQL Editor do Supabase
-- ============================================

-- Tabela para guardar os tokens de notificação (Firebase FCM token ou VAPID)
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    token TEXT NOT NULL UNIQUE, -- Firebase FCM token
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabela para guardar as regras configuradas no frontend (liga/desliga por tipo)
CREATE TABLE IF NOT EXISTS push_config_regras (
    id BIGSERIAL PRIMARY KEY,
    regra_id TEXT UNIQUE NOT NULL, -- ex: 'notificar_erros', 'notificar_sucesso', 'notificar_descartes'
    ativo BOOLEAN NOT NULL DEFAULT true,
    descricao TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Inserir regras padrão
INSERT INTO push_config_regras (regra_id, ativo, descricao) VALUES
('notificar_erros', true, 'Notificar quando ocorrer falha crítica ou erro na extração'),
('notificar_sucesso', true, 'Notificar ao finalizar extrações com sucesso'),
('notificar_descartes', true, 'Notificar sobre linhas descartadas ou formato inválido')
ON CONFLICT (regra_id) DO NOTHING;

-- Adicionar coluna na tabela execucoes para registrar descartes
ALTER TABLE execucoes
ADD COLUMN IF NOT EXISTS total_linhas_descartadas INT DEFAULT 0;
