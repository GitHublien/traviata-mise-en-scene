@echo off
REM ============================================================
REM   LANCER LE SITE — La Traviata Mise en scène
REM   Double-clic sur ce fichier = site qui s'ouvre dans le navigateur
REM ============================================================

cd /d "%~dp0"
title Traviata - Serveur local

echo.
echo ===============================================
echo   LA TRAVIATA - Mise en scene Marchese
echo   Lancement du serveur local...
echo ===============================================
echo.

REM Detection du port libre (essaie 8765, 8766, 8767...)
set PORT=8765
:findport
netstat -an | find ":%PORT% " | find "LISTENING" >nul 2>&1
if %ERRORLEVEL%==0 (
    set /a PORT+=1
    if %PORT% GTR 8780 goto error_port
    goto findport
)

echo Serveur HTTP sur http://localhost:%PORT%
echo.
echo Le navigateur va s'ouvrir dans 2 secondes.
echo Ne ferme PAS cette fenetre tant que tu utilises le site.
echo Ferme cette fenetre quand tu as fini.
echo.

REM Lance le navigateur en arriere-plan apres 2 secondes
start /b "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:%PORT%"

REM Lance le serveur Python avec support Range (essentiel pour le seek video)
REM On utilise serve.py au lieu de "python -m http.server" parce que le module
REM standard ne supporte PAS les requetes Range : quand on cherche dans la timeline
REM video, il renvoie tout depuis zero, donc la video revient au debut.
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py serve.py %PORT%
    goto end
)
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python serve.py %PORT%
    goto end
)
where python3 >nul 2>&1
if %ERRORLEVEL%==0 (
    python3 serve.py %PORT%
    goto end
)

echo.
echo ERREUR : Python n'est pas installe sur cette machine.
echo Telecharge Python depuis https://www.python.org puis relance ce fichier.
pause
exit /b 1

:error_port
echo ERREUR : Aucun port libre entre 8765 et 8780.
pause
exit /b 1

:end
