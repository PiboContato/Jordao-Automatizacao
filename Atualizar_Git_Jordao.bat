@echo off
chcp 65001 >nul
echo ========================================================
echo         ATUALIZAR GIT - AGENTE JORDAO
echo ========================================================
echo.

cd /d "%~dp0"

echo [INFO] Verificando alteracoes no repositorio...
git status --short
echo.

set "MSG="
set /p MSG="Digite a mensagem do commit (ou pressione ENTER para mensagem padrao): "
if "%MSG%"=="" set "MSG=Atualizacao automatica via bat"

echo.
echo [INFO] Adicionando todos os arquivos...
git add -A

echo [INFO] Criando commit: "%MSG%"...
git commit -m "%MSG%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AVISO] Nenhuma alteracao nova para commitar.
)

echo [INFO] Enviando para o GitHub (branch master)...
git push origin master
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Falha ao enviar para o GitHub! Verifique sua conexao ou permissoes.
    goto LOG
)

echo.
echo [INFO] Push realizado com sucesso!
echo [INFO] Disparando atualizacao imediata no Render...
powershell -Command "Invoke-RestMethod -Uri 'https://api.render.com/deploy/srv-d9i2uibh2c0s73827k40?key=wVTdZiCxMfE' -Method Post" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SUCESSO] Sinal de deploy enviado com sucesso ao Render! O site esta sendo reconstruido.
) else (
    echo [AVISO] Nao foi possivel disparar o hook, mas o Render devera atualizar automaticamente.
)
echo.

:LOG
echo ========================================================
echo         ULTIMOS COMMITS
echo ========================================================
git log --oneline -5
echo.

echo ========================================================
echo         STATUS DO RENDER
echo ========================================================
echo Acompanhe o deploy em:
echo https://dashboard.render.com
echo.
echo Ou teste o site direto:
echo https://jordao-dashboard.onrender.com/login
echo.

:END
pause
