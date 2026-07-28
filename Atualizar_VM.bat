@echo off
cd /d "C:\projetos\Jordao Automatizacao"

echo === 1) COMMIT E PUSH LOCAL ===
git add -A
git diff --cached --quiet || git commit -m "atualizacao via Atualizar_VM.bat"
git push origin master

echo.
echo === 2) DEPLOY NA VM ORACLE ===
"C:\Program Files\PuTTY\plink.exe" -ssh -pw 2022 ubuntu@168.138.234.37 "cd /home/ubuntu/Jordao-Automatizacao && git pull && pm2 restart jordao-agente && sleep 3 && pm2 logs jordao-agente --lines 10 --nostream"

echo.
echo === CONCLUIDO ===
pause
