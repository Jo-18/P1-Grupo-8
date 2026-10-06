@echo off
rem ==========================================================================
rem  Instala las dependencias de Python del proyecto MCOC P1 (grupo 8).
rem  OpenSeesPy 3.8.0.0 necesita Python 3.12. Unity usa "py -3.12" si existe.
rem ==========================================================================
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 goto sinpython
echo Python 3.12 encontrado. Instalando dependencias...
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 goto errorpip
py -3.12 -c "import openseespy.opensees; print('openseespy OK')"
if errorlevel 1 goto erroropensees
echo.
echo Listo: Unity usara "py -3.12" con OpenSees para recalcular.
echo En Unity, pestana ANALISIS, el boton "Revisar Python" debe decir "Motor de calculo: OpenSees".
pause
exit /b 0

:sinpython
echo No se encontro Python 3.12.
echo Instalalo desde https://www.python.org/downloads/ (version 3.12, marca "Add python.exe to PATH")
echo o en una terminal con:  winget install -e --id Python.Python.3.12
echo Luego vuelve a ejecutar este archivo.
pause
exit /b 1

:errorpip
echo No se pudieron instalar las dependencias. Revisa el mensaje de arriba (conexion a internet o permisos).
pause
exit /b 1

:erroropensees
echo openseespy se instalo pero no se puede importar. Revisa el mensaje de arriba.
echo Mientras tanto, en Unity puedes activar "calcular con el solver de verificacion" (pestana ANALISIS).
pause
exit /b 1
