@echo off
if "%1"=="" GOTO NO_NBR
pkzip bkp\backup%1 *.h* *.c* *.mak *.cfg *.rsp *.bat *.asm
rem xcopy bkp\backup%1.zip Z:\TIGRE\BKP
goto END

:NO_NBR
dir bkp\backup*.zip

:END
