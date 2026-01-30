@echo off
title Instalador RecomendaProf
echo =====================================================
echo    INSTALANDO AMBIENTE E DEPENDENCIAS (AGUARDE)
echo =====================================================
echo.

:: Verifica se o Python esta no PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado! Por favor, instale o Python 3.10 ou superior.
    pause
    exit /b
)

echo 1/4 - Criando ambiente virtual (venv)...
python -m venv venv

echo 2/4 - Ativando ambiente e atualizando pip...
call venv\Scripts\activate
python -m pip install --upgrade pip

echo 3/4 - Instalando bibliotecas do requirements.txt...
pip install -r requirements.txt

echo 4/4 - Baixando modelo de linguagem spaCy (Portugues)...
python -m spacy download pt_core_news_md

echo.
echo =====================================================
echo    INSTALACAO CONCLUIDA COM SUCESSO!
echo    Agora voce pode abrir o bot pelo arquivo:
echo    ABRIR_APLICACAO.bat
echo =====================================================
pause