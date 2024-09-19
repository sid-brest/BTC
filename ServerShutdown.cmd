@echo off
rem Server Shutdown Script for PowerChute Business Edition

rem Usage Instructions:
rem To use this script:
rem 1. Save it as "ServerShutdown.cmd" in the PowerChute Business Edition command files directory.
rem 2. Replace your_password_here with the actual domain administrator password.
rem 3. Verify that the PSSHUTDOWN path is correct for your system.
rem 4. Ensure that the LOGFILE path is accessible and writable.
rem 5. Add or remove server variables as needed at the top of the script.
rem 6. If you add or remove servers, adjust the range in the for loop. 
rem    For example, if you have 5 servers, change for /L %%i in (1,1,3) to for /L %%i in (1,1,5).

rem Set variables
set PSSHUTDOWN=C:\Tools\PsTools\PsShutdown.exe
set DOMAIN=domainname.local
set USERNAME=administrator
set PASSWORD=your_password_here
set LOGFILE=C:\Program Files\APC\PowerChute Business Edition\agent\cmdfiles\ServerShutdown.log

rem Define servers
set pc1=server1
set pc2=server2
set pc3=server3
rem Add more servers as needed, e.g.:
rem set pc4=server4
rem set pc5=server5

rem Create or append to log file
echo Server Shutdown Script executed at %date% %time% >> %LOGFILE%

rem Shutdown servers
for /L %%i in (1,1,3) do (
    if defined pc%%i (
        call :ShutdownServer %%pc%%i%%
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
@START "" "%PSSHUTDOWN%" \\%server%.%DOMAIN% -u %DOMAIN%\%USERNAME% -p %PASSWORD% -s -t 0 -c -f
if %ERRORLEVEL% EQU 0 (
    echo Shutdown command sent successfully to %server% >> %LOGFILE%
) else (
    echo Failed to send shutdown command to %server%. Error code: %ERRORLEVEL% >> %LOGFILE%
)
exit /b