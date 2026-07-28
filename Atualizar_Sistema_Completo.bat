@echo off
chcp 65001 >nul
echo ========================================================
echo     ATUALIZACAO COMPLETA - JORDAO (RENDER + VM ORACLE)
echo ========================================================
echo.

cd /d "%~dp0"

echo [INFO] Verificando alteracoes no repositorio...
git status --short
echo.

set "MSG="
set /p MSG="Digite a mensagem do commit (ou pressione ENTER para mensagem padrao): "
if "%MSG%"=="" set "MSG=Atualizacao automatica do sistema"

echo.
echo [1/3] Adicionando e criando commit local...
git add -A
git commit -m "%MSG%"
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] Nenhuma alteracao nova detectada localmente para commitar.
)

echo.
echo [2/3] Enviando codigo para o GitHub (branch master)...
git push origin master
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao enviar para o GitHub! Verifique sua conexao ou permissoes.
    goto LOG
)
echo [SUCESSO] Codigo enviado com sucesso ao GitHub!

echo.
echo [3/3 - RENDER] Disparando sinal de deploy imediato no Render...
powershell -Command "Invoke-RestMethod -Uri 'https://api.render.com/deploy/srv-d9i2uibh2c0s73827k40?key=wVTdZiCxMfE' -Method Post" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SUCESSO] Webhook enviado! O Dashboard no Render esta sendo reconstruido.
) else (
    echo [AVISO] Nao foi possivel disparar o webhook direto, mas o Render atualizara via Git.
)

echo.
echo [3/3 - VM ORACLE] Atualizando e reiniciando o robo na VM Oracle via SSH...
"C:\Program Files\PuTTY\plink.exe" -batch -load "pibo_mv1" -l ubuntu "cd /home/ubuntu/Jordao-Automatizacao && git pull origin master && pm2 restart jordao-agente && sleep 2 && pm2 status"
if %ERRORLEVEL% EQU 0 (
    echo [SUCESSO] Robo na VM Oracle atualizado e reiniciado com sucesso via PM2!
) else (
    echo [AVISO] Falha ao comunicar com a VM via Plink.
)

echo.
:LOG
echo ========================================================
echo         RESUMO DOS ULTIMOS COMMITS
echo ========================================================
git log --oneline -5
echo.

echo ========================================================
echo         STATUS DOS AMBIENTES
echo ========================================================
echo  * Render (Dashboard Web): https://jordao-dashboard.onrender.com/dashboard
echo  * VM Oracle Cloud: Atualizada e rodando via PM2
echo ========================================================
echo.

pause
