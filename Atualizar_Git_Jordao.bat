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

set /p MSG="Digite a mensagem do commit: "
if "%MSG%"=="" set MSG="Atualizacao automatica via bat"

echo.
echo [INFO] Adicionando todos os arquivos...
git add -A

echo [INFO] Criando commit...
git commit -m "%MSG%"
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] Nenhuma alteracao para commitar ou erro ao commitar.
    echo [INFO] Pulando para abertura do navegador...
    goto OPEN
)

echo [INFO] Enviando para o GitHub (isso aciona o deploy no Render)...
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao enviar para o GitHub!
    pause
    goto END
)

echo [INFO] Push realizado com sucesso!
echo [INFO] O Render ira atualizar automaticamente (pode levar 1-2 minutos).
echo.

:OPEN
echo [INFO] Abrindo o painel no navegador...
start https://jordao-dashboard.onrender.com/login

echo.
echo [INFO] Concluido! O terminal sera fechado em 3 segundos.
timeout /t 3 /nobreak >nul

:END
exit
