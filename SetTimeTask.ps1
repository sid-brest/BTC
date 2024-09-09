# Function to get computers
function Get-ComputerList {
    $filePath = "C:\Users\107\Documents\computers.txt"
    if (Test-Path $filePath) {
        return Get-Content -Path $filePath
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

# Function to create a time synchronization script on a remote computer
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
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            if (-not (Test-Path "C:\Scripts")) {
                New-Item -ItemType Directory -Path "C:\Scripts"
            }
            $using:setTimeContent | Out-File -FilePath "C:\Scripts\SetTime.ps1" -Encoding utf8
        }
        Write-Host "SetTime.ps1 has been created in C:\Scripts\ on $ComputerName"
    }
    catch {
        Write-Host "Error creating SetTime.ps1 on $ComputerName':' $_"
        return $false
    }
    return $true
}

# Function to create a scheduled task for time synchronization
function Create-ScheduledTask {
    param (
        [string]$ComputerName,
        [int]$IntervalMinutes
    )

    $taskName = "TimeSync"
    $taskRun = "Powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\SetTime.ps1"

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            param($taskName, $taskRun, $IntervalMinutes)

            # Create the scheduled task action, trigger, and principal
            $action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $taskRun"
            $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
            $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

            # Register the scheduled task
            Register-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -TaskName $taskName -Force

        } -ArgumentList $taskName, $taskRun, $IntervalMinutes

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
        $scriptCreated = Create-SetTimeScript -ComputerName $computer

        if ($scriptCreated) {
            # Prompt for the interval in minutes
            $IntervalMinutes = Read-Host "Specify the interval in minutes for the time synchronization script to run on $computer"

            # Create the scheduled task
            $taskCreated = Create-ScheduledTask -ComputerName $computer -IntervalMinutes $IntervalMinutes

            if ($taskCreated) {
                Write-Host "Time synchronization task created on $computer."
            }
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}