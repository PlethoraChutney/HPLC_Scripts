@echo off

set date_filename=results_%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%
mkdir %date_filename%
move *.arw .\%date_filename% >nul

for /f "delims=" %%A in ('python assemble_rename_traces.py .\%date_filename%\') do set "descriptive_filename=%%A"
ren %date_filename% %descriptive_filename% >nul

if exist %descriptive_filename% (
  copy auto_graph.R .\%descriptive_filename% >nul
  cd .\%descriptive_filename%
  Rscript .\auto_graph.R --no-save --no-restore >nul
  del .\auto_graph.R
) else (
  echo The analyzed trace folder is missing. Exiting without making graphs...
  pause >nul
  exit
)
exit
