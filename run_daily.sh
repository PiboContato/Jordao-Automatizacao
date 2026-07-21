#!/bin/bash
# ============================================
# run_daily.sh — Script de execução diária
# Uso no cron: 0 6 * * * /caminho/projeto/run_daily.sh
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

DATE_TAG=$(date +%Y-%m-%d)
LOG_FILE="$LOG_DIR/daily_${DATE_TAG}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Execução diária: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_DIR/daily_${DATE_TAG}.log"

# Ativar virtualenv (Linux/Mac)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtualenv ativado." | tee -a "$LOG_FILE"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "Virtualenv (Windows) ativado." | tee -a "$LOG_FILE"
else
    echo "AVISO: venv não encontrado, usando Python do sistema." | tee -a "$LOG_FILE"
fi

# Carregar variáveis de ambiente
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
    echo ".env carregado." | tee -a "$LOG_FILE"
else
    echo "ERRO: Arquivo .env não encontrado!" | tee -a "$LOG_FILE"
    exit 1
fi

# Calcular período: últimos 30 dias
DATA_INICIO=$(date -d "30 days ago" +%Y-%m-%d)
DATA_FIM=$(date +%Y-%m-%d)
echo "Período: $DATA_INICIO a $DATA_FIM" | tee -a "$LOG_FILE"

# Executar orquestrador
echo "Iniciando orquestrador..." | tee -a "$LOG_FILE"

python -m src.orquestrador --data-inicio "$DATA_INICIO" --data-fim "$DATA_FIM" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo "========================================" | tee -a "$LOG_FILE"
    echo "✅ Execução concluída com sucesso!" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
else
    echo "========================================" | tee -a "$LOG_FILE"
    echo "❌ Execução falhou (exit code: $EXIT_CODE)" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
fi

# Limpar logs antigos (manter últimos 30 dias)
find "$LOG_DIR" -name "daily_*.log" -mtime +30 -delete 2>/dev/null || true

exit $EXIT_CODE
