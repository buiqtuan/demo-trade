# PowerShell script to stop services

Write-Host "Stopping all services..." -ForegroundColor Yellow

# Kill uvicorn processes
$processes = Get-Process | Where-Object {
    $_.ProcessName -eq "python" -and 
    $_.CommandLine -like "*uvicorn*"
}

if ($processes) {
    $processes | Stop-Process -Force
    Write-Host "Stopped $($processes.Count) uvicorn process(es)." -ForegroundColor Green
} else {
    Write-Host "No uvicorn processes found." -ForegroundColor Gray
}

# Alternative: Kill by port
try {
    $port8000 = netstat -ano | findstr ":8000"
    $port8001 = netstat -ano | findstr ":8001"
    
    if ($port8000 -or $port8001) {
        Write-Host "Killing processes on ports 8000 and 8001..." -ForegroundColor Yellow
        
        # Extract PIDs and kill them
        if ($port8000) {
            $pid8000 = ($port8000 -split '\s+')[-1]
            Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
        }
        
        if ($port8001) {
            $pid8001 = ($port8001 -split '\s+')[-1]
            Stop-Process -Id $pid8001 -Force -ErrorAction SilentlyContinue
        }
    }
} catch {
    # Ignore errors
}

Write-Host "Services stopped." -ForegroundColor Green
