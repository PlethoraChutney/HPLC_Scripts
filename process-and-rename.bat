@echo off

set /P new_name="Rename experiment to: "

python appia.py -v process ./* --id "%new_name%" --output-dir "%new_name%" --database

if %ERRORLEVEL%==1 (
    PAUSE
)