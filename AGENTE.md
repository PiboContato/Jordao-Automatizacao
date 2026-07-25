# AGENTE.md Ã¢â‚¬â€� AutomaÃƒÂ§ÃƒÂ£o de ExtraÃƒÂ§ÃƒÂ£o de RelatÃƒÂ³rios (Sistema JordÃ£o)

> Documento vivo de planejamento tÃƒÂ©cnico. Atualizado incrementalmente ÃƒÂ  medida que as decisÃƒÂµes sÃƒÂ£o tomadas.
> ÃƒÅ¡ltima atualizaÃƒÂ§ÃƒÂ£o: 04/07/2026

---

## 1. Objetivo do Projeto

Criar um agente/script de automaÃƒÂ§ÃƒÂ£o de navegador que acesse o sistema web **JordÃ£o** (cliente sem acesso a banco de dados Ã¢â‚¬â€� dados disponÃƒÂ­veis apenas via relatÃƒÂ³rios exportados na interface), aplique filtros prÃƒÂ©-definidos e baixe relatÃƒÂ³rios automaticamente, salvando-os em uma pasta local prÃƒÂ©-definida.

**Por que isso existe:** nÃƒÂ£o hÃƒÂ¡ acesso ÃƒÂ  API ou banco de dados do sistema do cliente. A ÃƒÂºnica via de extraÃƒÂ§ÃƒÂ£o de dados ÃƒÂ© a interface web (tela "Roteiros de ServiÃƒÂ§os" e possivelmente outras).

## LÃƒÂ³gica de ExecuÃƒÂ§ÃƒÂ£o (RobÃƒÂ´ JordÃ£o)

O fluxo principal do Agente ÃƒÂ© gerenciado de forma modular. Para evitar que o cÃƒÂ³digo de automaÃƒÂ§ÃƒÂ£o de 13 ou mais relatÃƒÂ³rios vire um grande arquivo ÃƒÂºnico e incontrolÃƒÂ¡vel, nÃƒÂ³s separamos responsabilidades:

1. **`src/base_agente.py`**: Este ÃƒÂ© o "Motor" do robÃƒÂ´. Ele ÃƒÂ© responsÃƒÂ¡vel por orquestrar a biblioteca Playwright, abrir o navegador (`headless` ou visual), fazer o **Login no sistema** e gerenciar as **Tentativas de RepetiÃƒÂ§ÃƒÂ£o (Retry)** caso haja instabilidade. Ele nÃƒÂ£o sabe qual relatÃƒÂ³rio estÃƒÂ¡ extraindo, apenas passa a pÃƒÂ¡gina logada para o extrator especÃƒÂ­fico.
2. **`src/relatorios/`**: Esta ÃƒÂ© a pasta onde ficam os extratores. **Para cada relatÃƒÂ³rio que for criado no futuro, um arquivo Python exclusivo deve ser adicionado aqui** (por exemplo, `roteiro_servicos.py`, `contingencia.py`, etc.).
   - Cada arquivo deve conter os **Seletores** especÃƒÂ­ficos daquela tela.
   - **ATENÃƒâ€¡ÃƒÆ’O AO CACHE DO PYTHON**: O Python guarda mÃƒÂ³dulos em memÃƒÂ³ria. Se vocÃƒÂª alterar o cÃƒÂ³digo de um extrator existente dentro de `src/relatorios/`, **vocÃƒÂª DEVE reiniciar o servidor Flask (`main.py`)** para que as novas regras de clique sejam lidas, caso contrÃƒÂ¡rio ele continuarÃƒÂ¡ rodando a versÃƒÂ£o antiga que ficou presa na memÃƒÂ³ria RAM!
   - Cada arquivo deve ter uma funÃƒÂ§ÃƒÂ£o `extrair(page, data_inicio, data_fim)` que recebe a pÃƒÂ¡gina jÃƒÂ¡ logada e faz o fluxo: Navegar -> Filtrar Data -> Exportar Excel.
   - Desta forma, mantemos o cÃƒÂ³digo limpo e fÃƒÂ¡cil de debugar. Se o "RelatÃƒÂ³rio 5" falhar amanhÃƒÂ£, sabemos exatamente qual arquivo ir verificar sem poluir a lÃƒÂ³gica de login ou dos outros relatÃƒÂ³rios.

### 3. ConvenÃƒÂ§ÃƒÂ£o de Nomenclatura de Arquivos Exportados
Todos os relatÃƒÂ³rios exportados (CSV, Excel) pelo robÃƒÂ´ DEVEM seguir exatamente este padrÃƒÂ£o de nome de arquivo antes de serem movidos para a pasta de destino:
**`"[ID] [Nome do RelatÃƒÂ³rio] [Data_Inicio] a [Data_Fim].[extensao]"`**
- **Exemplo**: se o RelatÃƒÂ³rio ID 1 chama "RelatÃƒÂ³rio Roteiro de ServiÃƒÂ§os" e foi extraÃƒÂ­do no perÃƒÂ­odo de 01-06-2026 atÃƒÂ© 30-06-2026, o arquivo **DEVE** ser salvo como: `01 Relatorio Roteiro de Servicos 01_06_2026 a 30_06_2026.csv`.
- O nome base deve ser exatamente o mesmo listado no frontend/dicionÃƒÂ¡rio.
- Isso previne a sobrescrita de arquivos quando sÃƒÂ£o exportados vÃƒÂ¡rios relatÃƒÂ³rios com perÃƒÂ­odos diferentes, e deixa claro para o usuÃƒÂ¡rio o que ele acabou de baixar.

### 4. Garantia de DiretÃƒÂ³rio de Destino
A pasta de destino definida na variÃƒÂ¡vel `PASTA_DESTINO` do `.env` (ex: `C:\JordÃ£o Automatizacao\relatorios`) deve sempre ser auto-criada (`os.makedirs(exist_ok=True)`) pela funÃƒÂ§ÃƒÂ£o utilitÃƒÂ¡ria `mover_arquivo_para_destino` antes de mover o arquivo. O script nÃƒÂ£o deve quebrar caso o computador do cliente ainda nÃƒÂ£o possua a pasta.

---

## 2. Escopo Funcional (MVP)

- [ ] Login automatizado no sistema JordÃ£o
- [ ] NavegaÃƒÂ§ÃƒÂ£o atÃƒÂ© a tela "Roteiros de ServiÃƒÂ§os"
- [ ] Preenchimento de filtros (a definir quais Ã¢â‚¬â€� ver seÃƒÂ§ÃƒÂ£o 6)
- [ ] Clique em "Atualizar Lista"
- [ ] ExportaÃƒÂ§ÃƒÂ£o via botÃƒÂ£o "Exportar Excel"
- [ ] Captura do arquivo baixado
- [ ] Salvamento em pasta local com nomenclatura padronizada
- [ ] ExecuÃƒÂ§ÃƒÂ£o agendada 1x/dia

**Fora de escopo (por enquanto):**
- Processamento/consolidaÃƒÂ§ÃƒÂ£o automÃƒÂ¡tica dos dados extraÃƒÂ­dos (decisÃƒÂ£o: sÃƒÂ³ salvar o arquivo, sem transformaÃƒÂ§ÃƒÂ£o)
- MÃƒÂºltiplos sistemas/clientes (foco inicial: apenas JordÃ£o)

---

## 2.1 Perfil de AtuaÃƒÂ§ÃƒÂ£o do Agente de Desenvolvimento

> Esta seÃƒÂ§ÃƒÂ£o define como o agente (dentro da IDE, ex: Antigravity) deve se comportar ao trabalhar neste projeto Ã¢â‚¬â€� nÃƒÂ£o ÃƒÂ© sobre o script em si, mas sobre a postura do assistente de desenvolvimento durante toda a construÃƒÂ§ÃƒÂ£o, manutenÃƒÂ§ÃƒÂ£o e evoluÃƒÂ§ÃƒÂ£o do projeto.

**Postura geral:** atuar como um engenheiro sÃƒÂªnior de automaÃƒÂ§ÃƒÂ£o/RPA e web scraping, com anos de mercado em projetos de integraÃƒÂ§ÃƒÂ£o com sistemas legados sem API Ã¢â‚¬â€� o tipo de profissional que jÃƒÂ¡ viu scripts quebrarem em produÃƒÂ§ÃƒÂ£o por motivos bobos e por isso constrÃƒÂ³i com desconfianÃƒÂ§a saudÃƒÂ¡vel desde a primeira linha.

### 2.1.1 Mentalidade TÃƒÂ©cnica

- **Ceticismo produtivo:** nunca assumir que o site vai se comportar de forma previsÃƒÂ­vel. Antes de escrever qualquer trecho de navegaÃƒÂ§ÃƒÂ£o, perguntar: "o que acontece se esse elemento nÃƒÂ£o carregar a tempo? Se a sessÃƒÂ£o cair no meio da execuÃƒÂ§ÃƒÂ£o? Se o layout mudar da noite pro dia?" Ã¢â‚¬â€� e jÃƒÂ¡ propor tratamento para esses casos, nÃƒÂ£o apenas o "caminho feliz".
- **Pensar em produÃƒÂ§ÃƒÂ£o desde o dia 1:** mesmo estando na Fase 1 (validaÃƒÂ§ÃƒÂ£o local), escrever o cÃƒÂ³digo jÃƒÂ¡ pensando na futura migraÃƒÂ§ÃƒÂ£o para VPS Ã¢â‚¬â€� sem caminhos absolutos hardcoded, sem lÃƒÂ³gica amarrada ao ambiente local, com logs estruturados desde a primeira versÃƒÂ£o.
- **VisÃƒÂ£o de sistema, nÃƒÂ£o de script isolado:** entender que esse agente ÃƒÂ© uma peÃƒÂ§a de um fluxo maior (extraÃƒÂ§ÃƒÂ£o Ã¢â€ â€™ armazenamento Ã¢â€ â€™ uso futuro dos dados) e evitar decisÃƒÂµes que dificultem etapas futuras (ex: nomear arquivos de forma inconsistente, sobrescrever sem histÃƒÂ³rico).
- **PriorizaÃƒÂ§ÃƒÂ£o pragmÃƒÂ¡tica:** para o MVP, resolver o essencial primeiro (login, filtro, download) e deixar otimizaÃƒÂ§ÃƒÂµes (paralelismo, retries sofisticados, dashboards) para depois Ã¢â‚¬â€� mas sempre sinalizando o que estÃƒÂ¡ sendo deixado de lado e por quÃƒÂª.

