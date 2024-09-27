# Get the current date in the format YYYYMMDD
$currentDate = Get-Date -Format "yyyyMMdd"

# Construct the log file name
$logFileName = "vpn_$currentDate.log"

# Set the path to the log file
$logFilePath = "C:\Program Files\SoftEther VPN Server\server_log\$logFileName"

# Get the directory of the current script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set the path for the restart log file
$restartLogPath = Join-Path $scriptDir "vpn_service_restart_log.txt"

# The improved search pattern
$searchPattern = '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3} A DoS attack on the TCP Listener \(port (443|5555|992)\) has been detected\. The connecting source IP address is \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}, port number is \d+\. This connection will be forcefully disconnected now\.$'

# Function to log events
function LogEvent {
    param (
        [string]$message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $message"
    Add-Content -Path $restartLogPath -Value $logMessage
}

# Get the start time of the check
$checkStartTime = Get-Date
$checkStartTimeString = $checkStartTime.ToString("yyyy-MM-dd HH:mm:ss")

# Log the start of the check
LogEvent -message "Started checking file: $logFilePath at $checkStartTimeString"

# Check if the file exists
if (Test-Path $logFilePath) {
    # Read the content of the file
    $content = Get-Content $logFilePath

    # Initialize a counter for consecutive matching lines
    $consecutiveCount = 0
    $restartNeeded = $false

    # Loop through each line in the file
    foreach ($line in $content) {
        if ($line -match $searchPattern) {
            $consecutiveCount++
            if ($consecutiveCount -ge 100) {
                $restartNeeded = $true
                break  # Exit the loop as soon as we reach 100 consecutive matches
            }
        } else {
            $consecutiveCount = 0  # Reset the counter if a non-matching line is found
        }
    }

    # Check if we need to restart the service
    if ($restartNeeded) {
        $restartTime = Get-Date
        $restartTimeString = $restartTime.ToString("yyyy-MM-dd HH:mm:ss")
        
        Write-Output "Found 100 or more consecutive matching lines. Restarting the service..."
        
        # Restart the service
        Restart-Service -Name "SEVPNSERVER" -Force
        
        Write-Output "Service restarted successfully."
        
        # Log the restart event
        $logMessage = "Service SEVPNSERVER restarted due to DoS attack detection. " +
                      "Matching log file: $logFilePath. " +
                      "Check started at: $checkStartTimeString. " +
                      "Restart time: $restartTimeString"
        LogEvent -message $logMessage
    } else {
        $checkEndTime = Get-Date
        $checkEndTimeString = $checkEndTime.ToString("yyyy-MM-dd HH:mm:ss")
        $logMessage = "Check completed. No restart needed. " +
                      "Checked file: $logFilePath. " +
                      "Check started at: $checkStartTimeString. " +
                      "Check ended at: $checkEndTimeString"
        LogEvent -message $logMessage
        Write-Output "Less than 100 consecutive matching lines found. No action taken."
    }
} else {
    $logMessage = "Log file not found: $logFilePath. " +
                  "Check attempted at: $checkStartTimeString"
    LogEvent -message $logMessage
    Write-Output "Log file not found: $logFilePath"
}