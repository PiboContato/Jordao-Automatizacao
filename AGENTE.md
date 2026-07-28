# AGENTE.md — Automação de Extração de Relatórios (Sistema Jordão)

> Documento vivo de planejamento técnico. Atualizado incrementalmente à medida que as decisões são tomadas.
> Última atualização: 28/07/2026

---

## 1. Objetivo do Projeto

Criar um agente/script de automação de navegador que acesse o sistema web **Jordão** (cliente sem acesso a banco de dados — dados disponíveis apenas via relatórios exportados na interface), aplique filtros pré-definidos e baixe relatórios automaticamente, salvando-os em uma pasta local pré-definida.

**Por que isso existe:** não há acesso à API ou banco de dados do sistema do cliente. A única via de extração de dados é a interface web.

## Lógica de Execução (Robô Jordão)

O fluxo principal do Agente é gerenciado de forma modular:

1. **`src/base_agente.py`**: Motor do robô. Orquestra Playwright, abre o navegador, faz o Login e gerencia Tentativas de Repetiçao (Retry). Não sabe qual relatório está extraindo — apenas passa a página logada para o extrator específico.
2. **`src/relatorios/`**: Pasta com os extratores. **Para cada relatório, um arquivo Python exclusivo.**
   - Cada arquivo contém os Seletores específicos daquela tela.
   - **ATENÇÃO AO CACHE DO PYTHON**: ao alterar um extrator, **DEVE** reiniciar o servidor Flask (`main.py`) para que as novas regras de clique sejam lidas.
   - Cada arquivo tem uma função `extrair(page, data_inicio, data_fim)` que recebe a página já logada e faz: Navegar → Filtrar Data → Exportar Excel.
3. **`src/ingestao/`**: Pasta com os ingestores. Cada relatório tem um ingestor que valida, limpa e insere dados no Supabase.
   - **`src/ingestao/base_ingestor.py`**: Classe base com toda a lógica de leitura Excel, validação, limpeza de período/snapshot e inserção no Supabase.
   - Cada ingestor herda de `BaseIngestor` e define `table_name`, `report_id` e `min_colunas`.
4. **`app.py`**: Servidor Flask que centraliza toda execução (manual + agendada + comandos remotos). É o canal único canônico de execução.

### 3. Convenção de Nomenclatura de Arquivos Exportados
Todos os relatórios exportados pelo robô DEVEM seguir o padrão:
**`"[ID] [Nome do Relatório] [Data_Inicio] a [Data_Fim].[extensao]"`**
- Exemplo: `01 Relatorio Roteiro de Servicos 01_06_2026 a 30_06_2026.csv`
- Previne sobrescrita e deixa claro o que foi baixado.

### 4. Garantia de Diretório de Destino
A pasta `PASTA_DESTINO` do `.env` deve ser auto-criada (`os.makedirs(exist_ok=True)`) pela função `mover_arquivo_para_destino`.

---

## 2. Escopo Funcional (MVP)

- [x] Login automatizado no sistema Jordão
- [x] Navegação até a tela "Roteiros de Serviços"
- [x] Preenchimento de filtros
- [x] Clique em "Atualizar Lista"
- [x] Exportação via botão "Exportar Excel"
- [x] Captura do arquivo baixado
- [x] Salvamento em pasta local com nomenclatura padronizada
- [x] Execução agendada 1x/dia
- [x] Ingestão de dados no Supabase (15 relatórios)
- [x] Controle remoto via celular (Render → Supabase → VM)
- [x] Dashboard Render com monitor de status da VM
- [x] Deploy one-click via `Atualizar_VM.bat`

**Fora de escopo (por enquanto):**
- Processamento/consolidação automática dos dados extraídos (decisão: só salvar + ingerir no Supabase)
- Múltiplos sistemas/clientes (foco: apenas Jordão)

---

## 2.1 Perfil de Atuação do Agente de Desenvolvimento

**Postura geral:** atuar como engenheiro sênior de automação/RPA e web scraping.

### 2.1.1 Mentalidade Técnica
- **Ceticismo produtivo:** nunca assumir que o site vai se comportar de forma previsível.
- **Pensar em produção desde o dia 1:** sem caminhos absolutos hardcoded, com logs estruturados.
- **Visão de sistema, não de script isolado:** esse agente é peça de um fluxo maior (extração → armazenamento → uso futuro dos dados).
- **Priorização pragmática:** resolver o essencial primeiro, deixar otimizações para depois — sempre sinalizando o que está sendo deixado de lado.

