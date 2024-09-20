@echo off
rem Server Shutdown Script for PowerChute Business Edition

rem ===== USAGE INSTRUCTIONS =====
rem 1. Ensure this script is run with administrator privileges.
rem 2. Place this script in a secure location, as it contains sensitive information.
rem 3. Update the DOMAIN, USERNAME, and PASSWORD variables below with your credentials.
rem 4. Add or remove servers in the "Define servers" section as needed.
rem 5. The script will attempt to shut down each server in sequence.
rem 6. Check the log file (default: C:\PSTools\ServerShutdown.log) for results.
rem 7. It's recommended to test this script in a controlled environment first.
rem ===============================

rem Set variables
set DOMAIN=domain.local
set USERNAME=username
set PASSWORD=strongpassword
set LOGFILE=C:\ServerShutdown.log

rem Define servers
set pc1=107Win10Test
set pc2=107Win7Test
rem Add more servers as needed:
rem set pc3=AnotherServerName

rem Create or append to log file
echo Server Shutdown Script executed at %date% %time% >> %LOGFILE%

rem Shutdown servers
for /L %%i in (1,1,2) do (
    if defined pc%%i (
        call :ShutdownServer %%pc%%i%%
        rem Add a delay between shutdowns
        timeout /t 5 /nobreak >nul
    )
)

echo Shutdown commands sent to all servers.
echo All shutdown commands completed at %date% %time% >> %LOGFILE%
echo ---------------------------------------- >> %LOGFILE%

exit /b

:ShutdownServer
set server=%1
echo Shutting down %server%...
echo Sending shutdown command to %server% at %date% %time% >> %LOGFILE%

rem Establish connection with credentials
net use \\%server%.%DOMAIN% /user:%DOMAIN%\%USERNAME% %PASSWORD%

if %ERRORLEVEL% EQU 0 (
    rem Connection established, proceed with shutdown
    shutdown /s /f /m \\%server%.%DOMAIN% /t 0 /d p:0:0 /c "Remote shutdown initiated"
    if %ERRORLEVEL% EQU 0 (
        echo Shutdown command sent successfully to %server% >> %LOGFILE%
        rem Test if the server is actually shutting down
        ping -n 1 -w 5000 %server% >nul
        if %ERRORLEVEL% EQU 0 (
            echo Warning: %server% is still responding after shutdown command >> %LOGFILE%
        ) else (
            echo %server% appears to be shutting down >> %LOGFILE%
        )
    ) else (
        echo Failed to send shutdown command to %server%. Error code: %ERRORLEVEL% >> %LOGFILE%
    )
    
    rem Remove the connection
    net use \\%server%.%DOMAIN% /delete
) else (
    echo Failed to establish connection with %server%. Error code: %ERRORLEVEL% >> %LOGFILE%
)

exit /b