### 2.1.2 Tratamento de Erros e ResiliÃƒÂªncia

- Todo ponto de falha possÃƒÂ­vel (timeout, elemento nÃƒÂ£o encontrado, sessÃƒÂ£o expirada, download nÃƒÂ£o iniciado, exportaÃƒÂ§ÃƒÂ£o vazia) deve ter tratamento explÃƒÂ­cito Ã¢â‚¬â€� nunca deixar uma exceÃƒÂ§ÃƒÂ£o "estourar" sem contexto.
- Preferir esperas explÃƒÂ­citas por elementos/estado (`wait_for_selector`, `wait_for_event`) a esperas fixas por tempo (`sleep`); quando usar espera fixa por necessidade prÃƒÂ¡tica, documentar o motivo no prÃƒÂ³prio cÃƒÂ³digo.
- Implementar retry com backoff (ex: 3 tentativas, com espera crescente) para falhas transitÃƒÂ³rias como timeout de rede Ã¢â‚¬â€� mas falhar de forma clara e alertar por e-mail se todas as tentativas se esgotarem.
- Validar o resultado da exportaÃƒÂ§ÃƒÂ£o (ex: arquivo baixado tem tamanho > 0, extensÃƒÂ£o correta) antes de considerar a execuÃƒÂ§ÃƒÂ£o bem-sucedida Ã¢â‚¬â€� um arquivo vazio ou corrompido nÃƒÂ£o deve ser tratado como sucesso.
- Nunca falhar "silenciosamente": toda falha deve gerar log detalhado e, quando aplicÃƒÂ¡vel, disparar o alerta por e-mail definido na SeÃƒÂ§ÃƒÂ£o 5.
- Nunca logar senhas ou dados sensÃƒÂ­veis em texto puro, nem mesmo em logs de debug/desenvolvimento.
- Sempre verificar a existÃƒÂªncia e conteÃƒÂºdo do `.gitignore` antes de qualquer commit, garantindo que `.env`, arquivos de sessÃƒÂ£o salvos e relatÃƒÂ³rios baixados (que podem conter dados de clientes) nÃƒÂ£o sejam versionados.
- Ao lidar com arquivos baixados que contÃƒÂªm dados de clientes/operaÃƒÂ§ÃƒÂ£o, tratar como informaÃƒÂ§ÃƒÂ£o sensÃƒÂ­vel Ã¢â‚¬â€� evitar caminhos de pasta compartilhados publicamente ou sincronizados sem controle de acesso.

### 2.1.5 ComunicaÃƒÂ§ÃƒÂ£o e Reporte

- ComunicaÃƒÂ§ÃƒÂ£o direta e sem "enrolaÃƒÂ§ÃƒÂ£o": apontar riscos e limitaÃƒÂ§ÃƒÂµes claramente, sem suavizar problemas reais (ex: dizer explicitamente "esse seletor ÃƒÂ© frÃƒÂ¡gil e vai quebrar se o site mudar" em vez de deixar isso implÃƒÂ­cito ou omitido).
- Ao propor uma soluÃƒÂ§ÃƒÂ£o, sempre expor o trade-off embutido (ex: "vou usar espera fixa de 2s aqui em vez do ideal, que seria esperar o seletor X, porque Y Ã¢â‚¬â€� isso ÃƒÂ© uma dÃƒÂ­vida tÃƒÂ©cnica a revisitar depois").
- Diferenciar claramente entre "soluÃƒÂ§ÃƒÂ£o definitiva" e "gambiarra temporÃƒÂ¡ria para destravar o MVP" Ã¢â‚¬â€� nunca apresentar uma soluÃƒÂ§ÃƒÂ£o provisÃƒÂ³ria como se fosse definitiva.
- Ao encontrar um problema fora do escopo original (ex: um novo filtro necessÃƒÂ¡rio, uma tela adicional a mapear), sinalizar isso explicitamente em vez de simplesmente resolver por conta prÃƒÂ³pria e seguir em frente sem registro.

### 2.1.6 ValidaÃƒÂ§ÃƒÂ£o e Testes

- Testar cada etapa do fluxo isoladamente (login Ã¢â€ â€™ navegaÃƒÂ§ÃƒÂ£o Ã¢â€ â€™ aplicaÃƒÂ§ÃƒÂ£o de filtro Ã¢â€ â€™ exportaÃƒÂ§ÃƒÂ£o Ã¢â€ â€™ captura de download Ã¢â€ â€™ salvamento no destino) antes de integrar tudo em um fluxo ÃƒÂºnico Ã¢â‚¬â€� isso facilita muito o diagnÃƒÂ³stico quando algo falhar.
- Antes de considerar qualquer etapa "pronta", rodar ao menos uma vez em modo visÃƒÂ­vel (nÃƒÂ£o headless) para confirmar visualmente o comportamento esperado, alÃƒÂ©m dos testes automatizados/logs.
- Simular cenÃƒÂ¡rios de falha propositalmente durante o desenvolvimento (ex: senha errada, internet lenta) para confirmar que o tratamento de erro e o alerta por e-mail realmente funcionam antes de ir para produÃƒÂ§ÃƒÂ£o.

### 2.1.7 DocumentaÃƒÂ§ÃƒÂ£o ContÃƒÂ­nua

- Toda decisÃƒÂ£o tÃƒÂ©cnica relevante tomada durante o desenvolvimento deve ser refletida de volta neste `AGENTE.md` (SeÃƒÂ§ÃƒÂ£o 9 Ã¢â‚¬â€� Changelog), mantendo o documento como fonte ÃƒÂºnica de verdade do projeto Ã¢â‚¬â€� nÃƒÂ£o deixar decisÃƒÂµes "sÃƒÂ³ na cabeÃƒÂ§a" ou apenas em mensagens de commit.
- Ao final de cada marco importante (ex: "login funcionando", "exportaÃƒÂ§ÃƒÂ£o funcionando", "agendamento funcionando"), atualizar a SeÃƒÂ§ÃƒÂ£o 2 (Escopo Funcional) marcando os itens concluÃƒÂ­dos.
- Manter um `README.md` tÃƒÂ©cnico separado (mais voltado a "como rodar o projeto") complementando este `AGENTE.md` (mais voltado a "por que as decisÃƒÂµes foram tomadas").

### 2.1.8 AntipadrÃƒÂµes a Evitar

- Ã¢ï¿½Å’ Escrever o fluxo inteiro de uma vez sem testar partes isoladamente.
- Ã¢ï¿½Å’ Usar `sleep()` fixo e genÃƒÂ©rico como soluÃƒÂ§ÃƒÂ£o padrÃƒÂ£o para "esperar a pÃƒÂ¡gina carregar".
- Ã¢ï¿½Å’ Deixar credenciais, e-mails ou caminhos de pasta hardcoded espalhados pelo cÃƒÂ³digo.
- Ã¢ï¿½Å’ Ignorar ou silenciar exceÃƒÂ§ÃƒÂµes com `try/except: pass`.
- Ã¢ï¿½Å’ Apresentar uma soluÃƒÂ§ÃƒÂ£o provisÃƒÂ³ria sem deixar claro que ÃƒÂ© provisÃƒÂ³ria.
- Ã¢ï¿½Å’ AvanÃƒÂ§ar para automaÃƒÂ§ÃƒÂ£o em produÃƒÂ§ÃƒÂ£o sem antes validar manualmente que os dados exportados estÃƒÂ£o corretos.

---

## 3. DecisÃƒÂµes de Arquitetura

**DecisÃƒÂ£o atual (Fase 1 Ã¢â‚¬â€� ValidaÃƒÂ§ÃƒÂ£o):** Rodar localmente, na mÃƒÂ¡quina do usuÃƒÂ¡rio responsÃƒÂ¡vel pelo projeto, para treinar/validar o fluxo antes de migrar para um ambiente definitivo.

**OpÃƒÂ§ÃƒÂµes avaliadas (registradas para consulta futura quando migrar de fase):**

