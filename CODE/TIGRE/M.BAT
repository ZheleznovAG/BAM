@echo off
rem legacy tigre library cleanup removed
smartdrv c+
wmake -e -f tigre.mak  %1 > err
smartdrv c
type err
