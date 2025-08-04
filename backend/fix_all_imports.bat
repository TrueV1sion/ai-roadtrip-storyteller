@echo off
echo === Fixing Backend Import Issues ===
echo.
powershell -ExecutionPolicy Bypass -File fix_all_imports.ps1
echo.
echo Press any key to exit...
pause > nul