### 2.1.2 Tratamento de Erros e Resiliência
- Todo ponto de falha deve ter tratamento explícito.
- Preferir esperas explícitas por elementos/estado a `sleep()` fixo.
- Retry com backoff para falhas transitórias.
- Validar resultado da exportação antes de considerar sucesso.
- Nunca falhar silenciosamente.
- Nunca logar senhas ou dados sensíveis em texto puro.
- Verificar `.gitignore` antes de commits.

### 2.1.5 Comunicação e Reporte
- Comunicação direta, sem "enrolação".
- Ao propor solução, sempre expor o trade-off.
- Diferenciar "solução definitiva" de "gambiarra temporária".
- Ao encontrar problema fora do escopo, sinalizar explicitamente.

### 2.1.6 Validação e Testes
- Testar etapas isoladamente antes de integrar.
- Rodar ao menos uma vez em modo visível para confirmar comportamento.
- Simular cenários de falha propositalmente.

### 2.1.7 Documentação Contínua
- Toda decisão técnica relevante deve ser refletida neste `AGENTE.md` (Seção 9 — Changelog).
- Ao final de cada marco importante, atualizar a Seção 2.

### 2.1.8 Antipadrões a Evitar
- Escrever o fluxo inteiro sem testar partes isoladamente.
- Usar `sleep()` fixo como solução padrão.
- Deixar credenciais hardcoded.
- Ignorar exceções com `try/except: pass`.
- Apresentar solução provisória como definitiva.
- Avançar para produção sem validar manualmente.

---

## 3. Decisões de Arquitetura

**Decisão atual:** Executar em VM Oracle Cloud (Fase 2 — Produção).

**Opções avaliadas:**

| Opção | Custo | Prós | Contras | Status |
|---|---|---|---|---|
| **Máquina local** | Grátis | Controle total, fácil debugar | Depende de energia/internet, sem redundância | Fase 1 (validação) |
| **VPS pago** (Hetzner, Contabo) | ~R$20-40/mês | Sempre ligado, sessão persiste | Custo fixo, manutenção básica | Descartado |
| **Oracle Cloud Free Tier** | Grátis (4 OCPUs, 24GB RAM) | VM real 24/7, sem custo | Configuração mais técnica | **Escolhido para Fase 2** |
| **GitHub Actions** | Grátis (2.000 min/mês) | Zero manutenção | Ambiente novo a cada execução | Alternativa |
| **Render/Railway** | ~US$5-7/mês | Deploy simples | Free tier não confiável para cron | Descartado |

### 3.2 Stack Técnica
- **Python + Playwright** (automação de navegador)
- **Flask** (servidor web, canal único de execução)
- **Supabase** (banco PostgreSQL + API REST)
- **Render** (hospedagem do dashboard/API)
- **Oracle Cloud VM** (execução do agente 24/7)
- **PM2** (gerenciamento de processos na VM)
- **PuTTY/plink** (SSH remoto para deploy)

### 3.3 Frequência de Execução
**Decisão:** Diária.

### 3.4 Pós-processamento dos Dados
Ingestão no Supabase com validação, limpeza de período e inserção em lotes.

---

## 4. Segurança e Credenciais

- Uso de arquivo `.env` local (fora do controle de versão, no `.gitignore`)
- Script lê credenciais via variáveis de ambiente
- **Recomendação:** credencial dedicada de automação (separada do login pessoal)

---

## 5. Monitoramento e Alertas

**Decisão:** Alerta por e-mail em caso de falha.

**Cenários que devem disparar alerta:**
- Falha no login
- Site fora do ar / timeout
- Botão de exportação não encontrado
- Download não concluído dentro de tempo limite
- Qualquer exceção não tratada

**Detalhes técnicos pendentes:**
- [ ] Qual e-mail(s) deve(m) receber o alerta?
- [ ] Qual serviço usar para envio (SMTP, SendGrid, Gmail API)?
- [ ] Deve haver e-mail de confirmação em caso de sucesso?

---

## 6. Detalhes do Sistema Alvo (Jordão)

- **URL base:** phcfocosistema.com.br/jordaogestaodeimoveis/
- **Autenticação:** Sem 2FA — login simples via usuário/senha
- **Sessão:** persiste por várias horas (validado em testes)

---

## 7. Perguntas em Aberto / Pendências