| OpÃƒÂ§ÃƒÂ£o | Custo | PrÃƒÂ³s | Contras | Status |
|---|---|---|---|---|
| **MÃƒÂ¡quina local** | GrÃƒÂ¡tis (sÃƒÂ³ energia) | Controle total, fÃƒÂ¡cil debugar, zero configuraÃƒÂ§ÃƒÂ£o de rede | Depende de energia/internet estÃƒÂ¡veis, sem redundÃƒÂ¢ncia, precisa que a mÃƒÂ¡quina fique ligada no horÃƒÂ¡rio agendado | Ã¢Å“â€¦ **Escolhido para Fase 1 (validaÃƒÂ§ÃƒÂ£o)** |
| **VPS pago barato** (Hetzner, Contabo, DigitalOcean) | ~R$20Ã¢â‚¬â€œ40/mÃƒÂªs | Sempre ligado, sessÃƒÂ£o/cookies persistem em disco, sem limite de execuÃƒÂ§ÃƒÂ£o, controle total via SSH | Custo fixo mensal, exige manutenÃƒÂ§ÃƒÂ£o bÃƒÂ¡sica (updates de SO/seguranÃƒÂ§a) | Ã°Å¸â€¢â€œ Candidato natural para Fase 2 (produÃƒÂ§ÃƒÂ£o) |
| **GitHub Actions (cron)** | GrÃƒÂ¡tis (atÃƒÂ© 2.000 min/mÃƒÂªs em repo privado) | Zero manutenÃƒÂ§ÃƒÂ£o de servidor, fÃƒÂ¡cil de configurar | Ambiente novo a cada execuÃƒÂ§ÃƒÂ£o (dificulta manter sessÃƒÂ£o logada), risco de bloqueio por IP de datacenter, precisa de passo extra para enviar o arquivo baixado a algum destino (Drive/S3) | Ã°Å¸â€¢â€œ Alternativa gratuita se custo for restritivo |
| **Google Cloud / AWS free tier** | GrÃƒÂ¡tis (com limites) | VM real 24/7, sessÃƒÂ£o persiste em disco | ConfiguraÃƒÂ§ÃƒÂ£o mais tÃƒÂ©cnica, risco de cobranÃƒÂ§a se ultrapassar limite, free tier da AWS expira em 12 meses | Ã°Å¸â€¢â€œ Alternativa se jÃƒÂ¡ houver familiaridade com a nuvem |
| **Render/Railway (cron gerenciado)** | ~US$5Ã¢â‚¬â€œ7/mÃƒÂªs | Deploy simples, sem gerenciar SO | Free tier nÃƒÂ£o confiÃƒÂ¡vel para cron diÃƒÂ¡rio, menos controle que VPS puro | Ã¢â€ºâ€� Descartado por ora |

**CritÃƒÂ©rio de migraÃƒÂ§ÃƒÂ£o para Fase 2:** a definir (ex: apÃƒÂ³s X dias de execuÃƒÂ§ÃƒÂ£o estÃƒÂ¡vel local, ou quando a mÃƒÂ¡quina local nÃƒÂ£o puder mais garantir disponibilidade).

### 3.2 Stack TÃƒÂ©cnica
**DecisÃƒÂ£o:** Python + Playwright.

Justificativa: Playwright oferece controle robusto sobre navegaÃƒÂ§ÃƒÂ£o, espera de elementos dinÃƒÂ¢micos e interceptaÃƒÂ§ÃƒÂ£o de downloads. Python foi escolhido pela preferÃƒÂªncia do time e facilidade de manutenÃƒÂ§ÃƒÂ£o/leitura do cÃƒÂ³digo.

**Bibliotecas previstas:**
- `playwright` (automaÃƒÂ§ÃƒÂ£o de navegador)
- `python-dotenv` (leitura segura de credenciais via `.env`)
- `logging` (nativo do Python, para registro estruturado de execuÃƒÂ§ÃƒÂ£o)

### 3.3 FrequÃƒÂªncia de ExecuÃƒÂ§ÃƒÂ£o
**DecisÃƒÂ£o:** DiÃƒÂ¡ria.

### 3.4 PÃƒÂ³s-processamento dos Dados
**DecisÃƒÂ£o:** Apenas salvar o arquivo baixado na pasta de destino. Sem consolidaÃƒÂ§ÃƒÂ£o/processamento automÃƒÂ¡tico nesta fase.

---

## 4. SeguranÃƒÂ§a e Credenciais

**DecisÃƒÂ£o:** Credenciais NUNCA devem ser armazenadas em texto puro em documentos, cÃƒÂ³digo-fonte ou repositÃƒÂ³rios. PrÃƒÂ¡ticas obrigatÃƒÂ³rias:

- Uso de arquivo `.env` local (fora do controle de versÃƒÂ£o, incluÃƒÂ­do no `.gitignore`) para armazenar usuÃƒÂ¡rio/senha
- Script lÃƒÂª as credenciais via variÃƒÂ¡veis de ambiente (`process.env` no Node.js ou `os.environ` no Python)
- **RecomendaÃƒÂ§ÃƒÂ£o:** solicitar ao cliente uma credencial dedicada de automaÃƒÂ§ÃƒÂ£o (ex: `automacao_relatorios`), separada do login pessoal da equipe Ã¢â‚¬â€� facilita auditoria e revogaÃƒÂ§ÃƒÂ£o de acesso sem impactar o usuÃƒÂ¡rio normal
- Ã¢Å¡Â Ã¯Â¸ï¿½ **AÃƒÂ§ÃƒÂ£o pendente:** login usado durante os testes iniciais foi digitado em texto puro nesta conversa de planejamento Ã¢â‚¬â€� recomenda-se **trocar a senha** desse usuÃƒÂ¡rio assim que possÃƒÂ­vel, e migrar para a credencial dedicada de automaÃƒÂ§ÃƒÂ£o quando definida com o cliente

**Pendente:** confirmar com o cliente se serÃƒÂ¡ fornecida credencial dedicada ou se o uso serÃƒÂ¡ via login pessoal existente.

---

## 5. Monitoramento e Alertas

**DecisÃƒÂ£o:** Alerta por e-mail em caso de falha na execuÃƒÂ§ÃƒÂ£o.

**CenÃƒÂ¡rios que devem disparar alerta:**
- Falha no login (credencial incorreta, sessÃƒÂ£o expirada, campo nÃƒÂ£o encontrado)
- Site fora do ar / timeout de carregamento
- BotÃƒÂ£o de exportaÃƒÂ§ÃƒÂ£o nÃƒÂ£o encontrado (indÃƒÂ­cio de mudanÃƒÂ§a de layout)
- Download nÃƒÂ£o concluÃƒÂ­do dentro de um tempo limite
- Qualquer exceÃƒÂ§ÃƒÂ£o nÃƒÂ£o tratada durante a execuÃƒÂ§ÃƒÂ£o

**Detalhes tÃƒÂ©cnicos pendentes:**
- [ ] Qual e-mail(s) deve(m) receber o alerta?
- [ ] Qual serviÃƒÂ§o usar para envio (SMTP prÃƒÂ³prio, SendGrid, Gmail API, etc.)?
- [ ] Deve haver tambÃƒÂ©m um e-mail de confirmaÃƒÂ§ÃƒÂ£o em caso de sucesso, ou sÃƒÂ³ em falha?

---

## 6. Detalhes do Sistema Alvo (JordÃ£o)

- **URL base:** phcfocosistema.com.br/jordaogestaodeimoveis/
- **Tela principal identificada:** Roteiros de ServiÃƒÂ§os
- **Filtros disponÃƒÂ­veis na tela:** Data (DE/ATÃƒâ€°), Cliente, Status, A/C, Carteira, Cidade, RegiÃƒÂ£o, Bairro, ServiÃƒÂ§o, Praga, Operador, Vendedor, Monitoramento, MotivaÃƒÂ§ÃƒÂ£o, Rede, Turnos, Status Documento, Status de Clientes, Rota, NÃ‚Âº Roteiro, NÃ‚Âº OS
- **AÃƒÂ§ÃƒÂ£o de exportaÃƒÂ§ÃƒÂ£o:** botÃƒÂ£o/ÃƒÂ­cone "Exportar Excel" (verde) e "CSV" no canto superior direito da tabela de resultados
- **AutenticaÃƒÂ§ÃƒÂ£o:** Sem 2FA Ã¢â‚¬â€� login simples via usuÃƒÂ¡rio/senha. SessÃƒÂ£o a ter duraÃƒÂ§ÃƒÂ£o confirmada em testes prÃƒÂ¡ticos.
- **Filtros que o agente deve aplicar automaticamente:** Data "DE" = data de hoje, "ATÃƒâ€°" = data de hoje (captura apenas o dia corrente). Demais filtros (Cliente, Status, A/C, Carteira, Cidade, RegiÃƒÂ£o, Bairro, ServiÃƒÂ§o, Praga, Operador, Vendedor, Monitoramento, MotivaÃƒÂ§ÃƒÂ£o, Rede, Status Documento, Status de Clientes, Rota): sempre "TODOS" / valor padrÃƒÂ£o, sem restriÃƒÂ§ÃƒÂ£o adicional.
- **Pasta de destino:** padrÃƒÂ£o local, ex: `Documentos/Relatorios_Astral/` (caminho exato completo a definir na hora da implementaÃƒÂ§ÃƒÂ£o, conforme SO da mÃƒÂ¡quina local)
- **Nomenclatura sugerida dos arquivos:** `roteiros_servicos_AAAA-MM-DD.xlsx` (data do dia da execuÃƒÂ§ÃƒÂ£o)
- **HorÃƒÂ¡rio de execuÃƒÂ§ÃƒÂ£o:** inÃƒÂ­cio do expediente (faixa 08hÃ¢â‚¬â€œ09h)

---

## 7. Perguntas em Aberto / PendÃƒÂªncias

