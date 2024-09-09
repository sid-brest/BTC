function Create-SetTimeScript {
    param (
        [string]$ComputerName
    )

    $setTimeContent = @"
# Script to synchronize system date and time with an online source
`$apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"
`$response = Invoke-RestMethod -Uri `$apiUrl
`$currentDateTime = `$response.datetime
`$format = "yyyy-MM-ddTHH:mm:ss.ffffffK"
`$parsedDate = [datetime]::ParseExact(`$currentDateTime, `$format, `$null)
Set-Date -Date `$parsedDate
"@

    try {
        Invoke-Command -ComputerName $ComputerName -ScriptBlock {
            if (-not (Test-Path "C:\Scripts")) {
                New-Item -ItemType Directory -Path "C:\Scripts"
            }
            $using:setTimeContent | Out-File -FilePath "C:\Scripts\SetTime.ps1" -Encoding utf8
        }
        Write-Host "SetTime.ps1 has been created in C:\Scripts\ on $ComputerName"
    }
    catch {
        Write-Host "Error creating SetTime.ps1 on $ComputerName':' $_"
        exit
    }
}

function Create-ScheduledTask {
    param (
        [string]$ComputerName,
        [int]$IntervalMinutes
    )

    $taskName = "TimeSync"
    $taskRun = "Powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\SetTime.ps1"

    $command = if ($ComputerName -eq "localhost") {
        "schtasks /Create /TN `"$taskName`" /TR `"$taskRun`" /SC MINUTE /MO $IntervalMinutes /RL HIGHEST /F"
    } else {
        "schtasks /Create /S $ComputerName /TN `"$taskName`" /TR `"$taskRun`" /SC MINUTE /MO $IntervalMinutes /RL HIGHEST /F"
    }

    try {
        Invoke-Expression $command
        Write-Host "Scheduled task 'TimeSync' has been created successfully on $ComputerName."
    }
    catch {
        Write-Host "Error creating scheduled task on $ComputerName':' $_"
        exit
    }
}

function Test-ScheduledTask {
    param (
        [string]$ComputerName
    )

    $command = if ($ComputerName -eq "localhost") {
        "schtasks /Run /TN `"TimeSync`""
    } else {
        "schtasks /Run /S $ComputerName /TN `"TimeSync`""
    }

    try {
        Invoke-Expression $command
        Write-Host "Scheduled task 'TimeSync' has been run successfully on $ComputerName."
        
        Start-Sleep -Seconds 10

        $result = schtasks /Query /S $ComputerName /TN "TimeSync" /FO LIST /V | Select-String "Last Result"
        if ($result -match "0x0") {
            Write-Host "The task completed successfully."
        }
        else {
            Write-Host "The task did not complete successfully. Last result: $result"
        }
    }
    catch {
        Write-Host "Error running scheduled task on $ComputerName':' $_"
    }
}

# Main script execution
$ComputerName = Read-Host "1. Specify IP address or computer name"

if (-not (Test-Connection -ComputerName $ComputerName -Count 1 -Quiet)) {
    Write-Host "Error: Cannot reach $ComputerName. Please check the computer name or IP address and ensure it's accessible."
    exit
}

$IntervalMinutes = Read-Host "2. Specify the interval in minutes for the time synchronization script to run"

Write-Host "`nStarting script execution..."

Write-Host "`nStep 1: Creating C:\Scripts folder and SetTime.ps1 on remote computer"
Create-SetTimeScript -ComputerName $ComputerName

Write-Host "`nStep 2: Creating scheduled task on remote computer"
Create-ScheduledTask -ComputerName $ComputerName -IntervalMinutes $IntervalMinutes

Write-Host "`nStep 3: Testing the newly created task"
Test-ScheduledTask -ComputerName $ComputerName

Write-Host "`nScript execution completed."