- [x] Stack: Python + Playwright
- [x] Sistema sem 2FA
- [x] Filtros: Data "hoje até hoje", demais "TODOS"
- [x] Pasta de destino definida
- [x] Alertas: e-mail
- [x] Horário: início do expediente (08h-09h)
- [x] Autorização do cliente confirmada
- [ ] **(Pausado)** E-mail de alerta: código pronto (`src/alertas.py`), ativação pausada — e-mail corporativo requer configuração de SMTP no Microsoft 365

---

## 8. Riscos Identificados

- Mudanças no layout/HTML do site podem quebrar seletores (manutenção recorrente esperada)
- Bloqueio de conta por excesso de tentativas de login
- ~~Questão contratual/ToS~~ — ✅ Resolvido: autorização explícita do cliente

---

## 9. Histórico de Decisões (Changelog)

| Data | Decisão |
|---|---|
| 04/07/2026 | Frequência definida como diária |
| 04/07/2026 | Stack: Python + Playwright |
| 04/07/2026 | Confirmado: sistema sem 2FA |
| 04/07/2026 | Polítca de credenciais: `.env`, nunca em texto puro |
| 04/07/2026 | Filtro de data: "hoje até hoje" |
| 04/07/2026 | Canal de alerta: e-mail |
| 04/07/2026 | Pasta de destino: padrão local |
| 04/07/2026 | Autorização formal do cliente confirmada |
| 04/07/2026 | Perfil de atuação do agente de desenvolvimento adicionado |
| 15/07/2026 | Migração para VM Oracle Cloud (Fase 2 — Produção) |
| 15/07/2026 | Supabase escolhido como banco de dados (PostgreSQL + API REST) |
| 15/07/2026 | Render escolhido para hospedagem do dashboard/API |
| 15/07/2026 | PM2 configurado como gerenciador de processos na VM |
| 15/07/2026 | Canal único canônico de execução via `app.py` (Flask) |
| 20/07/2026 | Controle remoto via celular implementado (Render → Supabase → VM) |
| 20/07/2026 | Dashboard Render com monitor de status da VM implementado |
| 22/07/2026 | Bug "File is not a zip file" corrigido — raiz: double-move em 10 relatórios |
| 22/07/2026 | Bug de ordem invertida para snapshots corrigido (limpar antes de inserir) |
| 22/07/2026 | `Atualizar_VM.bat` criado para deploy one-click via plink/SSH |
| 28/07/2026 | Todos os 15 relatórios validados com sucesso em ingestão manual |

---

## 10. Status — Produção Ativa

**Decisões fechadas:**
- ✅ Infraestrutura: VM Oracle Cloud (168.138.234.37)
- ✅ Stack: Python + Playwright + Flask + Supabase + PM2
- ✅ Frequência: diária, 08h-09h
- ✅ Filtro de data: "hoje até hoje" / demais "TODOS"
- ✅ Pós-processamento: ingestão no Supabase com validação
- ✅ Alertas: e-mail (pendente configuração SMTP)
- ✅ Sem 2FA no sistema alvo
- ✅ Autorização do cliente confirmada
- ✅ Deploy one-click via `Atualizar_VM.bat`

**Pendências remanescentes:**
- [ ] **(Pausado)** Definir e-mail(s) destinatário(s) do alerta e serviço de envio

---

## 11. Rotina de Testes

Para testar manualmente na VM:
```bash
cd /home/ubuntu/Jordao-Automatizacao
pm2 logs jordao-agente --lines 20
```

Para deploy + teste completo:
```bat
Atualizar_VM.bat
```

Regras de Nomenclatura dos Relatórios:
- Todos os relatórios devem ser cadastrados no `app.py` com o número correspondente em dois dígitos como prefixo.
- Exemplo: `01 Relatório Roteiro dos Serviços`, `02 Relatório de Contingência`, etc.

---

## 12. Reiniciando o Servidor (Prevenção de Fantasmas)

**Na VM (produção):**
```bash
pm2 restart jordao-agente
```

**Localmente (desenvolvimento):**
```powershell
Stop-Process -Name python -Force
```
NUNCA mate apenas o terminal — use `Stop-Process` para garantir que processos zumbis do Python/Playwright sejam destruídos.

---

## 13. Foco na Análise de Dados (Excel > PDF)

