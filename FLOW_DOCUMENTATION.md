# Documentação de Fluxo — Robô Jordão Automatização

> **IMPORTANTE:** Qualquer alteração na rotina do robô **DEVE** ser anotada neste arquivo,
> incluindo data, descrição da mudança e motivo. Isso é de extrema importância para
> acompanhamento e auditoria de todas as modificações realizadas.

---

## Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura e Arquivos Principais](#2-arquitetura-e-arquivos-principais)
3. [Três Rotas de Execução](#3-três-rotas-de-execução)
4. [Fluxo Completo Passo a Passo](#4-fluxo-completo-passo-a-passo)
5. [Tabela de Relatórios — Comportamento Detalhado](#5-tabela-de-relatórios--comportamento-detalhado)
6. [Classificação de Dados: Snapshot vs Temporal](#6-classificação-de-dados-snapshot-vs-temporal)
7. [Regras de Coluna de Data por Relatório](#7-regras-de-coluna-de-data-por-relatório)
8. [Mecanismo de Preservação de Histórico](#8-mecanismo-de-preservação-de-histórico)
9. [Sistema de Auditoria (Tabela `execucoes`)](#9-sistema-de-auditoria-tabela-execucoes)
10. [Tratamento de Erros e Resiliência](#10-tratamento-de-erros-e-resiliência)
11. [Configuração e Agendamento](#11-configuração-e-agendamento)
12. [Logs e Monitoramento](#12-logs-e-monitoramento)
13. [Registro de Alterações](#13-registro-de-alterações)

---

## 1. Visão Geral do Sistema

O robô automatiza a extração de **15 relatórios** do sistema Jordão Gestão de Imóveis
e os ingere no **Supabase** (PostgreSQL). O sistema roda em uma VM Windows com agendamento
automático via Flask + timer em segundo plano.

**Fluxo resumido:**
```
Jordão Gestão (web) → Playwright extrai Excel → Processamento local → Supabase (PostgreSQL)
```

---

## 2. Arquitetura e Arquivos Principais

| Arquivo | Função |
|---|---|
| `app.py` | Flask app — Dashboard web, processamento manual, motor de agendamento |
| `src/orquestrador.py` | Coordenador — extração + ingestão via CLI ou chamada programática |
| `src/base_agente.py` | Agente Playwright — login, navegação, extração dos relatórios |
| `src/ingestao/base_ingestor.py` | Classe base de ingestão — limpeza, validação, inserção no Supabase |
| `src/ingestao/__init__.py` | Registry — mapeia report_id → classe Ingestor |
| `src/ingestao/ingestor_XX_*.py` | 15 ingestores individuais (todos herdam BaseIngestor) |
| `src/utils.py` | Utilitários — `calcular_datas_padrao()`, limpeza de arquivos |
| `src/config.py` | Configurações centralizadas (variáveis de ambiente) |
| `src/logger.py` | Logging estruturado (console + arquivo rotativo + memória para UI) |
| `run_daily.sh` | Script de execução diária (cron) |
| `agendamento.json` | Horários de agendamento automático |

---

## 3. Três Rotas de Execução

### Rota 1: Manual (Flask Dashboard)

**Trigger:** Usuário clica "Iniciar" no dashboard web.

```
Dashboard → POST /iniciar → iniciar_robo() → processar_fila()
```

**Fluxo detalhado:**
1. `app.py:iniciar_robo()` — Valida fila, cria thread
2. `app.py:processar_fila()` — Chama `base_agente.processar_fila_em_massa()` para extração
3. Após extração, itera sobre cada relatório na fila:
   - Report 10: registra sucesso/falha (apenas PDF, sem ingestão)
   - Demais: chama `_encontrar_excel_reports(rid)` → `ingestor.executar(excel_path)` para cada Excel
4. `_registrar_execucao()` chamada **por arquivo Excel** — registra na tabela `execucoes`

**Variável de controle:** `status_robo["rodando"]` (True enquanto processa)

### Rota 2: Automática (Timer em segundo plano)

**Trigger:** Horário programado em `agendamento.json` (ex: 06:00, 07:00, etc.)

```
motor_agendamento() → calcula datas → preenche fila → processar_fila()
```

**Fluxo detalhado:**
1. `app.py:motor_agendamento()` — Loop infinito, verifica a cada 30 segundos
2. Compara `HH:MM` atual com horários do `agendamento.json`
3. Se horário bate e robô não está rodando:
   - Chama `calcular_datas_padrao()` para definir datas por relatório
   - Preenche `status_robo["fila"]` com todos os relatórios (exceto 3, 9, 10)
   - Inicia thread com `processar_fila()`
4. A partir daqui, **comportamento idêntico à Rota 1**

**Proteção:** Se `status_robo["rodando"]` é True, pula o disparo (evita sobreposição).

### Rota 3: CLI (Command Line Interface)

**Trigger:** `python -m src.orquestrador` via `run_daily.sh` ou cron.

```
run_daily.sh → python -m src.orquestrador → executar()
```

**Fluxo detalhado:**
1. `orquestrador:executar()` — Função principal
2. Testa conexão Supabase
3. Registra início na tabela `execucoes`
4. Calcula datas via `calcular_datas_padrao()`
5. Executa extração via `base_agente.processar_fila_em_massa()`
6. Para cada relatório com extração bem-sucedida:
   - Report 10: registra sucesso (apenas PDF)
   - Demais: `_encontrar_excel_reports(rid)` → loop por cada Excel → `ingestor.executar()`
7. Registra resultado final na tabela `execucoes`
8. Limpa arquivos locais antigos (>7 dias)

**Argumentos CLI:**
- `--data-inicio YYYY-MM-DD` — Data início específica
- `--data-fim YYYY-MM-DD` — Data fim específica
- `--report-id N` — Rodar apenas relatório N (1-15)
- `--skip-extract` — Pular extração, apenas ingerir Excel existente

---

## 4. Fluxo Completo Passo a Passo

```
┌─────────────────────────────────────────────────────────────────┐
│                     INÍCIO DA EXECUÇÃO                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. CONEXÃO SUPABASE                                           │
│     testar_conexao() — verifica se Supabase está acessível     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. CÁLCULO DE DATAS                                           │
│     calcular_datas_padrao() define datas por grupo:            │
│     • Grupo A (1,2,4,5,8,12): mês atual, sem data_fim         │
│     • Grupo B (13,15): primeiro → último dia do mês atual      │
│     • Grupo C/D (6,7,11,14): mês anterior → último dia atual   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. PREPARAÇÃO DA FILA                                         │
│     Lista de relatórios a processar (exclui 3, 9, 10 se CLI)  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. EXTRAÇÃO (Playwright)                                      │
│     processar_fila_em_massa():                                 │
│     • Abre navegador Chromium (headless configurável)          │
│     • Faz login no Jordão Gestão                               │
│     • Para cada relatório na fila:                              │
│       → Importa módulo extrator (src.relatorios.relatorio_XX) │
│       → Chama extrair(page, data_inicio, data_fim)            │
│       → Valida arquivo Excel gerado                            │
│       → Move para pasta destino com nome padronizado           │
│       • Relatórios 6, 11, 14: itera mês a mês                 │
│         (gera múltiplos arquivos Excel)                        │
│       → Máximo 3 tentativas por relatório                      │
│       → Falha de 1 relatório NÃO bloqueia os próximos         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. PÓS-EXTRAÇÃO — Análise de Resultados                       │
│     Para cada report_id na fila:                                │
│     • Verifica status no historico (sucesso/falha)             │
│     • Se sucesso: busca Excel(s) na pasta destino              │
│     • Se falha: registra falha na auditoria                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. INGESTÃO NO SUPABASE                                       │
│     Para cada relatório com extração OK:                       │
│     • Report 10: pula (apenas PDF)                             │
│     • Demais:                                                  │
│       → _encontrar_excel_reports(rid) — busca TODOS os .xlsx  │
│       → Para CADA arquivo Excel:                               │
│         1. ingestor.ler_excel() — lê com pandas/openpyxl      │
│         2. ingestor.validar_linhas() — remove linhas sem data  │
│         3. ingestor.df_para_registros() — converte para dict   │
│         4. ingestor.limpar_periodo(df) — limpa dados antigos   │
│         5. ingestor.inserir_supabase() — insere em lotes 100   │
│         6. _registrar_execucao() — registra na tabela execucoes│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. RESULTADO FINAL                                            │
│     Registra resumo na tabela execucoes:                       │
│     • total de relatórios processados                          │
│     • quantos sucesso / falha                                  │
│     • total de linhas inseridas                                │
│     • tempo total de execução                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. LIMPEZA                                                    │
│     limpar_arquivos_antigos() — remove Excels >7 dias          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Tabela de Relatórios — Comportamento Detalhado

| ID | Nome | Status | Tipo | Coluna de Data | Tabela Supabase | Extração Mensal |
|---|---|---|---|---|---|---|
| 01 | Relatório de Imóveis | **ATIVO** | Snapshot | — | `relatorio_01_imoveis` | Não |
| 02 | Relatório de Contratos | **ATIVO** | Snapshot | — | `relatorio_02_contratos` | Não |
| 03 | Relatório de Fluxo de Caixa | **DESATIVADO** | — | — | — | — |
| 04 | Relatório Ficha do Contrato | **ATIVO** | Snapshot | — | `relatorio_04_ficha_contrato` | Não |
| 05 | Relatório por Tipo de Recebimento | **ATIVO** | Snapshot | — | `relatorio_05_tipo_recebimento` | Não |
| 06 | Relatório de Cobrança de Aluguel e IPTU | **ATIVO** | Temporal | Mes/Ano | `relatorio_06_cobranca_aluguel` | **SIM** |
| 07 | Relatório de Cobranças Recebidas | **ATIVO** | Temporal | Pagamento | `relatorio_07_cobrancas_recebidas` | Não |
| 08 | Relatório de Contratos x Cobranças | **ATIVO** | Snapshot | — | `relatorio_08_contratos_x_cobrancas` | Não |
| 09 | Relatório de Comissão das Cobranças | **DESATIVADO** | — | — | — | — |
| 10 | Relatório de Pagamentos aos Beneficiários | **ATIVO** | PDF only | — | — (sem ingestão) | Não |
| 11 | Relatório de Conferência de Despesas | **ATIVO** | Temporal | Data Despesa | `relatorio_11_conferencia_despesas` | **SIM** |
| 12 | Relatório de Pessoas Ativos | **ATIVO** | Snapshot | — | `relatorio_12_pessoas_ativos` | Não |
| 13 | Relatório de Recebimentos e Pagamentos | **ATIVO** | Temporal | Pagamento | `relatorio_13_recebimentos_pagamentos` | Não |
| 14 | Relatório de Conferência de Movimentos Detalhado | **ATIVO** | Temporal | Mes/Ano | `relatorio_14_movimentos_detalhados` | **SIM** |
| 15 | Relatório de Contas a Pagar/Receber | **ATIVO** | Temporal | Vencimento | `relatorio_15_contas_pagar_receber` | Não |

### Definições

- **Snapshot (Estático):** Dados completos de um período. A tabela inteira é apagada a cada execução.
- **Temporal:** Dados acumulados. Apenas o período específico é apagado, preservando meses anteriores.
- **Extração Mensal:** O robô itera mês a mês, gerando um Excel separado por mês.
- **PDF only:** Relatório gera apenas PDF, sem ingestão de dados estruturados.

---

## 6. Classificação de Dados: Snapshot vs Temporal

### Snapshots (limpeza total — `limpar_tabela()`)

Relatórios **1, 2, 4, 5, 8, 12** são considerados "fotos" do momento atual.
A cada execução bem-sucedida, a tabela inteira é apagada e reescrita.

**Lógica em `base_ingestor.py:limpar_periodo()` (linha 70):**
```python
if self.report_id in [1, 2, 4, 5, 8, 12]:
    self.limpar_tabela()  # Apaga TUDO
    return
```

**Por quê?** Esses relatórios não têm data de referência confiável.
Exemplo: "Lista de imóveis" — se executarmos hoje e amanhã, queremos apenas a lista atual.

### Temporais (limpeza por período — `limpar_periodo()`)

Relatórios **6, 7, 11, 13, 14, 15** preservam histórico.
Apenas os meses/anos presentes no novo Excel são apagados antes da inserção.

**Lógica:**
1. Detecta coluna de data principal (prioridade por relatório)
2. Extrai meses/anos únicos dos dados novos
3. Para cada mês: `DELETE WHERE dados->>coluna LIKE '%MM/YYYY%'`
4. Insere novos dados (preservando meses anteriores não presentes no Excel)

### Regra de Fallback

Se o relatório NÃO está na lista de snapshots E não tem coluna de data detectável,
o sistema assume snapshot por segurança (limpa tudo). Isso evita duplicatas acidentais.

---

## 7. Regras de Coluna de Data por Relatório

A detecção da coluna de data é **crítica** para o funcionamento correto.
Cada relatório tem uma regra específica na cascata de detecção:

```
Prioridade de detecção (em ordem):
1. relatorio_15 → coluna "Vencimento"
2. relatorio_13 → coluna "Pagamento"
3. relatorio_11 → coluna "Data Despesa"
4. relatorio_07 → coluna "Pagamento"
5. relatorio_06 → coluna "Mes/Ano"
6. relatorio_14 → coluna "Mes/Ano"
7. Fallback      → primeira coluna "Pagamento" encontrada
8. Fallback      → primeira coluna "Vencimento" encontrada
9. Fallback      → primeira coluna de data qualquer
```

**Normalização:** Antes da comparação, os nomes das colunas passam por `_normalizar_texto()`:
- Converte para minúsculas
- Remove acentos (Mês/Ano → mes/ano)
- Normaliza espaços (Mes / Ano → mes/ano)

**Arquivo:** `src/ingestao/base_ingestor.py` — função `_normalizar_texto()` (linha 13)

Essa cascata está replicada em **3 lugares** (mantidos sincronizados):
1. `limpar_periodo()` — para decidir qual coluna usar na limpeza
2. `validar_linhas()` — para decidir qual coluna validar (remover linhas sem data)
3. `executar()` — para decidir qual coluna usar nas estatísticas do banco

---

## 8. Mecanismo de Preservação de Histórico

### Como funciona a preservação para relatórios temporais

**Exemplo com Relatório 15 (Contas a Pagar/Receber):**

```
Execução 1 (Janeiro):
  Excel contém: Jan/2026, Jan/2026, Jan/2026
  → limpar_periodo(): limpa apenas "01/2026" no Supabase
  → Insere 3 linhas de Jan/2026
  → Supabase: [Jan/2026, Jan/2026, Jan/2026]

Execução 2 (Fevereiro):
  Excel contém: Jan/2026, Fev/2026, Fev/2026
  → limpar_periodo(): limpa "01/2026" e "02/2026"
  → Insere Jan/2026 e Fev/2026
  → Supabase: [Jan/2026, Jan/2026, Fev/2026, Fev/2026]
  → HISTÓRICO PRESERVADO: Janeiro continua lá
```

**Contraste com Snapshots (Relatório 01 - Imóveis):**

```
Execução 1:
  → limpar_tabela(): APAGA TUDO
  → Insere dados atuais
  → Supabase: [dados de hoje]

Execução 2:
  → limpar_tabela(): APAGA TUDO
  → Insere dados novos
  → Supabase: [dados de amanhã]
  → SEM histórico (correto para este tipo de relatório)
```

### Relatórios com Extração Mensal (6, 11, 14)

Esses relatórios itera mês a mês durante a extração. Se `data_inicio` = 2025-12 e `data_fim` = 2026-01, o robô gera:
- `06 Relatorio de Cobranca de Aluguel e IPTU_20251201.xlsx`
- `06 Relatorio de Cobranca de Aluguel e IPTU_20260101.xlsx`

**Cada arquivo é ingerido separadamente**, com sua própria limpeza de período.
Isso garante que meses anteriores não sejam apagados acidentalmente.

---

## 9. Sistema de Auditoria (Tabela `execucoes`)

Toda execução é registrada na tabela `execucoes` do Supabase.

### Estrutura de um registro

| Campo | Tipo | Descrição |
|---|---|---|
| `tipo` | text | "completo" para rotinas normais |
| `status` | text | "iniciou", "sucesso", "falha" |
| `relatorios_processados` | int | Total de relatórios na fila |
| `relatorios_sucesso` | int | Quantos tiveram sucesso |
| `relatorios_falha` | int | Quantos falharam |
| `total_linhas_inseridas` | int | Total de linhas inseridas no Supabase |
| `mensagem` | text | Detalhes da execução |

### Quando é registrado

1. **Início da execução** — `status="iniciou"`
2. **Cada arquivo Excel ingerido** — `status="sucesso"` ou `status="falha"`, com detalhes:
   - Nome do arquivo
   - Linhas inseridas
   - Duplicadas ignoradas
   - Total de itens na tabela no Supabase
   - Data início e data fim dos dados no Supabase
3. **Resultado final** — resumo da execução completa

### Função de registro

```python
def _registrar_execucao(tipo, status, **kwargs):
    # Insere registro na tabela 'execucoes' do Supabase
    # Em caso de falha no registro, loga erro mas NÃO interrompe o fluxo
```

**Arquivo:** `src/orquestrador.py:59` (definição) — chamada em:
- `orquestrador.py` — Rota CLI (início, por arquivo, final)
- `app.py` — Rotas Manual e Automática (por arquivo, início/fim)

### Proteção contra silenciamento de erros

Os imports de `_registrar_execucao` estão **fora** do bloco try/except no `app.py`,
garantindo que erros de importação sejam visíveis e não silenciados.

---

## 10. Tratamento de Erros e Resiliência

### Extração (Playwright)

- **3 tentativas** por relatório (`TENTATIVAS_MAX=3`)
- Falha de um relatório **NÃO** bloqueia os próximos
- Erros críticos de navegador (`Target closed`, `Browser closed`) são propagados imediatamente
- Relatórios 6, 11, 14: se um mês falhar, os demais meses continuam

### Ingestão (Supabase)

- **Try/except por arquivo Excel** — falha em um arquivo não impede os demais
- **Try/except externo no loop** — erro inesperado é logado e registrado na auditoria
- Se `limpar_periodo()` falhar, a ingestão daquele arquivo é abortada (segurança)
- Se `inserir_supabase()` falhar em um lote, os lotes anteriores permanecem

### Motor de Agendamento

- Se robô já está rodando no horário agendado, **pula a execução** (evita conflitos)
- Se `agendamento.json` não existe ou está vazio, ignora silenciosamente

### Conexão Supabase

- Testada no início de cada execução via `testar_conexao()`
- Se falhar, a execução é abortada imediatamente

---

## 11. Configuração e Agendamento

### Variáveis de Ambiente (`.env`)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `JORDAO_URL` | Sim | URL de login do Jordão Gestão |
| `JORDAO_USUARIO` | Sim | Usuário do Jordão |
| `JORDAO_SENHA` | Sim | Senha do Jordão |
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_KEY` | Sim | Chave de API do Supabase |
| `EMAIL_REMETENTE` | Sim | E-mail remetente para alertas |
| `EMAIL_SENHA` | Sim | Senha do e-mail remetente |
| `EMAIL_DESTINATARIO` | Sim | E-mails destinatários (separados por vírgula) |
| `HEADLESS` | Não | `true` = navegador invisível (padrão: false) |
| `PASTA_DESTINO` | Não | Pasta para salvar Excels (padrão: `./Relatorios`) |
| `TIMEOUT_NAVEGACAO` | Não | Timeout de navegação em ms (padrão: 60000) |
| `TENTATIVAS_MAX` | Não | Máximo de tentativas (padrão: 3) |
| `DIAS_RETENCAO_LOCAL` | Não | Dias para manter Excels locais (padrão: 7) |

### Horários de Agendamento (`agendamento.json`)

```json
{
  "horarios": ["06:00", "07:00", "08:00", "09:30", "14:00", "16:00", "18:00", "14:47"]
}
```

O motor de agendamento verifica a cada 30 segundos. Se o horário atual (`HH:MM`)
bate com algum horário da lista e o robô não está rodando, dispara a execução automática.

### Datas por Grupo (`calcular_datas_padrao()`)

| Grupo | Relatórios | data_inicio | data_fim |
|---|---|---|---|
| A (Snapshot) | 1, 2, 4, 5, 8, 12 | Primeiro dia do mês atual | *(vazio)* |
| B (Mês Atual) | 13, 15 | Primeiro dia do mês atual | Último dia do mês atual |
| C/D (Mês Anterior + Atual) | 6, 7, 11, 14 | Primeiro dia do mês anterior | Último dia do mês atual |

---

## 12. Logs e Monitoramento

### Arquivo de Log

- **Caminho:** `logs/jordao_agente.log`
- **Formato:** `YYYY-MM-DD HH:MM:SS | NÍVEL | módulo.função | mensagem`
- **Rotação:** Máximo 5MB, 3 backups
- **Memória:** Últimas 50 linhas ficam na memória (para exibição no dashboard)

### Exemplos de Log

```
2026-07-24 06:00:01 | INFO     | orquestrador.executar | ORQUESTRADOR — Iniciando fluxo completo
2026-07-24 06:00:02 | INFO     | base_agente.processar_fila_em_massa | INICIANDO SESSÃO ÚNICA
2026-07-24 06:02:15 | INFO     | base_agente.processar_fila_em_massa | ✅ EXPORTAÇÃO CONCLUÍDA: 06 Relatorio....xlsx
2026-07-24 06:02:20 | INFO     | base_ingestor.executar | Ingestão concluída: 150 linhas em relatorio_06
2026-07-24 06:02:20 | INFO     | orquestrador._registrar_execucao | Registrando execução no Supabase
```

### Logs de Execução Diária

- **Caminho:** `logs/daily_YYYY-MM-DD.log`
- **Gerado por:** `run_daily.sh`
- **Retenção:** 30 dias (limpeza automática no script)

---

## 13. Registro de Alterações

> **REGRAS OBRIGATÓRIAS:**
> 1. Toda alteração na rotina do robô DEVE ser documentada aqui
> 2. Incluir: data, autor, descrição da mudança, motivo, arquivos afetados
> 3. Alterações sem documentação são consideradas não-existentes para auditoria
> 4. Este arquivo é a fonte verdadeira do comportamento do sistema

### Histórico

| Data | Autor | Descrição | Motivo | Arquivos Afetados |
|---|---|---|---|---|
| 2026-07-24 | — | Criação desta documentação | Documentar fluxo completo | `FLOW_DOCUMENTATION.md` |
| 2026-07-24 | — | `_encontrar_excel_report()` → `_encontrar_excel_reports()` (retorna lista) | Relatórios 6, 11, 14 geram múltiplos Excels; apenas o mais recente era processado, causando perda de dados | `orquestrador.py`, `app.py` |
| 2026-07-24 | — | Adição de `_normalizar_texto()` para detecção de colunas | Colunas com acentos ou espaços (ex: "Mes / Ano") não eram detectadas | `base_ingestor.py` |
| 2026-07-24 | — | Limpeza de resíduos do projeto astral | Código de outro projeto não pertencia a este | `print_logs*.py`, `clean_astral.py`, `temp_logs.txt` |
| 2026-07-24 | — | Regra específica para Rel.7 em `limpar_periodo()` | Rel.7 (Cobranças Recebidas) não tinha regra de coluna, caía no fallback genérico | `base_ingestor.py` |
| 2026-07-24 | — | Auditoria para Rel.10 na Rota CLI | Rel.10 fazia `continue` sem registrar na tabela `execucoes` | `orquestrador.py` |
| 2026-07-24 | — | Imports movidos para fora do try no `app.py` | Erros de importação eram silenciados pelo except externo | `app.py` |
| 2026-07-24 | — | Try/except externo no loop de ingestão (orquestrador) | Erro inesperado no loop podia impedir o resumo final e a limpeza | `orquestrador.py` |

---

*Documento gerado em 2026-07-24. Última atualização: 2026-07-24.*
