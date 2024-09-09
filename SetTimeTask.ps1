# Script to synchronize system date and time with an online source and create a scheduled task

# Define the API URL to fetch the current UTC date and time.
$apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"

# Send a GET request to the API and store the response.
$response = Invoke-RestMethod -Uri $apiUrl

# Extract the datetime field from the response.
$currentDateTime = $response.datetime

# Define the format of the date and time string.
$format = "yyyy-MM-ddTHH:mm:ss.ffffffK"

# Parse the date and time string into a DateTime object.
$parsedDate = [datetime]::ParseExact($currentDateTime, $format, $null)

# Set the system date and time to the parsed DateTime object.
Set-Date -Date $parsedDate

# Function to create a scheduled task
function Create-ScheduledTask {
    # Request user credentials
    $username = Read-Host "Enter the username for the scheduled task (domain\username)"
    $password = Read-Host "Enter the password for $username" -AsSecureString

    # Convert the secure string password to plain text
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

    # Create the scheduled task using schtasks.exe
    $taskName = "TimeSync"
    $taskRun = "Powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\SetTime.ps1"
    $schedule = "MINUTE=120"  # Run every 2 hours

    $command = "schtasks /Create /TN `"$taskName`" /TR `"$taskRun`" /SC MINUTE /MO 120 /RU `"$username`" /RP `"$plainPassword`" /RL HIGHEST /F"

    try {
        Invoke-Expression $command
        Write-Host "Scheduled task 'TimeSync' has been created successfully."
    }
    catch {
        Write-Host "Error creating scheduled task: $_"
    }
}

# Ask user if they want to create a scheduled task
$createTask = Read-Host "Do you want to create a scheduled task to run this script every 2 hours? (Y/N)"

if ($createTask -eq "Y" -or $createTask -eq "y") {
    Create-ScheduledTask
}
else {
    Write-Host "No scheduled task created. Script execution complete."
}