PDFs são formatos de leitura humana, péssimos para manipulação estruturada de dados.
O objetivo principal é facilitar a análise de dados (linhas e colunas).
Sempre que o sistema gerar um relatório obrigatoriamente em PDF, devemos considerar isso como passo temporário.
A solução ideal prevê transformação para `.xlsx` ou `.csv`, seja extraindo do HTML antes de gerar o PDF, seja processando o PDF baixado.
**O entregável de maior valor é sempre a planilha.**

---

## 14. Ciclo de Visibilidade do Robô (Debug vs Produção)

Ao desenvolver um **novo** relatório, o robô DEVE rodar em modo visível (`HEADLESS=false` no `.env`).
Assim que validado (sucesso ponta a ponta), configurar modo oculto (`HEADLESS=true`).
O acompanhamento em produção é feito puramente pela leitura dos Logs.

---

## 15. Lidar com Selects Customizados (Dropdowns Não-nativos)

Sistemas que utilizam frameworks modernos (Angular, React, Vue) frequentemente substituem a tag `<select>` padrão por divs estilizadas (ex: `g-select`).

**A Solução (Lição Aprendida):**
Simular o comportamento exato de um usuário humano:
1. Localizar o container/seta que abre o dropdown (XPath com `following-sibling` a partir do `label`)
2. Clique físico (`.click()`) no container para forçar abertura do modal/lista
3. Espera (`wait_for_timeout(500)`) para animação CSS
4. Procurar a opção desejada pelo texto exato e forçar clique (`.locator("text=Opção").last.click()`)

O Fallback via injeção JavaScript deve ser mantido para casos onde o dropdown está inacessível fisicamente.

---

## 16. Otimização de Ingestão no Supabase e Regras de Datas dos Relatórios

### Aprendizados da Investigação de Limpeza do Banco (Julho/2026):

1. **Filtro de Arquivos em Ingestão (`_encontrar_excel_reports`)**:
   - Para relatórios estáticos/snapshots (1, 2, 4, 5, 8, 12), o orquestrador processa APENAS o arquivo mais recente baixado (`arquivos[0]`).
   - Para relatórios por período (3, 6, 7, 9, 11, 13, 14, 15), o orquestrador considera apenas arquivos gerados na janela recente.

2. **Validação de Colunas no Relatório 02 (Contratos)**:
   - `min_colunas = 7` (compatível com planilha de 7 colunas do sistema Jordão).

3. **Proteção contra Anos Fictícios (`0001`)**:
   - Filtra apenas datas com anos válidos entre 2000 e 2100.

4. **DIRETRIZ FUTURA (REVISÃO INDIVIDUAL POR RELATÓRIO)**:
   - **MUITO IMPORTANTE:** Precisaremos rever o robô individualmente para cada relatório e as regras de datas para extração, garantindo que as premissas de filtro de cada tela combinem exatamente com a estratégia de persistência no Supabase.

---

## 17. Centralização da Execução no Servidor Web (app.py) e Controle Remoto via Celular

### Decisões de Arquitetura (Julho/2026):

1. **Eliminação Permanente da Rota B (CLI Genérico)**:
   - A rota de linha de comando (`src/orquestrador.py:executar` e `run_daily.sh`) foi **desativada**.
   - `orquestrador.py` retém unicamente funções auxiliares (`_encontrar_excel_reports`, `_registrar_execucao`).

2. **Canal Único Canonical de Execução (`app.py`)**:
   - Todo disparo de automação passa exclusivamente pelo Flask.
   - Cada relatório/arquivo gera registro individual no Supabase.

3. **Arquitetura de Controle Remoto via Celular (Render → Supabase → VM)**:
   - Tabela `comandos_remotos` no Supabase como fila de mensagens.
   - Render grava solicitações (`extracao_massa`, `extracao_relatorio`, `salvar_agendamento`).
   - VM roda thread `ouvinte_comandos_remotos` em segundo plano (lê a cada 5s, executa, atualiza status).

4. **Inicialização Automática 24/7 na VM Windows**:
   - Atalho na pasta Startup do Windows para garantir `app.py` sempre ativo.

---

## 18. Infraestrutura de Produção (VM Oracle Cloud)

### Dados de Acesso
- **IP da VM:** 168.138.234.37
- **Usuário:** ubuntu
- **Sistema:** Oracle Cloud Free Tier (Ubuntu)
- **Chave SSH:** `E:\Maquina Virtual VM\private.ppk` (sessão PuTTY `pibo_mv1`)

