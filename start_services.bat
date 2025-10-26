@echo off
echo Starting ZPredict Services...

:: Start Django development server
start "Django Server" cmd /k "cd /d \"c:\Sanuthi BSC\Sem 3\Zpredict\zpredict\" && python manage.py runserver"

:: Wait 3 seconds for Django to start
timeout /t 3 /nobreak >nul

:: Start Celery worker with auto-restart
start "Celery Worker" cmd /k "cd /d \"c:\Sanuthi BSC\Sem 3\Zpredict\" && start_celery.bat"

:: Wait 2 seconds
timeout /t 2 /nobreak >nul

:: Start upload monitor daemon
start "Upload Monitor" cmd /k "cd /d \"c:\Sanuthi BSC\Sem 3\Zpredict\zpredict\" && python manage.py monitor_uploads --daemon --interval 300"

echo All services started!
echo - Django Server: http://localhost:8000
echo - Celery Worker: Running with auto-restart
echo - Upload Monitor: Checking every 5 minutes
echo.
echo Press any key to close this window...
pause >nul
