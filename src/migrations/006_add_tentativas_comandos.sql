-- Migration: adiciona coluna tentativas para backoff de comandos órfãos
ALTER TABLE comandos_remotos ADD COLUMN IF NOT EXISTS tentativas INT DEFAULT 0;
COMMENT ON COLUMN comandos_remotos.tentativas IS 'Número de tentativas de processamento (incrementado a cada retry no ouvinte).';