### Gerenciamento de Processos (PM2)
- **Comando:** `pm2 status` para verificar processos
- **Interpreter:** `/home/ubuntu/Jordao-Automatizacao/venv/bin/python3` (NÃO o python3 do sistema)
- **Startup systemd:** `pm2-ubuntu.service` configurado para sobreviver a reboot
- **Reiniciar:** `pm2 restart jordao-agente`
- **Logs:** `pm2 logs jordao-agente --lines 20`

### Processos PM2 Ativos
| ID | Nome | Descrição |
|---|---|---|
| 0 | alterdata-britt-backend | Backend Alterdata |
| 1 | alterdata-britt-frontend | Frontend Alterdata |
| 3 | jordao-agente | Agente de automação (Flask) |

### Servidor Flask (app.py)
- Escuta em `0.0.0.0:5001`
- Módulos ativos na inicialização:
  - `ouvinte_comandos_remotos()` — thread daemon que lê comandos do Supabase a cada 5s
  - `motor_agendamento()` — thread que dispara execuções agendadas
  - `processar_fila()` — thread daemon que processa a fila de relatórios (modo FIFO, deduplicado)

### Resiliência do app.py (9 melhorias implementadas)
1. **Globals thread-safe:** `cmd_id_atual`, `ultimo_heartbeat`, `_comandos_ja_processados`
2. **Heartbeat** em `processar_fila()` — atualiza timestamp a cada relatório processado
3. **Watchdog 30min** — reinicia fila se ficar travada
4. **Ordem FIFO** (`desc=False`) — processa comandos mais antigos primeiro
5. **Deduplicação em memória** — `_comandos_ja_processados` evita reprocessar IDs já executados
6. **Status "em_espera"** — comandos aguardando vez na fila (não ficam "pendente" para sempre)
7. **Thread daemon desacoplada** — `processar_fila()` roda em thread separada, não bloqueia Flask
8. **Filtro .xlsx** — só envia para ingestão arquivos com extensão `.xlsx`
9. **Fix `_comandos_ja_processados`** — `global` declarado corretamente em `ouvinte_comandos_remotos()`

### Render (Dashboard)
- **Backend:** `render/app_render.py` — API que serve o dashboard
- **Frontend:** `render/templates/dashboard_render.html` — Dashboard com monitor de status
- **Alerta VM:** Banner `#alertaVM` + JS que detecta se a VM está respondendo
- **Endpoint:** `GET /api/remoto/status/<id>` — retorna status do comando com flag `vm_sem_responder`
- **Deploy:** auto via webhook do GitHub (push no `master`)

### Supabase
- **Projeto:** `tqfzibpclgzugauxvgaf.supabase.co`
- **Service Role Key:** armazenada no `.env` (chave com permissão total, bypass RLS)
- **Tabelas:** 15 tabelas de relatórios (ver Seção 19)
- **Tabela de comandos:** `comandos_remotos`
- **Tabela de backups:** `backups_execucoes`

### Variáveis de Ambiente (.env) Relevantes
```env
SUPABASE_URL=https://tqfzibpclgzugauxvgaf.supabase.co
SUPABASE_KEY=<service_role_key>
PASTA_DOWNLOADS_SO=/home/ubuntu/Downloads
PASTA_DESTINO=/home/ubuntu/Jordao-Automatizacao/Relatorios
HEADLESS=true
```

---

## 19. Mapeamento Completo dos Relatórios

### 19.1 Tabela Geral

