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
    echo [AVISO] Nenhuma alteracao para commitar ou falha no commit.
    echo [INFO] Tentando enviar commits anteriores pendentes, se houver...
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
echo [INFO] O Render ira atualizar automaticamente em 1-2 minutos.
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
