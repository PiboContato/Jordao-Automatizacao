@echo off
chcp 65001 >nul
echo ========================================================
echo         INICIANDO PAINEL - AGENTE JORDAO
echo ========================================================
echo.

:: Verifica se o ambiente virtual existe
if exist venv\Scripts\activate.bat goto RUN

echo [INFO] Ambiente virtual nao encontrado. Criando venv...
py -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao criar ambiente virtual! O Python esta instalado no PATH?
    goto END
)

echo [INFO] Instalando dependencias (isso pode demorar)...
call venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install chromium
echo [INFO] Instalacao finalizada!

:RUN
echo [INFO] Ativando ambiente virtual...
call venv\Scripts\activate.bat

echo [INFO] Encerrando processos antigos na porta 5001 (se houver)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do taskkill /f /pid %%a >nul 2>&1

echo [INFO] Iniciando o servidor app.py em segundo plano...
start "" pythonw app.py

echo [INFO] Abrindo o navegador (Aguarde 3 segundos)...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5001

echo [INFO] Tudo certo! O terminal sera fechado automaticamente em 3 segundos.
timeout /t 3 /nobreak >nul
exit