- [x] Linguagem/stack preferida: ~~Node.js + Playwright ou~~ Python + Playwright Ã¢Å“â€¦ Decidido
- [ ] Como lidar com credenciais (usuÃƒÂ¡rio/senha fixo vs. credencial dedicada de automaÃƒÂ§ÃƒÂ£o)? Ã¢â‚¬â€� recomendaÃƒÂ§ÃƒÂ£o registrada na SeÃƒÂ§ÃƒÂ£o 4, decisÃƒÂ£o final pendente
- [x] O sistema JordÃ£o tem autenticaÃƒÂ§ÃƒÂ£o de dois fatores (2FA)? Ã¢â‚¬â€� **NÃƒÂ£o tem** Ã¢Å“â€¦ Confirmado
- [ ] Quanto tempo dura a sessÃƒÂ£o logada antes de expirar? (a testar na prÃƒÂ¡tica)
- [x] Quais filtros exatos devem ser aplicados automaticamente todo dia? Ã¢â‚¬â€� **Data: hoje atÃƒÂ© hoje**; demais filtros sempre "TODOS" Ã¢Å“â€¦ Confirmado
- [x] Qual pasta local de destino e padrÃƒÂ£o de nomenclatura dos arquivos? Ã¢â‚¬â€� **Pasta padrÃƒÂ£o tipo `Documentos/Relatorios_Astral/`** Ã¢Å“â€¦ Confirmado (caminho absoluto exato a fechar na implementaÃƒÂ§ÃƒÂ£o)
- [x] Como devem funcionar os alertas de falha? Ã¢â‚¬â€� **E-mail** Ã¢Å“â€¦ Confirmado (detalhes tÃƒÂ©cnicos ainda pendentes Ã¢â‚¬â€� ver SeÃƒÂ§ÃƒÂ£o 5)
- [x] HorÃƒÂ¡rio ideal de execuÃƒÂ§ÃƒÂ£o diÃƒÂ¡ria? Ã¢â‚¬â€� **InÃƒÂ­cio do expediente (08hÃ¢â‚¬â€œ09h)** Ã¢Å“â€¦ Confirmado
- [x] Existe autorizaÃƒÂ§ÃƒÂ£o formal do cliente para automatizar o acesso ao sistema dele? Ã¢â‚¬â€� **Sim, autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita jÃƒÂ¡ existe** Ã¢Å“â€¦ Confirmado

---

## 8. Riscos Identificados

- MudanÃƒÂ§as no layout/HTML do site podem quebrar os seletores do script (manutenÃƒÂ§ÃƒÂ£o recorrente esperada)
- Bloqueio de conta por excesso de tentativas de login automatizado, se mal configurado
- ~~QuestÃƒÂ£o contratual/ToS: automatizar acesso a sistema de terceiro sem autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita pode ser um problema~~ Ã¢â‚¬â€� Ã¢Å“â€¦ **Resolvido: autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita do cliente jÃƒÂ¡ existe**
- Credencial de automaÃƒÂ§ÃƒÂ£o foi digitada em texto puro durante o planejamento (nesta conversa) Ã¢â‚¬â€� recomenda-se trocar a senha antes de ir para produÃƒÂ§ÃƒÂ£o

---

## 9. HistÃƒÂ³rico de DecisÃƒÂµes (Changelog)

| Data | DecisÃƒÂ£o |
|---|---|
| 04/07/2026 | FrequÃƒÂªncia definida como diÃƒÂ¡ria |
| 04/07/2026 | Time possui dev disponÃƒÂ­vel Ã¢â‚¬â€� descartada opÃƒÂ§ÃƒÂ£o no-code |
| 04/07/2026 | PÃƒÂ³s-processamento: apenas salvar arquivo, sem consolidaÃƒÂ§ÃƒÂ£o |
| 04/07/2026 | Infraestrutura Fase 1: mÃƒÂ¡quina local, para validaÃƒÂ§ÃƒÂ£o/treino do fluxo |
| 04/07/2026 | Stack tÃƒÂ©cnica definida: Python + Playwright |
| 04/07/2026 | Confirmado: sistema JordÃ£o nÃƒÂ£o possui 2FA |
| 04/07/2026 | PolÃƒÂ­tica de credenciais definida: uso obrigatÃƒÂ³rio de `.env`, nunca em texto puro |
| 04/07/2026 | Filtro de data diÃƒÂ¡rio definido: sempre "hoje atÃƒÂ© hoje" |
| 04/07/2026 | Demais filtros mantidos sempre em "TODOS" (sem restriÃƒÂ§ÃƒÂ£o por cliente/status/etc.) |
| 04/07/2026 | Canal de alerta de falha definido: e-mail |
| 04/07/2026 | Pasta de destino definida: padrÃƒÂ£o local tipo `Documentos/Relatorios_Astral/` |
| 04/07/2026 | HorÃƒÂ¡rio de execuÃƒÂ§ÃƒÂ£o definido: inÃƒÂ­cio do expediente (08hÃ¢â‚¬â€œ09h) |
| 04/07/2026 | Confirmada autorizaÃƒÂ§ÃƒÂ£o formal do cliente para automatizar o acesso |
| 04/07/2026 | Adicionado perfil de atuaÃƒÂ§ÃƒÂ£o/comportamento do agente de desenvolvimento (postura sÃƒÂªnior, foco em produÃƒÂ§ÃƒÂ£o e transparÃƒÂªncia de trade-offs) |

---

## 10. Status do Planejamento Ã¢â‚¬â€� Pronto para ImplementaÃƒÂ§ÃƒÂ£o

**DecisÃƒÂµes fechadas:**
- Ã¢Å“â€¦ Infraestrutura Fase 1: mÃƒÂ¡quina local
- Ã¢Å“â€¦ Stack: Python + Playwright
- Ã¢Å“â€¦ FrequÃƒÂªncia: diÃƒÂ¡ria, 08hÃ¢â‚¬â€œ09h
- Ã¢Å“â€¦ Filtro de data: hoje atÃƒÂ© hoje / demais filtros: "TODOS"
- Ã¢Å“â€¦ PÃƒÂ³s-processamento: nenhum (apenas salvar arquivo)
- Ã¢Å“â€¦ Alertas: e-mail em caso de falha
- âœ… Infraestrutura Fase 1: mÃƒÂ¡quina local
- âœ… Stack: Python + Playwright
- âœ… FrequÃƒÂªncia: diÃƒÂ¡ria, 08hÃ¢â‚¬â€œ09h
- âœ… Filtro de data: hoje atÃƒÂ© hoje / demais filtros: "TODOS"
- âœ… PÃƒÂ³s-processamento: nenhum (apenas salvar arquivo)
- âœ… Alertas: e-mail em caso de falha
- âœ… Pasta de destino: padrÃƒÂ£o local (`Documentos/Relatorios_Astral/`)
- âœ… Sem 2FA no sistema alvo
- âœ… AutorizaÃƒÂ§ÃƒÂ£o do cliente confirmada

**PendÃƒÂªncias remanescentes (nÃƒÂ£o bloqueiam o inÃƒÂ­cio do desenvolvimento, mas devem ser resolvidas durante a implementaÃƒÂ§ÃƒÂ£o):**
- [x] Definir credencial final (login pessoal vs. dedicada de automaÃ§Ã£o) â€“ trocar senha exposta durante o planejamento
- [x] Confirmar caminho absoluto exato da pasta de destino na mÃ¡quina local
- [ ] **(Pausado)** Definir e-mail(s) destinatÃ¡rio(s) do alerta e serviÃ§o de envio (SMTP/API) - *CÃ³digo de envio estÃ¡ pronto (`src/alertas.py`), mas a ativaÃ§Ã£o real no fluxo principal foi pausada pois o e-mail corporativo requer configuraÃ§Ã£o do Administrador de TI (Senha de Aplicativo/LiberaÃ§Ã£o SMTP no Microsoft 365).*
- [x] Testar na prÃ¡tica a duraÃ§Ã£o da sessÃ£o logada

**PrÃƒÂ³ximo passo sugerido:** iniciar o projeto na IDE (Antigravity), usando este documento como contexto/system prompt do agente de desenvolvimento, comeÃƒÂ§ando pela estrutura bÃƒÂ¡sica do script (login + navegaÃƒÂ§ÃƒÂ£o + captura de download) antes de agendar a execuÃƒÂ§ÃƒÂ£o automÃƒÂ¡tica.

---

## 11. Rotina de Testes

Sempre que o usuÃƒÂ¡rio solicitar para "habilitar o navegador" ou "fazer uns testes", o assistente deve **executar automaticamente** o robÃƒÂ´ no terminal (sem exigir que o usuÃƒÂ¡rio o faÃƒÂ§a manualmente) utilizando o seguinte comando:
```powershell
.\venv\Scripts\python -c "from src.agente import executar_fluxo_completo; executar_fluxo_completo()"
```
*ObservaÃƒÂ§ÃƒÂ£o: A variÃƒÂ¡vel `HEADLESS` no `.env` deve estar como `false` para que o navegador Chromium fique visÃƒÂ­vel durante o teste.*

 # #   R e g r a s   d e   N o m e n c l a t u r a   d o s   R e l a t Ã³ r i o s 
 -   T o d o s   o s   r e l a t Ã³ r i o s   d e v e m   s e r   c a d a s t r a d o s   n o   ` a p p . p y `   c o m   o   n Ãº m e r o   c o r r e s p o n d e n t e   e m   d o i s   d Ã­ g i t o s   c o m o   p r e f i x o .   E x e m p l o :   ` 0 1   R e l a t Ã³ r i o   R o t e i r o   d o s   S e r v i Ã§ o s ` ,   ` 0 2   R e l a t Ã³ r i o   d e   C o n t i n g Ãª n c i a ` ,   e t c . 
 
 
 

