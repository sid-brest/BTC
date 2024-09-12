﻿# Function to get computers
function Get-ComputerList {
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    $defaultFilePath = Join-Path $scriptPath "computers.txt"

    if (Test-Path $defaultFilePath) {
        $filePath = $defaultFilePath
    } else {
        $filePath = Read-Host "Enter the path to computers.txt file (or press Enter to skip)"
        if ([string]::IsNullOrWhiteSpace($filePath)) {
            $filePath = $null
        } elseif (-not (Test-Path $filePath)) {
            Write-Host "File not found. Proceeding with manual input."
            $filePath = $null
        }
    }

    if ($filePath) {
        # Read the file and filter out lines starting with '#'
        return Get-Content -Path $filePath | Where-Object { $_ -notmatch '^\s*#' -and $_ -ne '' }
    } else {
        $computers = @()
        $count = 1
        do {
            $computer = Read-Host "Enter a computer name $count (or press Enter to finish)"
            if ($computer -ne "") {
                $computers += $computer
                $count++
            }
        } while ($computer -ne "")
        return $computers
    }
}

# Get the list of computers
$computers = Get-ComputerList

# Prompt for credentials once
$cred = Get-Credential

# Prompt for the interval in minutes once
$IntervalMinutes = Read-Host "Specify the interval in minutes for the time synchronization script to run on all computers"

# Function to create a time synchronization script on a remote computer
function Update-SetTimeScript {
    param (
        [string]$ComputerName
    )

    $setTimeContent = @"
# Script to synchronize system date and time with an online source
`$apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"
`$webClient = New-Object System.Net.WebClient
`$response = `$webClient.DownloadString(`$apiUrl)
`$currentDateTime = (`$response | ConvertFrom-Json).datetime
`$format = "yyyy-MM-ddTHH:mm:ss.ffffffK"
`$parsedDate = [datetime]::ParseExact(`$currentDateTime, `$format, `$null)
Set-Date -Date `$parsedDate
"@

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            if (-not (Test-Path "c:\Windows\Setup\Scripts")) {
                New-Item -ItemType Directory -Path "c:\Windows\Setup\Scripts"
            }
            $using:setTimeContent | Out-File -FilePath "c:\Windows\Setup\Scripts\SetTime.ps1" -Encoding utf8
        }
        Write-Host "SetTime.ps1 has been created in c:\Windows\Setup\Scripts\ on $ComputerName"
    }
    catch {
        Write-Host "Error creating SetTime.ps1 on $ComputerName':' $_"
        return $false
    }
    return $true
}

# Function to create a scheduled task for time synchronization
function Update-ScheduledTask {
    param (
        [string]$ComputerName,
        [int]$IntervalMinutes
    )

    $taskName = "TimeSync"
    $taskRun = "Powershell.exe -NoProfile -ExecutionPolicy Bypass -File c:\Windows\Setup\Scripts\SetTime.ps1"

    try {
        $command = "schtasks.exe /Create /TN `"$taskName`" /TR `"$taskRun`" /SC MINUTE /MO $IntervalMinutes /RU `"NT AUTHORITY\SYSTEM`" /RL HIGHEST /F"
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            param($command)
            $output = cmd /c $command 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create scheduled task. Error: $output"
            }
        } -ArgumentList $command

        Write-Host "Scheduled task 'TimeSync' has been created successfully on $ComputerName."
        return $true
    }
    catch {
        Write-Host "Error creating scheduled task on $ComputerName':' $_"
        return $false
    }
}

# Main script execution
foreach ($computer in $computers) {
    Write-Host "Connecting to $computer..."

    # Check if the computer is accessible
    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        # Create the time synchronization script
        $scriptCreated = Update-SetTimeScript -ComputerName $computer

        if ($scriptCreated) {
            # Create the scheduled task
            $taskCreated = Update-ScheduledTask -ComputerName $computer -IntervalMinutes $IntervalMinutes

            if ($taskCreated) {
                Write-Host "Time synchronization task created on $computer."
            }
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}