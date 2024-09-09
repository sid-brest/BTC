# Script to synchronize system date and time with an online source

$scriptBlock = {
    # Define the URL of the API that provides the current date and time in UTC
    $apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"
    
    # Fetch the current date and time from the API
    $response = Invoke-RestMethod -Uri $apiUrl
    
    # Extract the datetime value from the API response
    $currentDateTime = $response.datetime

    # Define the format of the datetime string received from the API
    $format = "yyyy-MM-ddTHH:mm:ss.ffffffK"
    
    # Parse the datetime string into a DateTime object
    $parsedDate = [datetime]::ParseExact($currentDateTime, $format, $null)

    # Set the system date and time to the parsed DateTime object
    Set-Date -Date $parsedDate
}

# Execute the script block on the specified remote computer
Invoke-Command -ComputerName "Computername" -ScriptBlock $scriptBlock
