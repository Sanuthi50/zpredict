@echo off
echo Fixing Windows Network Configuration for API Connectivity...
echo.

echo 1. Flushing DNS cache...
ipconfig /flushdns

echo 2. Resetting TCP/IP stack...
netsh winsock reset
netsh int ip reset

echo 3. Clearing proxy settings...
netsh winhttp reset proxy

echo 4. Restarting network services...
net stop dnscache
net start dnscache

echo 5. Checking Windows Defender firewall...
netsh advfirewall firewall add rule name="Allow Python API Calls" dir=out action=allow program="%LOCALAPPDATA%\Programs\Python\Python*\python.exe" enable=yes

echo.
echo Network configuration completed!
echo Please restart your computer for changes to take effect.
echo.
pause
