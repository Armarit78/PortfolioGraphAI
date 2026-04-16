$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Banner {
    param(
        [string]$Text,
        [ConsoleColor]$Color = [ConsoleColor]::Yellow
    )

    $line = ("-" * 42)
    Write-Host $line -ForegroundColor $Color
    Write-Host ("  {0}" -f $Text) -ForegroundColor $Color
    Write-Host $line -ForegroundColor $Color
}

function Resolve-PythonTools {
    $pythonPath = $null
    $uvicornPath = $null

    $venvCandidates = @()
    if ($env:VIRTUAL_ENV) {
        $venvCandidates += $env:VIRTUAL_ENV
    }

    $venvCandidates += @(
        (Join-Path $RootDir ".venv"),
        (Join-Path $RootDir "venv"),
        (Join-Path $RootDir "backend\.venv"),
        (Join-Path $RootDir "backend\venv")
    )

    foreach ($venvPath in $venvCandidates | Select-Object -Unique) {
        $candidatePython = Join-Path $venvPath "Scripts\python.exe"
        $candidateUvicorn = Join-Path $venvPath "Scripts\uvicorn.exe"
        if (Test-Path $candidatePython) {
            $pythonPath = $candidatePython
            if (Test-Path $candidateUvicorn) {
                $uvicornPath = $candidateUvicorn
            }
            Write-Host ("Virtual environment detected: {0}" -f $venvPath) -ForegroundColor Green
            break
        }
    }

    if (-not $pythonPath) {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $pythonPath = $pythonCommand.Source
        }
    }

    if (-not $uvicornPath) {
        $uvicornCommand = Get-Command uvicorn -ErrorAction SilentlyContinue
        if ($uvicornCommand) {
            $uvicornPath = $uvicornCommand.Source
        }
    }

    [pscustomobject]@{
        Python  = $pythonPath
        Uvicorn = $uvicornPath
    }
}

function Start-PrefixedProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,

        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [ConsoleColor]$Color
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $escapedArguments = foreach ($argument in $Arguments) {
        if ($null -eq $argument) {
            '""'
        }
        elseif ($argument -match '[\s"]') {
            '"' + ($argument -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
        }
        else {
            $argument
        }
    }
    $psi.Arguments = ($escapedArguments -join ' ')

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    $process.EnableRaisingEvents = $true

    if (-not $process.Start()) {
        throw ("Unable to start process: {0}" -f $FilePath)
    }

    $messageData = @{
        Label = $Label
        Color = $Color
    }

    $stdoutEvent = Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -MessageData $messageData -Action {
        if ($EventArgs.Data) {
            Write-Host ("{0} {1}" -f $Event.MessageData.Label, $EventArgs.Data) -ForegroundColor $Event.MessageData.Color
        }
    }

    $stderrEvent = Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -MessageData $messageData -Action {
        if ($EventArgs.Data) {
            Write-Host ("{0} {1}" -f $Event.MessageData.Label, $EventArgs.Data) -ForegroundColor $Event.MessageData.Color
        }
    }

    $process.BeginOutputReadLine()
    $process.BeginErrorReadLine()

    [pscustomobject]@{
        Process = $process
        Events  = @($stdoutEvent, $stderrEvent)
    }
}

function Stop-RunningProcess {
    param(
        [Parameter(Mandatory = $false)]
        $ManagedProcess
    )

    if (-not $ManagedProcess) {
        return
    }

    $process = $ManagedProcess.Process
    if ($process -and -not $process.HasExited) {
        try {
            $process.Kill($true)
            $process.WaitForExit(5000) | Out-Null
        }
        catch {
        }
    }

    foreach ($eventSubscription in ($ManagedProcess.Events | Where-Object { $_ })) {
        try {
            Unregister-Event -SourceIdentifier $eventSubscription.Name -ErrorAction SilentlyContinue
        }
        catch {
        }
        $eventSubscription | Remove-Job -Force -ErrorAction SilentlyContinue
    }
}

$tools = Resolve-PythonTools
$pythonPath = $tools.Python
$uvicornPath = $tools.Uvicorn

if (-not $pythonPath -and -not $uvicornPath) {
    throw "Python or uvicorn not found. Activate a virtual environment or install them first."
}

Write-Banner "Starting project"

$backend = $null
$frontend = $null

try {
    if ($uvicornPath) {
        $backendCommand = $uvicornPath
        $backendArgs = @("backend.appRouter:app", "--reload")
    }
    else {
        $backendCommand = $pythonPath
        $backendArgs = @("-m", "uvicorn", "backend.appRouter:app", "--reload")
    }

    $backend = Start-PrefixedProcess `
        -FilePath $backendCommand `
        -Arguments $backendArgs `
        -WorkingDirectory $RootDir `
        -Label "[BACKEND ]" `
        -Color Blue

    $frontendDir = Join-Path $RootDir "frontend"
    if (-not (Test-Path $frontendDir)) {
        throw "Directory 'frontend' not found."
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCommand) {
        $npmCommand = Get-Command npm -ErrorAction SilentlyContinue
    }
    if (-not $npmCommand) {
        throw "npm not found. Install Node.js or add npm to PATH."
    }

    Write-Host "Starting frontend (npm run dev)..." -ForegroundColor Green

    $frontend = Start-PrefixedProcess `
        -FilePath $npmCommand.Source `
        -Arguments @("run", "dev") `
        -WorkingDirectory $frontendDir `
        -Label "[FRONTEND]" `
        -Color Green

    Write-Host ("Backend  PID : {0}" -f $backend.Process.Id) -ForegroundColor Green
    Write-Host ("Frontend PID : {0}" -f $frontend.Process.Id) -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop everything." -ForegroundColor Yellow

    while (-not $backend.Process.HasExited -and -not $frontend.Process.HasExited) {
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Red
    Stop-RunningProcess -ManagedProcess $backend
    Stop-RunningProcess -ManagedProcess $frontend
    Write-Host "Services stopped." -ForegroundColor Red
}
