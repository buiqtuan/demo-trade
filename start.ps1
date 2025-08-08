# PowerShell script to start services with options
param(
    [Parameter(Position=0)]
    [string]$Service = "0"
)

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Add shared_models to Python path
$env:PYTHONPATH = "$ScriptDir;$env:PYTHONPATH"

# Display menu if no parameter provided
if ($Service -eq "" -or $Service -eq $null) {
    Write-Host ""
    Write-Host "=== Trading Simulator Service Launcher ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Choose which service(s) to start:" -ForegroundColor Yellow
    Write-Host "  0 - All services (Backend + Market Data Aggregator)" -ForegroundColor White
    Write-Host "  1 - Backend only (Recommended for development)" -ForegroundColor White
    Write-Host "  2 - Market Data Aggregator only" -ForegroundColor White
    Write-Host ""
    $Service = Read-Host "Enter your choice [0-2]"
}

Write-Host ""
Write-Host "=== Starting Services ===" -ForegroundColor Cyan

$BackendJob = $null
$MarketDataJob = $null

switch ($Service) {
    "1" {
        Write-Host "Starting Backend service only..." -ForegroundColor Green
        
        $BackendJob = Start-Job -ScriptBlock {
            param($dir, $pythonPath)
            $env:PYTHONPATH = $pythonPath
            Set-Location "$dir\backend"
            python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
        } -ArgumentList $ScriptDir, $env:PYTHONPATH
        
        Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
    }
    "2" {
        Write-Host "Starting Market Data Aggregator service only..." -ForegroundColor Green
        
        $MarketDataJob = Start-Job -ScriptBlock {
            param($dir, $pythonPath)
            $env:PYTHONPATH = $pythonPath
            Set-Location "$dir\market_data_aggregator"
            python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
        } -ArgumentList $ScriptDir, $env:PYTHONPATH
        
        Write-Host "Market Data Aggregator: http://localhost:8001" -ForegroundColor Cyan
    }
    "0" {
        Write-Host "Starting all services..." -ForegroundColor Green
        
        # Start Backend first
        $BackendJob = Start-Job -ScriptBlock {
            param($dir, $pythonPath)
            $env:PYTHONPATH = $pythonPath
            Set-Location "$dir\backend"
            python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
        } -ArgumentList $ScriptDir, $env:PYTHONPATH
        
        # Wait a moment for backend to start
        Start-Sleep -Seconds 3
        
        # Start Market Data Aggregator
        $MarketDataJob = Start-Job -ScriptBlock {
            param($dir, $pythonPath)
            $env:PYTHONPATH = $pythonPath
            Set-Location "$dir\market_data_aggregator"
            python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
        } -ArgumentList $ScriptDir, $env:PYTHONPATH
        
        Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "Market Data Aggregator: http://localhost:8001" -ForegroundColor Cyan
    }
    default {
        Write-Host "Invalid choice. Please run the script again and choose 0, 1, or 2." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Wait for services to start
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Checking service status..." -ForegroundColor Blue
Write-Host ""

# Check Backend service
if ($BackendJob -ne $null) {
    if ($BackendJob.State -eq "Running") {
        Write-Host "✓ Backend service is running" -ForegroundColor Green
        
        # Test backend health
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
            Write-Host "✓ Backend health check passed" -ForegroundColor Green
            Write-Host "  Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
        } catch {
            Write-Host "⚠ Backend started but health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Backend service failed to start" -ForegroundColor Red
        if ($BackendJob.State -eq "Failed") {
            Write-Host "Backend error output:" -ForegroundColor Red
            Receive-Job $BackendJob -ErrorAction SilentlyContinue | Write-Host
        }
    }
}

# Check Market Data Aggregator service
if ($MarketDataJob -ne $null) {
    if ($MarketDataJob.State -eq "Running") {
        Write-Host "✓ Market Data Aggregator service is running" -ForegroundColor Green
        
        # Test market data aggregator health
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get -TimeoutSec 10
            Write-Host "✓ Market Data Aggregator health check passed" -ForegroundColor Green
            Write-Host "  Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
        } catch {
            Write-Host "⚠ Market Data Aggregator started but health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Market Data Aggregator service failed to start" -ForegroundColor Red
        if ($MarketDataJob.State -eq "Failed") {
            Write-Host "Market Data Aggregator error output:" -ForegroundColor Red
            Receive-Job $MarketDataJob -ErrorAction SilentlyContinue | Write-Host
        }
    }
}

Write-Host ""
if ($Service -eq "1") {
    Write-Host "Note: Only Backend is running. The app will use mock data for stock prices." -ForegroundColor Yellow
} elseif ($Service -eq "2") {
    Write-Host "Note: Only Market Data Aggregator is running. You need the Backend for the full app." -ForegroundColor Yellow
} else {
    Write-Host "All requested services are running." -ForegroundColor Green
}

Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Red

# Handle Ctrl+C and monitor services
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if any job failed
        $anyFailed = $false
        
        if ($BackendJob -ne $null -and ($BackendJob.State -eq "Failed" -or $BackendJob.State -eq "Completed")) {
            Write-Host "Backend service stopped or failed." -ForegroundColor Red
            if ($BackendJob.State -eq "Failed") {
                Write-Host "Backend error output:" -ForegroundColor Red
                Receive-Job $BackendJob -ErrorAction SilentlyContinue | Write-Host
            }
            $anyFailed = $true
        }
        
        if ($MarketDataJob -ne $null -and ($MarketDataJob.State -eq "Failed" -or $MarketDataJob.State -eq "Completed")) {
            Write-Host "Market Data Aggregator service stopped or failed." -ForegroundColor Red
            if ($MarketDataJob.State -eq "Failed") {
                Write-Host "Market Data Aggregator error output:" -ForegroundColor Red
                Receive-Job $MarketDataJob -ErrorAction SilentlyContinue | Write-Host
            }
            $anyFailed = $true
        }
        
        if ($anyFailed) {
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    
    # Stop jobs
    if ($BackendJob -ne $null) {
        Stop-Job $BackendJob -ErrorAction SilentlyContinue
        Remove-Job $BackendJob -ErrorAction SilentlyContinue
    }
    
    if ($MarketDataJob -ne $null) {
        Stop-Job $MarketDataJob -ErrorAction SilentlyContinue
        Remove-Job $MarketDataJob -ErrorAction SilentlyContinue
    }
    
    # Kill any remaining uvicorn processes
    $uvicornProcesses = Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*"}
    if ($uvicornProcesses) {
        Write-Host "Stopping remaining uvicorn processes..." -ForegroundColor Yellow
        $uvicornProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "All services stopped." -ForegroundColor Green
}
