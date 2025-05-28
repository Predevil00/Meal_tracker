@echo off
:loop
set /p usercmd=Enter command (add/suggest/list/delete...): 
python meal.py %usercmd%
echo.
goto loop