| ID | Nome do Relatório | Arquivo Extrator | Tabela Supabase | Ingestor | Tipo | Conversor PDF→Excel |
|---|---|---|---|---|---|---|
| 01 | Roteiro dos Serviços | `relatorio_imoveis.py` | `relatorio_01_imoveis` | `ingestor_01_imoveis.py` | Snapshot | Não (Excel nativo) |
| 02 | Contratos | `relatorio_contratos.py` | `relatorio_02_contratos` | `ingestor_02_contratos.py` | Snapshot | Não (Excel nativo) |
| 03 | Fluxo de Caixa | `relatorio_fluxo_caixa.py` | `relatorio_03_fluxo_caixa` | `ingestor_03_fluxo_caixa.py` | Período | Não (PDF→Excel interno) |
| 04 | Ficha do Contrato | `relatorio_ficha_contrato.py` | `relatorio_04_ficha_contrato` | `ingestor_04_ficha_contrato.py` | Snapshot | Sim (`conversor_ficha.py`) |
| 05 | Tipo de Recebimento | `relatorio_tipo_recebimento.py` | `relatorio_05_tipo_recebimento` | `ingestor_05_tipo_recebimento.py` | Snapshot | Sim (PDF→Excel interno) |
| 06 | Cobrança de Aluguel | `relatorio_cobranca_aluguel.py` | `relatorio_06_cobranca_aluguel` | `ingestor_06_cobranca_aluguel.py` | Período | Sim (PDF→Excel interno) |
| 07 | Cobranças Recebidas | `relatorio_cobrancas_recebidas.py` | `relatorio_07_cobrancas_recebidas` | `ingestor_07_cobrancas_recebidas.py` | Período | Sim (PDF→Excel interno) |
| 08 | Contratos x Cobranças | `relatorio_contratos_x_cobrancas.py` | `relatorio_08_contratos_x_cobrancas` | `ingestor_08_contratos_x_cobrancas.py` | Snapshot | Sim (`conversor_contratos_x_cobrancas.py`) |
| 09 | Comissão de Cobranças | `relatorio_comissao_cobrancas.py` | `relatorio_09_comissao_cobrancas` | `ingestor_09_comissao_cobrancas.py` | Período | Sim (PDF→Excel interno) |
| 10 | Pagamentos Beneficiários | `relatorio_pagamentos_beneficiarios.py` | `relatorio_10_pagamentos_beneficiarios` | `ingestor_10_pagamentos_beneficiarios.py` | — | Não (PDF only, ignorado na ingestão) |
| 11 | Conferência de Despesas | `relatorio_conferencia_despesas.py` | `relatorio_11_conferencia_despesas` | `ingestor_11_conferencia_despesas.py` | Período | Sim (PDF→Excel interno) |
| 12 | Pessoas e Ativos | `relatorio_pessoas_ativos.py` | `relatorio_12_pessoas_ativos` | `ingestor_12_pessoas_ativos.py` | Snapshot | Sim (`conversor_pessoas_ativos.py`) |
| 13 | Recebimentos e Pagamentos | `relatorio_recebimentos_pagamentos.py` | `relatorio_13_recebimentos_pagamentos` | `ingestor_13_recebimentos_pagamentos.py` | Período | Sim (PDF→Excel interno) |
| 14 | Movimentos Detalhados | `relatorio_movimentos_detalhados.py` | `relatorio_14_movimentos_detalhados` | `ingestor_14_movimentos_detalhados.py` | Período | Sim (PDF→Excel interno) |
| 15 | Contas a Pagar/Receber | `relatorio_contas_pagar_receber.py` | `relatorio_15_contas_pagar_receber` | `ingestor_15_contas_pagar_receber.py` | Período | Não (PDF→Excel interno) |

### 19.2 Snapshot vs Período

**Snapshot** (`SNAPSHOT_REPORTS = {1, 2, 4, 5, 8, 12}`):
- A tabela é **substituída inteiramente** a cada extração (limpa → insere)
- Não acumula histórico de meses anteriores
- Processa APENAS o arquivo mais recente

**Período** (demais):
- A tabela **acumula histórico** — limpa apenas o período-alvo antes de inserir
- Extrai meses do nome do arquivo para determinar o que limpar
- Processa arquivos gerados nas últimas 2 horas

### 19.3 Padrão de Extração (PDF→Excel)

Relatórios que geram PDF precisam de conversão para Excel antes da ingestão:
1. `extrair()` captura o PDF via interceptação de blob URL (Base64)
2. Salva como `.pdf` temporário em `PASTA_DOWNLOADS_SO`
3. Chama conversor específico (ex: `conversor_ficha.py`) que processa o PDF e retorna `caminho_excel`
4. **Retorna `caminho_excel`** (NÃO move o arquivo internamente)
5. `base_agente.py` move o arquivo para `PASTA_DESTINO`
6. `base_ingestor.py` lê o `.xlsx` e ingeri no Supabase

---

## 20. Commits Relevantes e Histórico de Bugs Corrigidos

### Commits (cronológico, mais recente primeiro)

