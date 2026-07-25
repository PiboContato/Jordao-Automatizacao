-- ============================================
-- Migration 004: Criar tabela comandos_remotos
-- Permite acionar o robô da VM remotamente pelo celular (Render)
-- ============================================

CREATE TABLE IF NOT EXISTS comandos_remotos (
    id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- 'extracao_massa', 'extracao_relatorio', 'salvar_agendamento'
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente', -- 'pendente', 'em_execucao', 'concluido', 'falha'
    mensagem TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger para atualizar updated_at automaticamente
DROP TRIGGER IF EXISTS set_updated_at_comandos_remotos ON comandos_remotos;
CREATE TRIGGER set_updated_at_comandos_remotos
    BEFORE UPDATE ON comandos_remotos
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();
