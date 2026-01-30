@echo off
title Abrindo RecomendaProf
echo =====================================================
echo    INICIALIZANDO O MOTOR DE RECOMENDACAO...
echo =====================================================
echo.

:: Verifica se a venv existe antes de tentar abrir
if not exist venv\Scripts\activate.bat (
    echo [ERRO] Ambiente virtual nao encontrado. 
    echo Por favor, execute INSTALAR_RECOMENDAPROF.bat primeiro.
    pause
    exit /b
)

call venv\Scripts\activate
streamlit run streamlit_app.py

pause