| Hash | Descrição |
|---|---|
| `cc1502c` | Atualização via Atualizar_VM.bat (último deploy) |
| `449f2b7` | Atualização automática via bat |
| `f23b4d8` | Atualizar_VM.bat com `-load pibo_mv1 -l ubuntu` |
| `e86fdfb` | Atualizar_VM.bat inicial |
| `1e04bf5` | Fix: remove double-move in reports 04, 05, 08 |
| `2d96d8b` | Fix: remove double-move in 7 PDF→Excel reports |
| `d592e6a` | Fix: all PDF→Excel reports now return xlsx path |
| `97e1344` | Fix: filter only .xlsx files before ingestion |
| `4e43125` | Fix: add global `_comandos_ja_processados` to ouvinte |
| `1f4ae15` | Fix: resilience improvements (thread decouple, FIFO, dedup, watchdog, heartbeat, VM status) |
| `bfba36b` | Fix: remove age validation on remote commands |
| `32a6249` | Fix: remove horizontal scroll on desktop tables + mobile accordion |
| `b5dbde7` | Fix: limpar_periodo usa meses do nome do arquivo |
| `0e7ad9f` | Fix: report 15 extrair retorna .xlsx |
| `361f082` | Fix: ingestão usa caminhos exatos dos arquivos |

### Bug: "File is not a zip file"

**Sintoma:** Durante ingestão, o sistema tentava ler um arquivo `.pdf` como se fosse Excel, gerando erro "File is not a zip file".

**Causa raiz (double-move):** As funções `exportar_pdf()` e `exportar_excel()` em cada extrator moviam o arquivo XLSX de `PASTA_DOWNLOADS_SO` para `PASTA_DESTINO` internamente (via `mover_arquivo_para_destino`). Depois, `base_agente.py:353` tentava mover o mesmo arquivo novamente → `FileNotFoundError`.

**Por que funcionou para relatórios 01-03 e 15:** Esses relatórios não tinham double-move (ou o conversor retornava o caminho correto).

**Correção:** Removido `mover_arquivo_para_destino` dentro de `exportar_pdf()`/`exportar_excel()` dos 10 relatórios afetados (04-09, 11-14). Agora `extrair()` retorna `caminho_excel` de `PASTA_DOWNLOADS_SO` sem mover, e `base_agente.py` faz o move.

**Commits:** `97e1344`, `d592e6a`, `2d96d8b`, `1e04bf5`

### Bug: Ordem invertida para snapshots

**Sintoma:** Report 08 (e potencialmente 01, 02, 04, 05, 12) mostrava "140 inseridos" mas a tabela no Supabase ficava vazia.

**Causa raiz:** Em `base_ingestor.py:530-532`, o código para `SNAPSHOT_REPORTS` fazia:
```python
total = self.inserir_supabase(registros)  # insere 140
self.limpar_tabela()                       # DELETA TUDO
```
A ordem estava invertida — inseria primeiro, depois limpava.

**Correção:** Invertido para:
```python
self.limpar_tabela()                       # limpa primeiro
total = self.inserir_supabase(registros)   # insere depois
```

**Nota:** Para relatórios snapshot com tabela vazia antes, `limpar_tabela()` deleta 0 linhas — o bug só se manifesta quando a tabela já tem dados.

---

## 21. Testes Realizados (Resultados por Relatório)

### Teste Individual (todos via extração manual)

| Relatório | Status | Inseridos | Duplicados | Total na Tabela | Observação |
|---|---|---|---|---|---|
| 01 | ✅ OK | — | — | — | Testado antes da sessão |
| 02 | ✅ OK | — | — | — | Testado antes da sessão |
| 04 | ✅ OK | 141 | 0 | 141 | Primeiro teste pós-fix |
| 05 | ✅ OK | 258 | 0 | 258 | — |
| 06 | ✅ OK | 136 | 0 | 209 | Tabela já tinha 73 registros antigos |
| 07 | ✅ OK | — | — | — | Limpo via SQL e testado |
| 08 | ✅ OK | 140 | 0 | 140 | Após fix de snapshot order |
| 12 | ✅ OK | 686 | 0 | 686 | Primeiro teste pós-fix |

**Todos os 15 relatórios foram testados com sucesso.**

### Como limpar uma tabela no Supabase (quando necessário)
Acessar o painel → SQL Editor → executar:
```sql
TRUNCATE relatorio_XX_nome_tabela RESTART IDENTITY CASCADE;
```

---

## 22. Deploy One-Click via Atualizar_VM.bat

### Localização
`C:\projetos\Jordao Automatizacao\Atualizar_VM.bat`

