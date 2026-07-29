# 📘 Manual Prático — Jordão Automatização

> Documento de referência rápida para entender como o sistema funciona de ponta a ponta:
> **VM local → Robô → Supabase → Painel Render**

---

## 🗺️ Sumário

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Componente 1 — VM Local (Servidor Flask)](#2-componente-1--vm-local-servidor-flask)
3. [Componente 2 — Robô Playwright](#3-componente-2--robô-playwright)
4. [Componente 3 — Supabase (Banco de Dados na Nuvem)](#4-componente-3--supabase-banco-de-dados-na-nuvem)
5. [Componente 4 — Painel Render (Frontend React)](#5-componente-4--painel-render-frontend-react)
6. [Fluxo de Comando Remoto (Render → VM)](#6-fluxo-de-comando-remoto-render--vm)
7. [Os 15 Relatórios — Referência Rápida](#7-os-15-relatórios--referência-rápida)
8. [Ações do Usuário — O Que Fazer em Cada Situação](#8-ações-do-usuário--o-que-fazer-em-cada-situação)
9. [Páginas do App Render — Guia de Uso](#9-páginas-do-app-render--guia-de-uso)
10. [Arquivos Importantes — Mapa de Referência](#10-arquivos-importantes--mapa-de-referência)
11. [Variáveis de Ambiente (.env)](#11-variáveis-de-ambiente-env)
12. [Troubleshooting Rápido](#12-troubleshooting-rápido)

---

## 1. Visão Geral da Arquitetura

O sistema funciona em **4 camadas** que se comunicam:

```
┌─────────────────────────────────────────────────────────────────────┐
│  👤 USUÁRIO                                                         │
│  Acessa o painel via celular ou PC (qualquer lugar do mundo)        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ☁️  PAINEL RENDER (Frontend React + Backend Flask)                  │
│  URL pública — apenas leitura de dados + envio de comandos          │
│  Hospedado em: render.com                                           │
└──────────────┬──────────────────────────────────┬───────────────────┘
               │ Lê dados                          │ Escreve comandos
               │                                   │ na tabela
               ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  🗄️  SUPABASE (PostgreSQL na Nuvem)                                  │
│  Armazena: 12 tabelas de relatórios + execuções + logs +            │
│            comandos_remotos + backups_execucoes                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ Polling a cada 5s
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  💻 VM LOCAL (Windows — Servidor Flask app.py)                      │
│  Porta 5001 — Painel local de controle manual                       │
│  3 threads em segundo plano:                                        │
│    1. Motor de agendamento (verifica hora a cada 30s)               │
│    2. Ouvinte de comandos remotos (polling Supabase a cada 5s)      │
│    3. Processamento da fila (roda quando disparado)                 │
│                                                                     │
│  ↓ Quando precisa extrair dados:                                    │
│  🤖 ROBÔ PLAYWRIGHT (Chromium headless)                             │
│  Acessa o Jordão Gestão, faz login, extrai Excel por relatório      │
└─────────────────────────────────────────────────────────────────────┘
```

**Resumo do fluxo de dados:**
```
Jordão Gestão (web) → Playwright → Excel local → Python → Supabase → Painel Render
```

---

## 2. Componente 1 — VM Local (Servidor Flask)

### O que é?
Um servidor Flask rodando na máquina física (VM Windows) na porta **5001**. 
Acessível somente pela rede local: `http://127.0.0.1:5001`

### Como iniciar
```powershell
# Opção 1 — Duplo clique no arquivo:
iniciar_painel.bat

# Opção 2 — Manual:
.\venv\Scripts\python.exe app.py
```

### O que ele faz em segundo plano (automático, sem interação)

| Thread | O que faz | Frequência |
|---|---|---|
| **Motor de Agendamento** | Verifica se chegou a hora de rodar | A cada 30 segundos |
| **Ouvinte Remoto** | Verifica se o Render enviou um comando | A cada 5 segundos |
| **Watchdog** | Detecta robô travado (+30min sem heartbeat) | A cada 5 segundos |

### Rotas da API local (porta 5001)

| Rota | Método | O que faz |
|---|---|---|
| `/` | GET | Dashboard HTML local |
| `/login` | GET/POST | Página de login local |
| `/api/iniciar` | POST | Adiciona 1 relatório à fila |
| `/api/iniciar_todos` | POST | Adiciona vários relatórios à fila |
| `/api/cancelar` | POST | Cancela execução e fecha navegador |
| `/api/status` | GET | Retorna status atual do robô |
| `/api/logs` | GET | Retorna últimas 50 linhas de log |
| `/api/supabase/dados` | GET | Retorna dados de qualquer tabela |
| `/api/supabase/execucoes` | GET | Retorna histórico de execuções |
| `/api/supabase/kpis` | GET | Retorna KPIs calculados |

### Controle de execução

```python
# Variável global que guarda o estado vivo do robô:
status_robo = {
    "rodando": False,        # True enquanto o robô está processando
    "mensagem": "...",       # Mensagem atual de status
    "fila": [],              # Lista de relatórios a processar
    "relatorio_atual": N,    # ID do relatório sendo processado agora
    "historico": {},         # {"1": "sucesso", "2": "falha", "6": "na_fila"}
    "cancelado": False,      # True quando o usuário cancelou
    "tempos_execucao": {},   # Tempo gasto por relatório
}
```

---

## 3. Componente 2 — Robô Playwright

### O que é?
Um navegador Chromium controlado por código Python via biblioteca **Playwright**.
Opera em modo **headless** (invisível) em produção, ou **modo visível** para debug.

### Arquivos que compõem o robô

| Arquivo | Papel |
|---|---|
| `src/base_agente.py` | **Motor principal** — abre o browser, faz login, gerencia tentativas e chama os extratores |
| `src/relatorios/relatorio_01_imoveis.py` | Extrator específico do Relatório 01 |
| `src/relatorios/relatorio_02_contratos.py` | Extrator específico do Relatório 02 |
| `src/relatorios/relatorio_XX_*.py` | *(um arquivo por relatório, do 01 ao 15)* |

### Fluxo de execução do robô

```
processar_fila_em_massa(fila, status_robo)
    │
    ├─ 1. Abre navegador Chromium (1 sessão para toda a fila)
    │
    ├─ 2. Faz login no Jordão Gestão
    │     URL: JORDAO_URL  |  user: JORDAO_USUARIO  |  senha: JORDAO_SENHA
    │
    ├─ 3. Fecha popup Imoalert (aguarda até 15-20s)
    │
    └─ 4. Para cada relatório na fila:
          │
          ├─ Importa src.relatorios.relatorio_XX
          ├─ Chama extrair(page, data_inicio, data_fim)
          │   └─ Navega → Aplica filtros → Clica Exportar → Aguarda download
          ├─ Valida arquivo Excel gerado
          ├─ Move para /Relatorios/ com nome padronizado
          └─ Se falhar: tenta até 3x antes de marcar como falha
             (falha de 1 NÃO bloqueia os próximos)
```

### Nomes de arquivo gerados

Padrão: `[ID] [Nome do Relatório]_[YYYYMMDD].xlsx`

Exemplo: `06 Relatorio de Cobranca de Aluguel e IPTU_20260101.xlsx`

> Para relatórios mensais (6, 11, 14): um arquivo por mês, ex:
> - `06 ..._20251201.xlsx`
> - `06 ..._20260101.xlsx`

### Modo visível (debug)

No arquivo `.env`, defina:
```
HEADLESS=false
```
O navegador abrirá na tela. Útil para diagnosticar problemas de navegação.

---

## 4. Componente 3 — Supabase (Banco de Dados na Nuvem)

### Tabelas do sistema

| Tabela | O que armazena |
|---|---|
| `relatorio_01_imoveis` | Cadastro de imóveis |
| `relatorio_02_contratos` | Contratos ativos |
| `relatorio_04_ficha_contrato` | Fichas detalhadas de contrato |
| `relatorio_05_tipo_recebimento` | Tipos de recebimento |
| `relatorio_06_cobranca_aluguel` | Cobranças de aluguel e IPTU |
| `relatorio_07_cobrancas_recebidas` | Cobranças recebidas/baixadas |
| `relatorio_08_contratos_x_cobrancas` | Auditoria contrato vs cobrança |
| `relatorio_11_conferencia_despesas` | Despesas de proprietários |
| `relatorio_12_pessoas_ativos` | Cadastro de pessoas ativas |
| `relatorio_13_recebimentos_pagamentos` | Caixa — entradas e saídas |
| `relatorio_14_movimentos_detalhados` | Lançamentos detalhados |
| `relatorio_15_contas_pagar_receber` | Projeção financeira |
| `execucoes` | **Auditoria** — registro de cada execução |
| `logs` | Logs em tempo real |
| `comandos_remotos` | **Canal de comunicação** Render → VM |
| `backups_execucoes` | Backups pré-ingestão |

### Estrutura de cada linha de relatório

Cada linha armazenada tem:
```json
{
  "id": 1234,
  "data_extracao": "2026-07-29T09:15:00",
  "dados": {
    "Imóvel": "123 - Rua das Flores",
    "Proprietário": "João Silva",
    "Valor Aluguel": "1.500,00"
  }
}
```
Os dados brutos do Excel ficam dentro do campo `dados` (JSON).

### Dois tipos de limpeza antes de inserir

| Tipo | Relatórios | O que faz |
|---|---|---|
| **Snapshot** (limpa tudo) | 1, 2, 4, 5, 8, 12 | Apaga a tabela inteira antes de inserir |
| **Temporal** (preserva histórico) | 6, 7, 11, 13, 14, 15 | Apaga apenas os meses presentes no novo Excel |

> **Exemplo temporal:** Se o Excel novo tem dados de Jan/2026 e Fev/2026,
> o sistema apaga do Supabase apenas esses dois meses e insere os novos.
> Dados de meses anteriores ficam preservados.

---

## 5. Componente 4 — Painel Render (Frontend React)

### O que é?
Um dashboard acessível de qualquer lugar (celular, PC, tablet) hospedado no Render.com.
É **somente leitura de dados** + envio de comandos para a VM via Supabase.

**Não executa nada diretamente** — apenas escreve na tabela `comandos_remotos` e a VM lê.

### Tecnologias
- **Frontend:** React + TypeScript + Vite
- **Backend:** Flask (Python) — `render/app_render.py`
- **Comunicação:** API REST `/api/*`

### Páginas disponíveis

| Página | Rota | O que mostra/faz |
|---|---|---|
| **Início** | `/` | KPIs: total imóveis, contratos, contas a pagar/receber |
| **Automação** | `/automacao` | Disparar extração de relatórios + ver status da VM |
| **BI** | `/bi` | Gráficos e análises visuais |
| **Tabelas** | `/tabelas` | Lista de relatórios disponíveis |
| **Tabelas/:id** | `/tabelas/:tabela` | Grade com todos os dados de 1 relatório |
| **Auditoria** | `/auditoria` | Histórico de todas as execuções |
| **Backups** | `/backups` | Lista de backups + botão de restaurar |
| **Logs** | `/logs` | Logs em tempo real filtráveis |

---

## 6. Fluxo de Comando Remoto (Render → VM)

Este é o mecanismo que permite controlar a VM pelo celular:

```
┌──────────────────────────────────────────────────────────────────┐
│  1. USUÁRIO no Render                                            │
│     Clica "Disparar Extração" na página /automacao               │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. RENDER escreve no Supabase                                   │
│     Insere linha na tabela "comandos_remotos":                   │
│     { tipo: "extracao_massa", status: "pendente",               │
│       payload: { relatorios: [1, 2, 6, ...] } }                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │ (em até 5 segundos)
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. VM detecta o comando                                         │
│     Thread "ouvinte_comandos_remotos" faz polling a cada 5s     │
│     Encontra o registro "pendente", valida o _secret            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. VM atualiza o status para "em_execucao"                      │
│     Inicia thread de processamento (processar_fila)              │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. Robô roda na VM                                              │
│     Extrai relatórios, ingere no Supabase                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  6. VM atualiza o comando para "concluido"                       │
│     O Render exibe a confirmação para o usuário                  │
└──────────────────────────────────────────────────────────────────┘
```

### Tipos de comandos remotos

| `tipo` | O que faz |
|---|---|
| `extracao_massa` | Roda vários relatórios de uma vez |
| `extracao_relatorio` | Roda um único relatório |
| `cancelar_execucao` | Para o robô imediatamente, fecha o navegador |
| `salvar_agendamento` | Atualiza os horários de execução automática |

---

## 7. Os 15 Relatórios — Referência Rápida

| ID | Nome | Tipo | Extração Mensal | Tabela Supabase |
|---|---|---|---|---|
| 01 | Relatório de Imóveis | Snapshot | Não | `relatorio_01_imoveis` |
| 02 | Relatório de Contratos | Snapshot | Não | `relatorio_02_contratos` |
| 03 | Relatório de Fluxo de Caixa | **DESATIVADO** | — | — |
| 04 | Relatório Ficha do Contrato | Snapshot | Não | `relatorio_04_ficha_contrato` |
| 05 | Relatório por Tipo de Recebimento | Snapshot | Não | `relatorio_05_tipo_recebimento` |
| 06 | Cobrança de Aluguel e IPTU | Temporal | **SIM** | `relatorio_06_cobranca_aluguel` |
| 07 | Cobranças Recebidas | Temporal | Não | `relatorio_07_cobrancas_recebidas` |
| 08 | Contratos x Cobranças | Snapshot | Não | `relatorio_08_contratos_x_cobrancas` |
| 09 | Comissão das Cobranças | **DESATIVADO** | — | — |
| 10 | Pagamentos aos Beneficiários | **PDF apenas** | Não | *(sem ingestão)* |
| 11 | Conferência de Despesas | Temporal | **SIM** | `relatorio_11_conferencia_despesas` |
| 12 | Pessoas Ativos | Snapshot | Não | `relatorio_12_pessoas_ativos` |
| 13 | Recebimentos e Pagamentos | Temporal | Não | `relatorio_13_recebimentos_pagamentos` |
| 14 | Conferência Movimentos Detalhado | Temporal | **SIM** | `relatorio_14_movimentos_detalhados` |
| 15 | Contas a Pagar / Receber | Temporal | Não | `relatorio_15_contas_pagar_receber` |

### Datas padrão por grupo (execução automática)

| Grupo | Relatórios | data_inicio | data_fim |
|---|---|---|---|
| **A** (Snapshot) | 1, 2, 4, 5, 8, 12 | Primeiro dia do mês atual | *(vazio)* |
| **B** (Mês Atual) | 13, 15 | Primeiro dia do mês atual | Último dia do mês atual |
| **C/D** (Mês Anterior→Atual) | 6, 7, 11, 14 | Primeiro dia do mês anterior | Último dia do mês atual |

---

## 8. Ações do Usuário — O Que Fazer em Cada Situação

### 🟢 Situação normal — tudo automático

O sistema roda sozinho. Os horários configurados em `agendamento.json` disparam a extração automaticamente.

**Você não precisa fazer nada.**

---

### 🔵 Quero ver os dados no painel

1. Acesse a URL do Render no navegador ou celular
2. Faça login com as credenciais configuradas em `DASHBOARD_USER` / `DASHBOARD_PASS`
3. Navegue pelas páginas:
   - **Início** → KPIs gerais
   - **Tabelas** → Selecione um relatório para ver os dados
   - **Auditoria** → Veja quando rodou e o que foi inserido

---

### 🔵 Quero disparar uma extração agora (pelo celular/Render)

1. Acesse o painel Render → página **Automação**
2. Selecione os relatórios desejados
3. Clique **"Disparar Extração"**
4. Aguarde — em até 5 segundos a VM recebe o comando
5. Acompanhe o status na mesma tela

> ⚠️ A VM precisa estar ligada e o `app.py` rodando para receber o comando.

---

### 🔵 Quero disparar uma extração manualmente (painel local da VM)

1. Abra `http://127.0.0.1:5001` no navegador da VM
2. Selecione o relatório e datas desejadas
3. Clique **"Iniciar"**

---

### 🔵 Quero alterar os horários de execução automática

**Pelo Render (recomendado):**
1. Página Automação → seção de Agendamento
2. Configure os horários e clique em Salvar
3. O Render envia para o Supabase → VM atualiza o `agendamento.json`

**Diretamente na VM (manual):**
Edite o arquivo `agendamento.json`:
```json
{
  "horarios": ["06:00", "09:00", "18:00"]
}
```

---

### 🔴 O robô está travado / não termina

**Opção 1 — Cancelar pelo Render:**
1. Página Automação → clique **"Cancelar Execução"**
2. O Render envia comando `cancelar_execucao`
3. A VM fecha o navegador e para o robô

**Opção 2 — Cancelar pelo painel local:**
1. Abra `http://127.0.0.1:5001`
2. Clique **"Cancelar"**

**Opção 3 — Forçar reset (último recurso):**
```powershell
# Encontra o PID do servidor na porta 5001:
netstat -ano | findstr :5001
# Para o processo:
Stop-Process -Id <PID> -Force
# Reinicia:
.\venv\Scripts\python.exe app.py
```

> 💡 O Watchdog automático já detecta robô travado +30 minutos sem heartbeat e faz reset sozinho.

---

### 🔴 Preciso restaurar dados de um backup

1. Acesse o Render → página **Backups**
2. Encontre o backup desejado (por tabela e data)
3. Clique **"Restaurar"**
4. O sistema apaga os dados atuais da tabela e insere os dados do backup

---

### 🛠️ Preciso atualizar o código na VM

Execute o arquivo:
```
Atualizar_VM.bat
```
Ele faz `git pull` e reinicia o servidor automaticamente.

---

## 9. Páginas do App Render — Guia de Uso

### 📊 Início (`/`)
**O que mostra:**
- Total de imóveis cadastrados
- Total de contratos ativos
- Contas a receber × contas a pagar (do mês atual)
- Taxa de sucesso das últimas execuções

**Atualização:** Manual (botão de refresh) ou automática ao entrar na página.

---

### 🤖 Automação (`/automacao`)
**O que mostra:**
- Status atual da VM (rodando/parado/travado)
- Histórico do relatório atual em processamento
- Lista de relatórios para selecionar

**O que o usuário pode fazer:**
- ✅ Selecionar relatórios individuais ou todos
- ✅ Definir datas personalizadas por relatório
- ✅ Clicar "Disparar Extração"
- ✅ Clicar "Cancelar Execução"
- ✅ Gerenciar horários de agendamento automático

**Como funciona o status da VM:**
A página consulta `/api/remoto/status/<cmd_id>` a cada poucos segundos.
Se o comando ficar "pendente" por mais de 10 minutos, exibe alerta de VM sem resposta.

---

### 📈 BI (`/bi`)
**O que mostra:**
- Gráficos derivados dos dados do Supabase
- Análises visuais (tendências, comparativos)

---

### 📋 Tabelas (`/tabelas`)
**O que mostra:**
- Lista de todos os 12 relatórios com ingestão de dados
- Descrição curta de cada relatório
- Link para visualização completa

**Ao clicar em um relatório:**
- Vai para `/tabelas/:tabela`
- Exibe grade com **todos** os dados (com paginação automática)
- Colunas detectadas dinamicamente do campo `dados` do Supabase
- Exibe também metadados: `__id` e `__data_extracao`

---

### 🔍 Auditoria (`/auditoria`)
**O que mostra:**
- Tabela com histórico de todas as execuções (últimas 500)
- Campos: status, tipo, relatórios processados, sucesso, falha, linhas inseridas, mensagem

**Como interpretar o status:**
| Status | Significado |
|---|---|
| `iniciou` | A execução começou |
| `sucesso` | Relatório processado com êxito |
| `falha` | Houve erro (ver campo "mensagem") |

---

### 💾 Backups (`/backups`)
**O que mostra:**
- Lista de backups gerados automaticamente antes de cada ingestão
- Nome amigável da tabela, total de registros, data de criação

**Restaurar um backup:**
1. Encontre o backup desejado
2. Clique no botão de restauração
3. Confirme — o processo substitui os dados atuais pelos do backup

> ⚠️ A restauração é irreversível — faça um backup manual antes se necessário.

---

### 📝 Logs (`/logs`)
**O que mostra:**
- Últimas 200 linhas de log do sistema
- Filtrável por nível: INFO, WARNING, ERROR, todos

**Como usar:**
- Use o filtro de nível para encontrar erros rapidamente
- Logs são atualizados a cada carregamento da página

---

## 10. Arquivos Importantes — Mapa de Referência

```
Jordão Automatizacao/
│
├── app.py                        ← Servidor Flask local (VM). PONTO DE ENTRADA.
│                                    Contém: motor_agendamento, ouvinte_comandos_remotos,
│                                    processar_fila, todas as rotas da API local.
│
├── agendamento.json              ← Horários de execução automática
│                                    {"horarios": ["06:00", "09:00", "18:00"]}
│
├── .env                          ← Credenciais e configurações (NUNCA commitar!)
├── .env.example                  ← Template de configuração (versionar)
│
├── iniciar_painel.bat            ← Inicia o servidor Flask local
├── Atualizar_VM.bat              ← Faz git pull + reinicia servidor
├── Atualizar_Sistema_Completo.bat ← Atualiza tudo (VM + frontend Render)
│
├── src/
│   ├── base_agente.py            ← Motor Playwright (login, extração, retry)
│   ├── config.py                 ← Lê variáveis do .env centralizadamente
│   ├── logger.py                 ← Logging estruturado (arquivo + memória para UI)
│   ├── utils.py                  ← calcular_datas_padrao(), limpeza de arquivos
│   ├── supabase_client.py        ← Conexão com Supabase
│   ├── alertas.py                ← Envio de e-mails de alerta
│   ├── orquestrador.py           ← Execução via CLI + _registrar_execucao()
│   │
│   ├── relatorios/               ← Um arquivo Python por relatório
│   │   ├── relatorio_01_imoveis.py
│   │   ├── relatorio_02_contratos.py
│   │   └── ... (até relatorio_15)
│   │
│   └── ingestao/                 ← Um ingestor por relatório
│       ├── base_ingestor.py      ← Classe base: ler Excel, validar, limpar, inserir
│       ├── __init__.py           ← INGESTORES = {1: Ingestor01, 2: Ingestor02, ...}
│       └── ingestor_XX_*.py      ← 15 ingestores individuais
│
├── render/
│   ├── app_render.py             ← Backend Flask do painel Render (somente leitura)
│   ├── Dockerfile                ← Para deploy no Render.com
│   ├── Procfile                  ← Comando de start do Render
│   └── frontend/                 ← React + TypeScript
│       └── src/
│           ├── App.tsx           ← Roteamento principal
│           ├── pages/            ← Uma pasta por página
│           │   ├── Inicio/
│           │   ├── Automacao/
│           │   ├── BI/
│           │   ├── Tabelas/
│           │   ├── Auditoria/
│           │   ├── Backups/
│           │   └── Logs/
│           └── components/       ← Sidebar, BottomNav, Modal
│
├── Relatorios/                   ← Excels baixados pelo robô (limpo a cada 7 dias)
├── logs/                         ← Logs gerados (jordao_agente.log — máx 5MB × 3)
└── templates/
    └── dashboard.html            ← Dashboard HTML do painel local (VM)
```

---

## 11. Variáveis de Ambiente (.env)

| Variável | Obrigatória | Descrição |
|---|---|---|
| `JORDAO_URL` | ✅ | URL de login do Jordão Gestão |
| `JORDAO_USUARIO` | ✅ | Usuário do Jordão |
| `JORDAO_SENHA` | ✅ | Senha do Jordão |
| `SUPABASE_URL` | ✅ | URL do projeto Supabase |
| `SUPABASE_KEY` | ✅ | Chave de API do Supabase |
| `DASHBOARD_USER` | ✅ | Usuário do painel web |
| `DASHBOARD_PASS` | ✅ | Senha do painel web |
| `EMAIL_REMETENTE` | ✅ | E-mail remetente para alertas |
| `EMAIL_SENHA` | ✅ | Senha do e-mail remetente |
| `EMAIL_DESTINATARIO` | ✅ | Destinos de alerta (separados por vírgula) |
| `REMOTE_SECRET` | ✅ | Token de segurança Render ↔ VM |
| `HEADLESS` | — | `true` = invisível (padrão) / `false` = modo visível |
| `PASTA_DESTINO` | — | Pasta para salvar Excels (padrão: `./Relatorios`) |
| `TIMEOUT_NAVEGACAO` | — | Timeout em ms (padrão: 60000) |
| `TENTATIVAS_MAX` | — | Tentativas por relatório (padrão: 3) |
| `DIAS_RETENCAO_LOCAL` | — | Dias para manter Excels locais (padrão: 7) |

---

## 12. Troubleshooting Rápido

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Robô não inicia no horário | `app.py` não está rodando | Rodar `iniciar_painel.bat` |
| Comando do Render não chega na VM | `app.py` parado ou internet da VM | Verificar se `app.py` está ativo |
| `TimeoutError` no login | Site lento ou URL errada | Verificar `JORDAO_URL` + internet |
| Excel baixado está vazio | Sem dados no período / erro de export | Rodar com `HEADLESS=false` e observar |
| Dados desatualizados no Render | Robô não rodou / falha de ingestão | Ver página Auditoria + Logs |
| E-mail de alerta não chega | Credenciais SMTP erradas | Rodar `py main.py --testar-email` |
| Seletor não encontrado | Layout do Jordão mudou | Inspecionar site e atualizar `relatorio_XX.py` |
| Porta 5001 já em uso ao reiniciar | Processo anterior não fechou | `netstat -ano \| findstr :5001` → `Stop-Process -Id <PID> -Force` |
| Robô travado +30min | Bug ou crash silencioso | Watchdog faz reset automático; ou cancele pelo Render |
| Duplicatas no Supabase | Ingestor rodou 2x sem limpar | Verificar `limpar_periodo()` — temporais não apagam tudo |

---

*Manual gerado em 2026-07-29. Baseado no código-fonte atual do projeto.*