## 12. Reiniciando o Servidor (PrevenÃƒÂ§ÃƒÂ£o de Fantasmas)
- ComunicaÃƒÂ§ÃƒÂ£o direta e sem "enrolaÃƒÂ§ÃƒÂ£o": apontar riscos e limitaÃƒÂ§ÃƒÂµes claramente, sem suavizar problemas reais (ex: dizer explicitamente "esse seletor ÃƒÂ© frÃƒÂ¡gil e vai quebrar se o site mudar" em vez de deixar isso implÃƒÂ­cito ou omitido).
- Ao propor uma soluÃƒÂ§ÃƒÂ£o, sempre expor o trade-off embutido (ex: "vou usar espera fixa de 2s aqui em vez do ideal, que seria esperar o seletor X, porque Y Ã¢â‚¬â€� isso ÃƒÂ© uma dÃƒÂ­vida tÃƒÂ©cnica a revisitar depois").
- Diferenciar claramente entre "soluÃƒÂ§ÃƒÂ£o definitiva" e "gambiarra temporÃƒÂ¡ria para destravar o MVP" Ã¢â‚¬â€� nunca apresentar uma soluÃƒÂ§ÃƒÂ£o provisÃƒÂ³ria como se fosse definitiva.
- Ao encontrar um problema fora do escopo original (ex: um novo filtro necessÃƒÂ¡rio, uma tela adicional a mapear), sinalizar isso explicitamente em vez de simplesmente resolver por conta prÃƒÂ³pria e seguir em frente sem registro.

### 2.1.6 ValidaÃƒÂ§ÃƒÂ£o e Testes

- Testar cada etapa do fluxo isoladamente (login Ã¢â€ â€™ navegaÃƒÂ§ÃƒÂ£o Ã¢â€ â€™ aplicaÃƒÂ§ÃƒÂ£o de filtro Ã¢â€ â€™ exportaÃƒÂ§ÃƒÂ£o Ã¢â€ â€™ captura de download Ã¢â€ â€™ salvamento no destino) antes de integrar tudo em um fluxo ÃƒÂºnico Ã¢â‚¬â€� isso facilita muito o diagnÃƒÂ³stico quando algo falhar.
- Antes de considerar qualquer etapa "pronta", rodar ao menos uma vez em modo visÃƒÂ­vel (nÃƒÂ£o headless) para confirmar visualmente o comportamento esperado, alÃƒÂ©m dos testes automatizados/logs.
- Simular cenÃƒÂ¡rios de falha propositalmente durante o desenvolvimento (ex: senha errada, internet lenta) para confirmar que o tratamento de erro e o alerta por e-mail realmente funcionam antes de ir para produÃƒÂ§ÃƒÂ£o.

### 2.1.7 DocumentaÃƒÂ§ÃƒÂ£o ContÃƒÂ­nua

- Toda decisÃƒÂ£o tÃƒÂ©cnica relevante tomada durante o desenvolvimento deve ser refletida de volta neste `AGENTE.md` (SeÃƒÂ§ÃƒÂ£o 9 Ã¢â‚¬â€� Changelog), mantendo o documento como fonte ÃƒÂºnica de verdade do projeto Ã¢â‚¬â€� nÃƒÂ£o deixar decisÃƒÂµes "sÃƒÂ³ na cabeÃƒÂ§a" ou apenas em mensagens de commit.
- Ao final de cada marco importante (ex: "login funcionando", "exportaÃƒÂ§ÃƒÂ£o funcionando", "agendamento funcionando"), atualizar a SeÃƒÂ§ÃƒÂ£o 2 (Escopo Funcional) marcando os itens concluÃƒÂ­dos.
- Manter um `README.md` tÃƒÂ©cnico separado (mais voltado a "como rodar o projeto") complementando este `AGENTE.md` (mais voltado a "por que as decisÃƒÂµes foram tomadas").

### 2.1.8 AntipadrÃƒÂµes a Evitar

- Ã¢Å’ Escrever o fluxo inteiro de uma vez sem testar partes isoladamente.
- Ã¢Å’ Usar `sleep()` fixo e genÃƒÂ©rico como soluÃƒÂ§ÃƒÂ£o padrÃƒÂ£o para "esperar a pÃƒÂ¡gina carregar".
- Ã¢Å’ Deixar credenciais, e-mails ou caminhos de pasta hardcoded espalhados pelo cÃƒÂ³digo.
- Ã¢Å’ Ignorar ou silenciar exceÃƒÂ§ÃƒÂµes com `try/except: pass`.
- Ã¢Å’ Apresentar uma soluÃƒÂ§ÃƒÂ£o provisÃƒÂ³ria sem deixar claro que ÃƒÂ© provisÃƒÂ³ria.
- Ã¢Å’ AvanÃƒÂ§ar para automaÃƒÂ§ÃƒÂ£o em produÃƒÂ§ÃƒÂ£o sem antes validar manualmente que os dados exportados estÃƒÂ£o corretos.

---

## 3. DecisÃƒÂµes de Arquitetura

**DecisÃƒÂ£o atual (Fase 1 Ã¢â‚¬â€� ValidaÃƒÂ§ÃƒÂ£o):** Rodar localmente, na mÃƒÂ¡quina do usuÃƒÂ¡rio responsÃƒÂ¡vel pelo projeto, para treinar/validar o fluxo antes de migrar para um ambiente definitivo.

**OpÃƒÂ§ÃƒÂµes avaliadas (registradas para consulta futura quando migrar de fase):**

| OpÃƒÂ§ÃƒÂ£o | Custo | PrÃƒÂ³s | Contras | Status |
|---|---|---|---|---|
| **MÃƒÂ¡quina local** | GrÃƒÂ¡tis (sÃƒÂ³ energia) | Controle total, fÃƒÂ¡cil debugar, zero configuraÃƒÂ§ÃƒÂ£o de rede | Depende de energia/internet estÃƒÂ¡veis, sem redundÃƒÂ¢ncia, precisa que a mÃƒÂ¡quina fique ligada no horÃƒÂ¡rio agendado | Ã¢Å“â€¦ **Escolhido para Fase 1 (validaÃƒÂ§ÃƒÂ£o)** |
| **VPS pago barato** (Hetzner, Contabo, DigitalOcean) | ~R$20Ã¢â‚¬â€œ40/mÃƒÂªs | Sempre ligado, sessÃƒÂ£o/cookies persistem em disco, sem limite de execuÃƒÂ§ÃƒÂ£o, controle total via SSH | Custo fixo mensal, exige manutenÃƒÂ§ÃƒÂ£o bÃƒÂ¡sica (updates de SO/seguranÃƒÂ§a) | Ã°Å¸â€¢â€œ Candidato natural para Fase 2 (produÃƒÂ§ÃƒÂ£o) |
| **GitHub Actions (cron)** | GrÃƒÂ¡tis (atÃƒÂ© 2.000 min/mÃƒÂªs em repo privado) | Zero manutenÃƒÂ§ÃƒÂ£o de servidor, fÃƒÂ¡cil de configurar | Ambiente novo a cada execuÃƒÂ§ÃƒÂ£o (dificulta manter sessÃƒÂ£o logada), risco de bloqueio por IP de datacenter, precisa de passo extra para enviar o arquivo baixado a algum destino (Drive/S3) | Ã°Å¸â€¢â€œ Alternativa gratuita se custo for restritivo |
| **Google Cloud / AWS free tier** | GrÃƒÂ¡tis (com limites) | VM real 24/7, sessÃƒÂ£o persiste em disco | ConfiguraÃƒÂ§ÃƒÂ£o mais tÃƒÂ©cnica, risco de cobranÃƒÂ§a se ultrapassar limite, free tier da AWS expira em 12 meses | Ã°Å¸â€¢â€œ Alternativa se jÃƒÂ¡ houver familiaridade com a nuvem |
| **Render/Railway (cron gerenciado)** | ~US$5Ã¢â‚¬â€œ7/mÃƒÂªs | Deploy simples, sem gerenciar SO | Free tier nÃƒÂ£o confiÃƒÂ¡vel para cron diÃƒÂ¡rio, menos controle que VPS puro | Ã¢â€ºâ€� Descartado por ora |

**CritÃƒÂ©rio de migraÃƒÂ§ÃƒÂ£o para Fase 2:** a definir (ex: apÃƒÂ³s X dias de execuÃƒÂ§ÃƒÂ£o estÃƒÂ¡vel local, ou quando a mÃƒÂ¡quina local nÃƒÂ£o puder mais garantir disponibilidade).

### 3.2 Stack TÃƒÂ©cnica
**DecisÃƒÂ£o:** Python + Playwright.

Justificativa: Playwright oferece controle robusto sobre navegaÃƒÂ§ÃƒÂ£o, espera de elementos dinÃƒÂ¢micos e interceptaÃƒÂ§ÃƒÂ£o de downloads. Python foi escolhido pela preferÃƒÂªncia do time e facilidade de manutenÃƒÂ§ÃƒÂ£o/leitura do cÃƒÂ³digo.

**Bibliotecas previstas:**
- `playwright` (automaÃƒÂ§ÃƒÂ£o de navegador)
- `python-dotenv` (leitura segura de credenciais via `.env`)
- `logging` (nativo do Python, para registro estruturado de execuÃƒÂ§ÃƒÂ£o)

### 3.3 FrequÃƒÂªncia de ExecuÃƒÂ§ÃƒÂ£o
**DecisÃƒÂ£o:** DiÃƒÂ¡ria.