### O que faz (ordem)
1. `git add -A` + `git diff --cached --quiet || git commit` + `git push origin master` (commita e envia mudanças para GitHub)
2. Conecta na VM via plink/SSH usando sessão PuTTY salva (`pibo_mv1`)
3. Roda `git pull` na VM
4. Roda `pm2 restart jordao-agente`
5. Mostra últimas 10 linhas de logs

### Como funciona
- Usa `plink.exe` (`C:\Program Files\PuTTY\plink.exe`) com `-load "pibo_mv1" -l ubuntu`
- A sessão `pibo_mv1` carrega IP, porta e chave SSH (`E:\Maquina Virtual VM\private.ppk`)
- **Primeira execução:** plink pergunta "Store key in cache? (y/n)" — digitar `y`
- **Não pede senha** — usa autenticação por chave SSH

### Como usar
1. Editar arquivos localmente
2. Duplo-clique em `Atualizar_VM.bat`
3. Ver resultado na janela do CMD
4. Tecla Enter para fechar

### Seção Pendências de Deploy
- O `.bat` não tem tratamento de erro — se o push falhar, o deploy na VM continua
- Commit sem mudanças gera "nothing to commit" (não é erro, o `||` pula o commit)
- Host key cache: primeira execução precisa de confirmação manual

---

## 23. Estrutura de Arquivos (Referência Rápida)

```
Jordao-Automatizacao/
├── app.py                          # Servidor Flask (canal único de execução)
├── Atualizar_VM.bat                # Deploy one-click para VM
├── .env                            # Variáveis de ambiente (não versionado)
├── .env.example                    # Template de variáveis
├── .gitignore
├── AGENTE.md                       # Este arquivo
├── agendamento.json                # Configuração de agendamento
├── src/
│   ├── base_agente.py              # Motor: Playwright, login, retry, fila
│   ├── config.py                   # Configurações carregadas do .env
│   ├── supabase_client.py          # Conexão com Supabase
│   ├── logger.py                   # Sistema de log estruturado
│   ├── orquestrador.py             # Funções auxiliares (encontrar arquivos, registrar execução)
│   ├── utils.py                    # Utilitários: mover arquivo, gerar nome, validar Excel, limpar antigos
│   ├── alertas.py                  # Envio de e-mail (pendente configuração SMTP)
│   ├── migrations/
│   │   ├── 001_create_tables.sql   # Criação das 15 tabelas
│   │   ├── 005_enable_rls_security.sql
│   │   └── 006_add_tentativas_comandos.sql
│   ├── relatorios/                 # Extratores (1 arquivo por relatório)
│   │   ├── relatorio_imoveis.py              # 01
│   │   ├── relatorio_contratos.py            # 02
│   │   ├── relatorio_fluxo_caixa.py          # 03
│   │   ├── relatorio_ficha_contrato.py       # 04
│   │   ├── relatorio_tipo_recebimento.py     # 05
│   │   ├── relatorio_cobranca_aluguel.py     # 06
│   │   ├── relatorio_cobrancas_recebidas.py  # 07
│   │   ├── relatorio_contratos_x_cobrancas.py # 08
│   │   ├── relatorio_comissao_cobrancas.py   # 09
│   │   ├── relatorio_pagamentos_beneficiarios.py # 10
│   │   ├── relatorio_conferencia_despesas.py # 11
│   │   ├── relatorio_pessoas_ativos.py       # 12
│   │   ├── relatorio_recebimentos_pagamentos.py # 13
│   │   ├── relatorio_movimentos_detalhados.py # 14
│   │   └── relatorio_contas_pagar_receber.py # 15
│   ├── ingestao/                   # Ingestores (1 por relatório)
│   │   ├── base_ingestor.py        # Classe base: leitura, validação, limpeza, inserção
│   │   ├── ingestor_01_imoveis.py
│   │   ├── ingestor_02_contratos.py
│   │   ├── ...                     # (um por relatório)
│   │   └── ingestor_15_contas_pagar_receber.py
│   └── utilitarios/                # Conversores PDF→Excel
│       ├── conversor_ficha.py                    # 04
│       ├── conversor_contratos_x_cobrancas.py    # 08
│       ├── conversor_pessoas_ativos.py           # 12
│       └── ...                                   # demais conversores
├── Relatorios/                     # Pasta de destino dos arquivos baixados
└── render/                         # Código do dashboard Render
    ├── app_render.py               # API Flask do Render
    └── templates/
        └── dashboard_render.html   # Dashboard com monitor de status
```
