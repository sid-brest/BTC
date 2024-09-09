# Script to synchronize system date and time with an online source and create a scheduled task

# Function to create SetTime.ps1 file
function Create-SetTimeScript {
    $setTimeContent = @"
# Script to synchronize system date and time with an online source
# Define the API URL to fetch the current UTC date and time.
`$apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"

# Send a GET request to the API and store the response.
`$response = Invoke-RestMethod -Uri `$apiUrl

# Extract the datetime field from the response.
`$currentDateTime = `$response.datetime

# Define the format of the date and time string.
`$format = "yyyy-MM-ddTHH:mm:ss.ffffffK"

# Parse the date and time string into a DateTime object.
`$parsedDate = [datetime]::ParseExact(`$currentDateTime, `$format, `$null)

# Set the system date and time to the parsed DateTime object.
Set-Date -Date `$parsedDate
"@

    # Create the Scripts folder if it doesn't exist
    if (-not (Test-Path "C:\Scripts")) {
        New-Item -ItemType Directory -Path "C:\Scripts"
    }

    # Create the SetTime.ps1 file
    $setTimeContent | Out-File -FilePath "C:\Scripts\SetTime.ps1" -Encoding utf8
    Write-Host "SetTime.ps1 has been created in C:\Scripts\"
}

# Function to create a scheduled task
function Create-ScheduledTask {
    param (
        [string]$ComputerName = $env:COMPUTERNAME,
        [int]$IntervalMinutes
    )

    # Request user credentials
    $username = Read-Host "Enter the username for the scheduled task (domain\username)"
    $password = Read-Host "Enter the password for $username" -AsSecureString

    # Convert the secure string password to plain text
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

    # Create the scheduled task using schtasks.exe
    $taskName = "TimeSync"
    $taskRun = "Powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\SetTime.ps1"

    $command = "schtasks /Create /S $ComputerName /TN `"$taskName`" /TR `"$taskRun`" /SC MINUTE /MO $IntervalMinutes /RU `"$username`" /RP `"$plainPassword`" /RL HIGHEST /F"

    try {
        Invoke-Expression $command
        Write-Host "Scheduled task 'TimeSync' has been created successfully on $ComputerName."
    }
    catch {
        Write-Host "Error creating scheduled task on $ComputerName':' $_"
    }
}

# Main script execution
$createSetTimeScript = Read-Host "Do you want to create SetTime.ps1 in C:\Scripts? (Y/N)"
if ($createSetTimeScript -eq "Y" -or $createSetTimeScript -eq "y") {
    Create-SetTimeScript
}

$createTask = Read-Host "Do you want to create a scheduled task to run this script? (Y/N)"
if ($createTask -eq "Y" -or $createTask -eq "y") {
    $intervalMinutes = Read-Host "Enter the interval in minutes at which the task should run (e.g., 120 for every 2 hours)"
    $intervalMinutes = [int]$intervalMinutes

    $remoteExecution = Read-Host "Do you want to run this on a remote PC? (Y/N)"
    if ($remoteExecution -eq "Y" -or $remoteExecution -eq "y") {
        $remotePCName = Read-Host "Enter the name of the remote PC"
        Create-ScheduledTask -ComputerName $remotePCName -IntervalMinutes $intervalMinutes
    }
    else {
        Create-ScheduledTask -IntervalMinutes $intervalMinutes
    }
}
else {
    Write-Host "No scheduled task created. Script execution complete."
}