@echo off
rem Starts The Kill-Day Almanac from this drive. Close this window to stop it.
title The Kill-Day Almanac
cd /d "%~dp0"
echo Starting The Kill-Day Almanac. Your browser will open shortly.
echo Keep this window open while you use the library. Close it when finished.
"tools\windows-amd64\killday-serve.exe" --library "." --open
echo.
echo The Almanac could not start. Open START-HERE.html for the files directly.
pause