### 3.4 PÃƒÂ³s-processamento dos Dados
**DecisÃƒÂ£o:** Apenas salvar o arquivo baixado na pasta de destino. Sem consolidaÃƒÂ§ÃƒÂ£o/processamento automÃƒÂ¡tico nesta fase.

---

## 4. SeguranÃƒÂ§a e Credenciais

**DecisÃƒÂ£o:** Credenciais NUNCA devem ser armazenadas em texto puro em documentos, cÃƒÂ³digo-fonte ou repositÃƒÂ³rios. PrÃƒÂ¡ticas obrigatÃƒÂ³rias:

- Uso de arquivo `.env` local (fora do controle de versÃƒÂ£o, incluÃƒÂ­do no `.gitignore`) para armazenar usuÃƒÂ¡rio/senha
- Script lÃƒÂª as credenciais via variÃƒÂ¡veis de ambiente (`process.env` no Node.js ou `os.environ` no Python)
- **RecomendaÃƒÂ§ÃƒÂ£o:** solicitar ao cliente uma credencial dedicada de automaÃƒÂ§ÃƒÂ£o (ex: `automacao_relatorios`), separada do login pessoal da equipe Ã¢â‚¬â€� facilita auditoria e revogaÃƒÂ§ÃƒÂ£o de acesso sem impactar o usuÃƒÂ¡rio normal
- Ã¢Å¡Â Ã¯Â¸ **AÃƒÂ§ÃƒÂ£o pendente:** login usado durante os testes iniciais foi digitado em texto puro nesta conversa de planejamento Ã¢â‚¬â€� recomenda-se **trocar a senha** desse usuÃƒÂ¡rio assim que possÃƒÂ­vel, e migrar para a credencial dedicada de automaÃƒÂ§ÃƒÂ£o quando definida com o cliente

**Pendente:** confirmar com o cliente se serÃƒÂ¡ fornecida credencial dedicada ou se o uso serÃƒÂ¡ via login pessoal existente.

---

## 5. Monitoramento e Alertas

**DecisÃƒÂ£o:** Alerta por e-mail em caso de falha na execuÃƒÂ§ÃƒÂ£o.

**CenÃƒÂ¡rios que devem disparar alerta:**
- Falha no login (credencial incorreta, sessÃƒÂ£o expirada, campo nÃƒÂ£o encontrado)
- Site fora do ar / timeout de carregamento
- BotÃƒÂ£o de exportaÃƒÂ§ÃƒÂ£o nÃƒÂ£o encontrado (indÃƒÂ­cio de mudanÃƒÂ§a de layout)
- Download nÃƒÂ£o concluÃƒÂ­do dentro de um tempo limite
- Qualquer exceÃƒÂ§ÃƒÂ£o nÃƒÂ£o tratada durante a execuÃƒÂ§ÃƒÂ£o

**Detalhes tÃƒÂ©cnicos pendentes:**
- [ ] Qual e-mail(s) deve(m) receber o alerta?
- [ ] Qual serviÃƒÂ§o usar para envio (SMTP prÃƒÂ³prio, SendGrid, Gmail API, etc.)?
- [ ] Deve haver tambÃƒÂ©m um e-mail de confirmaÃƒÂ§ÃƒÂ£o em caso de sucesso, ou sÃƒÂ³ em falha?

---

## 6. Detalhes do Sistema Alvo (JordÃ£o)

- **URL base:** phcfocosistema.com.br/jordaogestaodeimoveis/
- **Tela principal identificada:** Roteiros de ServiÃƒÂ§os
- **Filtros disponÃƒÂ­veis na tela:** Data (DE/ATÃƒâ€°), Cliente, Status, A/C, Carteira, Cidade, RegiÃƒÂ£o, Bairro, ServiÃƒÂ§o, Praga, Operador, Vendedor, Monitoramento, MotivaÃƒÂ§ÃƒÂ£o, Rede, Turnos, Status Documento, Status de Clientes, Rota, NÃ‚Âº Roteiro, NÃ‚Âº OS
- **AÃƒÂ§ÃƒÂ£o de exportaÃƒÂ§ÃƒÂ£o:** botÃƒÂ£o/ÃƒÂ­cone "Exportar Excel" (verde) e "CSV" no canto superior direito da tabela de resultados
- **AutenticaÃƒÂ§ÃƒÂ£o:** Sem 2FA Ã¢â‚¬â€� login simples via usuÃƒÂ¡rio/senha. SessÃƒÂ£o a ter duraÃƒÂ§ÃƒÂ£o confirmada em testes prÃƒÂ¡ticos.
- **Filtros que o agente deve aplicar automaticamente:** Data "DE" = data de hoje, "ATÃƒâ€°" = data de hoje (captura apenas o dia corrente). Demais filtros (Cliente, Status, A/C, Carteira, Cidade, RegiÃƒÂ£o, Bairro, ServiÃƒÂ§o, Praga, Operador, Vendedor, Monitoramento, MotivaÃƒÂ§ÃƒÂ£o, Rede, Status Documento, Status de Clientes, Rota): sempre "TODOS" / valor padrÃƒÂ£o, sem restriÃƒÂ§ÃƒÂ£o adicional.
- **Pasta de destino:** padrÃƒÂ£o local, ex: `Documentos/Relatorios_Astral/` (caminho exato completo a definir na hora da implementaÃƒÂ§ÃƒÂ£o, conforme SO da mÃƒÂ¡quina local)
- **Nomenclatura sugerida dos arquivos:** `roteiros_servicos_AAAA-MM-DD.xlsx` (data do dia da execuÃƒÂ§ÃƒÂ£o)
- **HorÃƒÂ¡rio de execuÃƒÂ§ÃƒÂ£o:** inÃƒÂ­cio do expediente (faixa 08hÃ¢â‚¬â€œ09h)

---

## 7. Perguntas em Aberto / PendÃƒÂªncias

- [x] Linguagem/stack preferida: ~~Node.js + Playwright ou~~ Python + Playwright Ã¢Å“â€¦ Decidido
- [ ] Como lidar com credenciais (usuÃƒÂ¡rio/senha fixo vs. credencial dedicada de automaÃƒÂ§ÃƒÂ£o)? Ã¢â‚¬â€� recomendaÃƒÂ§ÃƒÂ£o registrada na SeÃƒÂ§ÃƒÂ£o 4, decisÃƒÂ£o final pendente
- [x] O sistema Jordão tem autenticação de dois fatores (2FA)? — **Não tem** ✅ Confirmado
- [ ] Quanto tempo dura a sessão logada antes de expirar? (a testar na prática)
- [x] Quais filtros exatos devem ser aplicados automaticamente todo dia? — **Data: hoje até hoje**; demais filtros sempre "TODOS" ✅ Confirmado
- [x] Qual pasta local de destino e padrão de nomenclatura dos arquivos? — **Pasta padrão tipo `Documentos/Relatorios_Astral/`** ✅ Confirmado (caminho absoluto exato a fechar na implementação)
- [x] Como devem funcionar os alertas de falha? — **E-mail** ✅ Confirmado (detalhes técnicos ainda pendentes — ver Seção 5)
- [x] Horário ideal de execução diária? — **Início do expediente (08h–09h)** ✅ Confirmado
- [x] Existe autorização formal do cliente para automatizar o acesso ao sistema dele? — **Sim, autorização explícita já existe** ✅ Confirmado

---

## 8. Riscos Identificados

- Mudanças no layout/HTML do site podem quebrar os seletores do script (manutenção recorrente esperada)
- Bloqueio de conta por excesso de tentativas de login automatizado, se mal configurado
- ~~QuestÃƒÂ£o contratual/ToS: automatizar acesso a sistema de terceiro sem autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita pode ser um problema~~ Ã¢â‚¬â€� Ã¢Å“â€¦ **Resolvido: autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita do cliente jÃƒÂ¡ existe**
- Credencial de automaÃƒÂ§ÃƒÂ£o foi digitada em texto puro durante o planejamento (nesta conversa) Ã¢â‚¬â€� recomenda-se trocar a senha antes de ir para produÃƒÂ§ÃƒÂ£o

---

## 9. HistÃƒÂ³rico de DecisÃƒÂµes (Changelog)

| Data | DecisÃƒÂ£o |
|---|---|
| 04/07/2026 | FrequÃƒÂªncia definida como diÃƒÂ¡ria |
| 04/07/2026 | Time possui dev disponÃƒÂ­vel Ã¢â‚¬â€� descartada opÃƒÂ§ÃƒÂ£o no-code |
| 04/07/2026 | PÃƒÂ³s-processamento: apenas salvar arquivo, sem consolidaÃƒÂ§ÃƒÂ£o |
| 04/07/2026 | Infraestrutura Fase 1: mÃƒÂ¡quina local, para validaÃƒÂ§ÃƒÂ£o/treino do fluxo |
| 04/07/2026 | Stack tÃƒÂ©cnica definida: Python + Playwright |
| 04/07/2026 | Confirmado: sistema JordÃ£o nÃƒÂ£o possui 2FA |
| 04/07/2026 | PolÃƒÂ­tica de credenciais definida: uso obrigatÃƒÂ³rio de `.env`, nunca em texto puro |
| 04/07/2026 | Filtro de data diÃƒÂ¡rio definido: sempre "hoje atÃƒÂ© hoje" |
| 04/07/2026 | Demais filtros mantidos sempre em "TODOS" (sem restriÃƒÂ§ÃƒÂ£o por cliente/status/etc.) |
| 04/07/2026 | Canal de alerta de falha definido: e-mail |
| 04/07/2026 | Pasta de destino definida: padrÃƒÂ£o local tipo `Documentos/Relatorios_Astral/` |
| 04/07/2026 | HorÃƒÂ¡rio de execuÃƒÂ§ÃƒÂ£o definido: inÃƒÂ­cio do expediente (08hÃ¢â‚¬â€œ09h) |
| 04/07/2026 | Confirmada autorizaÃƒÂ§ÃƒÂ£o formal do cliente para automatizar o acesso |
| 04/07/2026 | Adicionado perfil de atuaÃƒÂ§ÃƒÂ£o/comportamento do agente de desenvolvimento (postura sÃƒÂªnior, foco em produÃƒÂ§ÃƒÂ£o e transparÃƒÂªncia de trade-offs) |

