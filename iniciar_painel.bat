@echo off
echo ========================================================
echo         INICIANDO PAINEL - AGENTE Jordão
echo ========================================================
echo.

:: Verifica se o Python está instalado
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRO] O Python nao foi encontrado no seu computador!
    echo Por favor, instale o Python (marque a opcao "Add Python to PATH" na instalacao).
    pause
    exit /b
)

:: Verifica se o ambiente virtual existe, se não, cria
IF NOT EXIST "venv" (
    echo [INFO] Primeira execucao detectada. Configurando ambiente virtual...
    python -m venv venv
    echo [INFO] Instalando dependencias (isso pode demorar alguns minutos)...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo [INFO] Instalando navegador do robô (Playwright)...
    playwright install chromium
    echo [INFO] Tudo pronto!
) ELSE (
    echo [INFO] Ativando ambiente virtual...
    call venv\Scripts\activate.bat
)

echo.
echo [INFO] Iniciando o servidor local...
echo [INFO] Acesse http://127.0.0.1:5001 no seu navegador!
echo.
python app.py

pause
