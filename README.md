# Jordão Automatizacao — README Técnico

> Como rodar o projeto. Para decisões de arquitetura, consulte o [AGENTE.md](./AGENTE.md).

---

## Pré-requisitos

- Python 3.14+ (verificar com `py --version`)
- Acesso à internet (para acessar o sistema Jordão)
- Arquivo `.env` configurado (ver abaixo)

---

## Configuração inicial (apenas uma vez)

### 1. Criar o ambiente virtual e instalar dependências

```powershell
# Na raiz do projeto (c:\Jordão Automatizacao)
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -m playwright install chromium
```

### 2. Criar o arquivo `.env`

```powershell
copy .env.example .env
```

Edite o `.env` com as credenciais reais. **Nunca commitar este arquivo.**

### 3. Validar configurações

```powershell
py main.py --testar-config
```

### 4. Testar envio de e-mail

```powershell
py main.py --testar-email
```

---

## Execução do Painel Web

```powershell
# Com ambiente virtual ativo:
py app.py

# Sem ativar o venv (usando o Python do venv diretamente):
.\venv\Scripts\python.exe app.py
```

O servidor será iniciado. Acesse no seu navegador: **http://127.0.0.1:5000**

---

## Execução em modo visível (para debug)

No `.env`, defina:
```
HEADLESS=false
```
O navegador abrirá em tela cheia para acompanhamento visual.

---

## Agendamento diário (Windows Task Scheduler)

1. Abra o **Agendador de Tarefas** (`taskschd.msc`)
2. Crie nova tarefa básica:
   - **Nome:** Agente Jordão — Roteiros
   - **Trigger:** Diário, às 08:00
   - **Ação:** Iniciar programa
     - **Programa:** `C:\Jordão Automatizacao\venv\Scripts\python.exe`
     - **Argumentos:** `app.py`
     - **Iniciar em:** `C:\Jordão Automatizacao`
3. Em **Condições**: desmarcar "Iniciar somente se o computador estiver na alimentação CA" se necessário
4. Em **Configurações**: marcar "Executar tarefa assim que possível se uma execução agendada for perdida"

---

## Estrutura do projeto

```
Jordão Automatizacao/
├── app.py                   # Ponto de entrada (Servidor Web do Painel)
├── main.py                  # Utilitários de diagnóstico (teste de email/config)
├── requirements.txt         # Dependências Python
├── .env.example             # Template de configuração (versionar)
├── .env                     # Configurações reais (NUNCA versionar)
├── .gitignore
├── AGENTE.md                # Documento vivo de arquitetura e decisões
├── README.md                # Este arquivo
├── templates/               # Arquivos HTML do painel web
│   └── dashboard.html
├── static/                  # Arquivos estáticos (CSS)
│   └── style.css
├── src/
│   ├── __init__.py
│   ├── base_agente.py       # Automação Playwright (Motor base de execução)
│   ├── alertas.py           # Envio de e-mails
│   ├── config.py            # Leitura centralizada do .env
│   ├── logger.py            # Configuração de logging
│   ├── utils.py             # Utilitários (arquivos, validação, etc.)
│   └── relatorios/          # Scripts de extração de cada relatório (1 ao 15)
├── logs/                    # Logs gerados automaticamente (não versionar)
└── relatorios/              # Relatórios baixados em Excel/CSV (não versionar)
```

---

## Logs

Logs são gravados em `logs/astral_agente.log` (rotativo, máx 5MB × 3 arquivos).

Para acompanhar em tempo real:
```powershell
Get-Content .\logs\astral_agente.log -Wait -Tail 50
```

---

## Solução de problemas

| Sintoma | Causa provável | Ação |
|---|---|---|
| `EnvironmentError: variável ausente` | `.env` não configurado | Copiar `.env.example` → `.env` e preencher |
| `TimeoutError` no login | Site lento / URL errada | Verificar `ASTRAL_URL` e conexão com internet |
| `Seletor não encontrado` | Layout do site mudou | Inspecionar o site e atualizar `Seletores` em `agente.py` |
| Arquivo baixado vazio | Sem dados no dia / erro de exportação | Rodar com `HEADLESS=false` e observar |
| E-mail de alerta não chegou | Credenciais SMTP erradas | Rodar `py main.py --testar-email` |