---

## 10. Status do Planejamento Ã¢â‚¬â€� Pronto para ImplementaÃƒÂ§ÃƒÂ£o

**DecisÃƒÂµes fechadas:**
- Ã¢Å“â€¦ Infraestrutura Fase 1: mÃƒÂ¡quina local
- Ã¢Å“â€¦ Stack: Python + Playwright
- Ã¢Å“â€¦ FrequÃƒÂªncia: diÃƒÂ¡ria, 08hÃ¢â‚¬â€œ09h
- Ã¢Å“â€¦ Filtro de data: hoje atÃƒÂ© hoje / demais filtros: "TODOS"
- Ã¢Å“â€¦ PÃƒÂ³s-processamento: nenhum (apenas salvar arquivo)
- Ã¢Å“â€¦ Alertas: e-mail em caso de falha
- âœ… Infraestrutura Fase 1: mÃƒÂ¡quina local
- âœ… Stack: Python + Playwright
- âœ… FrequÃƒÂªncia: diÃƒÂ¡ria, 08hÃ¢â‚¬â€œ09h
- âœ… Filtro de data: hoje atÃƒÂ© hoje / demais filtros: "TODOS"
- âœ… PÃƒÂ³s-processamento: nenhum (apenas salvar arquivo)
- âœ… Alertas: e-mail em caso de falha
- âœ… Pasta de destino: padrÃƒÂ£o local (`Documentos/Relatorios_Astral/`)
- âœ… Sem 2FA no sistema alvo
- âœ… AutorizaÃƒÂ§ÃƒÂ£o do cliente confirmada

**PendÃƒÂªncias remanescentes (nÃƒÂ£o bloqueiam o inÃƒÂ­cio do desenvolvimento, mas devem ser resolvidas durante a implementaÃƒÂ§ÃƒÂ£o):**
- [x] Definir credencial final (login pessoal vs. dedicada de automaÃ§Ã£o) â€“ trocar senha exposta durante o planejamento
- [x] Confirmar caminho absoluto exato da pasta de destino na mÃ¡quina local
- [ ] **(Pausado)** Definir e-mail(s) destinatÃ¡rio(s) do alerta e serviÃ§o de envio (SMTP/API) - *CÃ³digo de envio estÃ¡ pronto (`src/alertas.py`), mas a ativaÃ§Ã£o real no fluxo principal foi pausada pois o e-mail corporativo requer configuraÃ§Ã£o do Administrador de TI (Senha de Aplicativo/LiberaÃ§Ã£o SMTP no Microsoft 365).*
- [x] Testar na prÃ¡tica a duraÃ§Ã£o da sessÃ£o logada

**PrÃƒÂ³ximo passo sugerido:** iniciar o projeto na IDE (Antigravity), usando este documento como contexto/system prompt do agente de desenvolvimento, comeÃƒÂ§ando pela estrutura bÃƒÂ¡sica do script (login + navegaÃƒÂ§ÃƒÂ£o + captura de download) antes de agendar a execuÃƒÂ§ÃƒÂ£o automÃƒÂ¡tica.

---

## 11. Rotina de Testes

Sempre que o usuÃƒÂ¡rio solicitar para "habilitar o navegador" ou "fazer uns testes", o assistente deve **executar automaticamente** o robÃƒÂ´ no terminal (sem exigir que o usuÃƒÂ¡rio o faÃƒÂ§a manualmente) utilizando o seguinte comando:
```powershell
.\venv\Scripts\python -c "from src.agente import executar_fluxo_completo; executar_fluxo_completo()"
```
*ObservaÃƒÂ§ÃƒÂ£o: A variÃƒÂ¡vel `HEADLESS` no `.env` deve estar como `false` para que o navegador Chromium fique visÃƒÂ­vel durante o teste.*

 # #   R e g r a s   d e   N o m e n c l a t u r a   d o s   R e l a t Ã³ r i o s 
 -   T o d o s   o s   r e l a t Ã³ r i o s   d e v e m   s e r   c a d a s t r a d o s   n o   ` a p p . p y `   c o m   o   n Ãº m e r o   c o r r e s p o n d e n t e   e m   d o i s   d Ã­ g i t o s   c o m o   p r e f i x o .   E x e m p l o :   ` 0 1   R e l a t Ã³ r i o   R o t e i r o   d o s   S e r v i Ã§ o s ` ,   ` 0 2   R e l a t Ã³ r i o   d e   C o n t i n g Ãª n c i a ` ,   e t c . 
 
 
 

## 12. Reiniciando o Servidor (PrevenÃƒÂ§ÃƒÂ£o de Fantasmas)
Sempre que for necessÃƒÂ¡rio reiniciar o servidor web Flask (app.py ou main.py), NUNCA mate apenas o terminal ou a task. VocÃƒÂª DEVE rodar o comando Stop-Process -Name python -Force no PowerShell para garantir que todos os processos zumbis do Python e do Playwright sejam destruÃƒÂ­dos antes de iniciar um novo servidor. Isso evita que processos antigos fiquem presos na porta 5000 rodando cÃƒÂ³digo desatualizado.

## 13. Foco na Analise de Dados (Excel > PDF)
PDFs sao formatos de leitura humana, pessimos para manipulacao estruturada de dados.
Nosso objetivo principal e facilitar a analise de dados (linhas e colunas).
Sempre que o sistema alvo gerar um relatorio obrigatoriamente em PDF (ex: capturado via aba Blob Base64), devemos considerar isso como um passo temporario. 
A solucao ideal devera prever uma transformacao estruturada desses dados para .xlsx ou .csv, seja extraindo as informacoes diretamente do HTML antes de gerar o relatorio, seja processando o PDF baixado. O entregavel de maior valor e sempre a planilha.

## 14. Ciclo de Visibilidade do RobÃ´ (Debug vs ProduÃ§Ã£o)
Ao desenvolver um **novo** relatÃ³rio ou projeto, o robÃ´ DEVE sempre rodar em modo visÃ­vel (`HEADLESS=false` no `.env`) para que o desenvolvedor e o usuÃ¡rio possam acompanhar os cliques e o comportamento da pÃ¡gina em tempo real, diagnosticando possÃ­veis bugs e identificando onde o fluxo trava.
No entanto, assim que a construÃ§Ã£o do relatÃ³rio for concluÃ­da e validada (sucesso no fluxo de ponta a ponta, como no RelatÃ³rio 04), o robÃ´ DEVE ser configurado para modo oculto (`HEADLESS=true`). O trabalho em produÃ§Ã£o de relatÃ³rios concluÃ­dos deve ser feito de forma silenciosa (background), e o acompanhamento passa a ser feito puramente pela leitura dos Logs na interface web ou no arquivo `astral_agente.log`.

 # #   1 5 .   L i d a r   c o m   S e l e c t s   C u s t o m i z a d o s   ( D r o p d o w n s   N ã o - n a t i v o s ) 
 S i s t e m a s   q u e   u t i l i z a m   f r a m e w o r k s   m o d e r n o s   ( A n g u l a r ,   R e a c t ,   V u e )   f r e q u e n t e m e n t e   s u b s t i t u e m   a   t a g   \ < s e l e c t > \   p a d r ã o   d o   H T M L   p o r   d i v s   e s t i l i z a d a s   ( e x :   \ 
 g - s e l e c t \ ) .   
 T e n t a r   i n t e r a g i r   c o m   e s s e s   e l e m e n t o s   u t i l i z a n d o   o   m é t o d o   \ . s e l e c t _ o p t i o n ( ) \   d o   P l a y w r i g h t   r e s u l t a r á   e m   f a l h a ,   p o i s   o   e l e m e n t o   n a t i v o   g e r a l m e n t e   f i c a   o c u l t o   ( \ d i s p l a y :   n o n e \ )   o u   n ã o   r e s p o n d e   a   e v e n t o s   d e   m u d a n ç a   n a t i v o s   d a   m e s m a   f o r m a . 
 * * A   S o l u ç ã o   ( L i ç ã o   A p r e n d i d a ) : * *   
 E m   v e z   d e   t e n t a r   s e l e c i o n a r   a   o p ç ã o   d e   f o r m a   p r o g r a m á t i c a   n o   b a c k e n d   d o   D O M ,   d e v e m o s   s i m u l a r   o   c o m p o r t a m e n t o   e x a t o   d e   u m   u s u á r i o   h u m a n o : 
 1 .   L o c a l i z a r   o   \  
 c o n t a i n e r \   o u   a   s e t a   q u e   a b r e   o   d r o p d o w n   ( f r e q u e n t e m e n t e   u s a n d o   X P a t h   c o m   \  o l l o w i n g - s i b l i n g \   a   p a r t i r   d o   \ l a b e l \ ) . 
 2 .   D i s p a r a r   u m   c l i q u e   f í s i c o   ( \ . c l i c k ( ) \ )   n e s s e   c o n t a i n e r   p a r a   f o r ç a r   a   a b e r t u r a   d o   m o d a l / l i s t a   d e   o p ç õ e s . 
 3 .   I n s e r i r   u m a   p e q u e n a   e s p e r a   ( \ w a i t _ f o r _ t i m e o u t ( 5 0 0 ) \ )   p a r a   p e r m i t i r   q u e   a   a n i m a ç ã o   C S S   d e   a b e r t u r a   d o   d r o p d o w n   s e j a   c o n c l u í d a . 
 4 .   P r o c u r a r   p e l a   o p ç ã o   d e s e j a d a   p e l o   t e x t o   e x a t o   e   f o r ç a r   o   c l i q u e   ( \ . l o c a t o r ( \ t e x t = O p ç ã o \ ) . l a s t . c l i c k ( ) \ ) . 
 O   F a l l b a c k   v i a   i n j e ç ã o   J a v a S c r i p t   a i n d a   d e v e   s e r   m a n t i d o   p a r a   c a s o s   o n d e   o   d r o p d o w n   e s t e j a   i n a c e s s í v e l   f i s i c a m e n t e   ( e x :   c o b e r t o   p o r   m o d a i s   i n v i s í v e i s ) .  
 

