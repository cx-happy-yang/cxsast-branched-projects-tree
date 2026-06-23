@echo off
REM Build CxSAST Tree Manager into a single .exe
REM Prerequisites: pip install pyinstaller waitress (and the SDK)

cd /d "%~dp0"

echo.
echo ========================================
echo Building CxSAST Tree Manager...
echo ========================================
echo.
echo Prerequisites: pip install -r requirements.txt pyinstaller waitress
echo.

python -m PyInstaller --clean --noconfirm cxsast-tree-manager.spec

echo.
echo ========================================
echo Build complete!
echo.
echo Output:  dist\CxSAST-TreeManager.exe  (%~z1 bytes)
echo.
echo To deploy to a customer machine:
echo   1. Copy dist\CxSAST-TreeManager.exe to the target server
echo   2. Set environment variables:
echo      set CXSAST_BASE_URL=https://cxserver.customer.local
echo      set CXSAST_USERNAME=admin
echo      set CXSAST_PASSWORD=their-password
echo      set CXSAST_VERIFY=False
echo      set APP_API_KEY=choose-a-secret-key
echo   3. Run CxSAST-TreeManager.exe
echo   4. Open http://localhost:5000
echo ========================================
