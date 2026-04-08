@echo off
echo Lancement de Paffloat avec Docker...
docker compose up -d --build

echo.
echo Patientez quelques secondes le temps que le serveur demarre...
timeout /t 3 /nobreak > NUL

echo Ouverture du navigateur...
start http://localhost:8000

echo.
echo Paffloat est en ligne ! Vous pouvez fermer cette fenetre.
pause