## 16. Otimização de Ingestão no Supabase e Regras de Datas dos Relatórios

### Aprendizados da Investigação de Limpeza do Banco (Julho/2026):
1. **Filtro de Arquivos em Ingestão (`_encontrar_excel_reports`)**:
   - Para relatórios estáticos/snapshots (1, 2, 4, 5, 8, 12), o orquestrador processa APENAS o arquivo mais recente baixado (`arquivos[0]`). Processar múltiplos arquivos antigos acumulados na pasta `Relatorios/` faz com que o método `limpar_tabela()` seja executado em loop, apagando e reescrevendo o banco repetidas vezes.
   - Para relatórios por período (6, 11, 13, 14, 15), o orquestrador considera apenas arquivos gerados na janela recente da execução atual (últimas 2 horas).

2. **Validação de Colunas no Relatório 02 (Contratos)**:
 # #   1 5 .   L i d a r   c o m   S e l e c t s   C u s t o m i z a d o s   ( D r o p d o w n s   N ã o - n a t i v o s ) 
 S i s t e m a s   q u e   u t i l i z a m   f r a m e w o r k s   m o d e r n o s   ( A n g u l a r ,   R e a c t ,   V u e )   f r e q u e n t e m e n t e   s u b s t i t u e m   a   t a g   \ < s e l e c t > \   p a d r ã o   d o   H T M L   p o r   d i v s   e s t i l i z a d a s   ( e x :   \ 
 g - s e l e c t \ ) .   
 T e n t a r   i n t e r a g i r   c o m   e s s e s   e l e m e n t o s   u t i l i z a n d o   o   m é t o d o   \ . s e l e c t _ o p t i o n ( ) \   d o   P l a y w r i g h t   r e s u l t a r á   e m   f a l h a ,   p o i s   o   e l e m e n t o   n a t i v o   g e r a l m e n t e   f i c a   o c u l t o   ( \ d i s p l a y :   n o n e \ )   o u   n ã o   r e s p o n d e   a   e v e n t o s   d e   m u d a n ç a   n a t i v o s   d a   m e s m a   f o r m a . 
 * * A   S o l u ç ã o   ( L i ç ã o   A p r e n d i d a ) : * *   
 E m   v e z   d e   t e n t a r   s e l e c i o n a r   a   o p ç ã o   d e   f o r m a   p r o g r a m á t i c a   n o   b a c k e n d   d o   D O M ,   d e v e m o s   s i m u l a r   o   c o m p o r t a m e n t o   e x a t o   d e   u m   u s u á r i o   h u m a n o : 
 1 .   L o c a l i z a r   o   \  
 c o n t a i n e r \   o u   a   s e t a   q u e   a b r e   o   d r o p d o w n   ( f r e q u e n t e m e n t e   u s a   X P a t h   c o m   \  o l l o w i n g - s i b l i n g \   a   p a r t i r   d o   \ l a b e l \ ) . 
 2 .   D i s p a r a r   u m   c l i q u e   f í s i c o   ( \ . c l i c k ( ) \ )   n e s s e   c o n t a i n e r   p a r a   f o r ç a r   a   a b e r t u r a   d o   m o d a l / l i s t a   d e   o p ç õ e s . 
 3 .   I n s e r i r   u m a   p e q u e n a   e s p e r a   ( \ w a i t _ f o r _ t i m e o u t ( 5 0 0 ) \ )   p a r a   p e r m i t i r   q u e   a   a n i m a ç ã o   C S S   d e   a b e r t u r a   d o   d r o p d o w n   s e j a   c o n c l u í d a . 
 4 .   P r o c u r a r   p e l a   o p ç ã o   d e s e j a d a   p e l o   t e x t o   e x a t o   e   f o r ç a r   o   c l i q u e   ( \ . l o c a t o r ( \ t e x t = O p ç ã o \ ) . l a s t . c l i c k ( ) \ ) . 
 O   F a l l b a c k   v i a   i n j e ç ã o   J a v a S c r i p t   a i n d a   d e v e   s e r   m a n t i d o   p a r a   c a s o s   o n d e   o   d r o p d o w n   e s t e j a   i n a c e s s í v e l   f i s i c a m e n t e   ( e x :   c o b e r t o   p o r   m o d a i s   i n v i s í v e i s ) .  
 

## 16. Otimização de Ingestão no Supabase e Regras de Datas dos Relatórios

### Aprendizados da Investigação de Limpeza do Banco (Julho/2026):
1. **Filtro de Arquivos em Ingestão (`_encontrar_excel_reports`)**:
   - Para relatórios estáticos/snapshots (1, 2, 4, 5, 8, 12), o orquestrador processa APENAS o arquivo mais recente baixado (`arquivos[0]`). Processar múltiplos arquivos antigos acumulados na pasta `Relatorios/` faz com que o método `limpar_tabela()` seja executado em loop, apagando e reescrevendo o banco repetidas vezes.
   - Para relatórios por período (6, 11, 13, 14, 15), o orquestrador considera apenas arquivos gerados na janela recente da execução atual (últimas 2 horas).

2. **Validação de Colunas no Relatório 02 (Contratos)**:
   - A classe `Ingestor02Contratos` teve seu parâmetro ajustado para `min_colunas = 7` (e não 8) para compatibilidade nativa com a planilha de 7 colunas gerada pelo sistema Jordão.

3. **Proteção contra Anos Fictícios (`0001`)**:
   - Na limpeza por período (`limpar_periodo`), o sistema filtra apenas datas com anos válidos entre `2000` e `2100`. Linhas de cabeçalho/totais sem data que viravam o ano `0001` são ignoradas antes dos comandos de exclusão.

4. **DIRETRIZ FUTURA (REVISÃO INDIVIDUAL POR RELATÓRIO)**:
   - **MUITO IMPORTANTE:** Precisaremos rever o robô individualmente para cada relatório e as regras de datas para extração (filtros de início/fim), garantindo que as premissas de filtro de cada tela combinem exatamente com a estratégia de persistência no Supabase.

## 17. Centralização da Execução no Servidor Web (app.py) e Controle Remoto via Celular

### Decisões de Arquitetura e Limpeza de Rotas (Julho/2026):

1. **Eliminação Permanente da Rota B (CLI Genérico)**:
   - A rota de linha de comando (`src/orquestrador.py:executar` e `run_daily.sh`) foi **desativada**. Essa rota antiga gerava registros de resumo genéricos de "Lote Completo (Todos)" e causava limpezas repetidas em loop no Supabase.
   - O arquivo `run_daily.sh` foi mantido apenas como aviso de deprecação e o `orquestrador.py` retém unicamente funções auxiliares puras (`_encontrar_excel_reports`, `_registrar_execucao`).

2. **Canal Único Canonical de Execução (`app.py`)**:
   - Todo o disparo de automação (manual ou agendado em `agendamento.json`) passa exclusivamente pelo servidor Web Flask ([app.py](file:///c:/projetos/Jordao%20Automatizacao/app.py)).
   - **Garantia de Auditoria Detalhada:** Cada relatório/arquivo extraído gera um registro individual no Supabase detalhando nome, período, quantidade de linhas inseridas e duplicados.

3. **Arquitetura de Controle Remoto via Celular (Render ➔ Supabase ➔ VM)**:
   - Para permitir que o usuário dispare o robô pelo celular de qualquer lugar do mundo com 100% de segurança, criamos uma fila de mensagens na tabela `comandos_remotos` no Supabase.
   - O Render (Online) grava solicitações do tipo `extracao_massa`, `extracao_relatorio` ou `salvar_agendamento` com `status = 'pendente'`.
   - A VM Windows roda uma thread em segundo plano (`ouvinte_comandos_remotos` em `app.py`) que lê novos comandos a cada 5s, abre o Playwright localmente na VM, executa a tarefa e atualiza o status para `em_execucao` ➔ `concluido`.

4. **Inicialização Automática 24/7 na VM Windows**:
   - Para garantir que o `app.py` esteja sempre ativo na VM (mesmo após reinicializações automáticas do Windows), foi configurado um atalho na pasta Startup do sistema (`C:\Users\PC Faro\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\AgenteJordao_Startup.lnk`), garantindo disponibilidade 24 horas por dia.
