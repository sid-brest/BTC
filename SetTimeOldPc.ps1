# SetTime.ps1
# This script synchronizes the system time with an internet time server

# Function to retrieve the current time from an internet time server
function Get-CurrentInternetTime {
    $url = "http://worldtimeapi.org/api/ip"
    try {
        # Attempt to download the time information from the server
        $response = (New-Object System.Net.WebClient).DownloadString($url)
        Write-Host "Received response: $response"
        
        # Extract the datetime value from the JSON response using regex
        if ($response -match '"datetime":"([^"]+)"') {
            return $matches[1]
        }
    }
    catch {
        # Log any errors that occur during the process
        Write-Host "Error while fetching time from the internet: $_"
    }
    return $null
}

# Retrieve the current time from the internet
$currentDateTime = Get-CurrentInternetTime

if ($currentDateTime) {
    Write-Host "Received time: $currentDateTime"
    
    # Define an array of possible date formats
    # This allows for flexibility in parsing different time formats returned by the server
    $formats = @(
        "yyyy-MM-ddTHH:mm:ss.ffffffzzz",
        "yyyy-MM-ddTHH:mm:ss.fffffffzzz",
        "yyyy-MM-ddTHH:mm:sszzz",
        "yyyy-MM-ddTHH:mm:ss.fffzzz"
    )
    
    $parsedDate = $null
    # Attempt to parse the received date string using each format
    foreach ($format in $formats) {
        try {
            $parsedDate = [datetime]::ParseExact($currentDateTime, $format, [System.Globalization.CultureInfo]::InvariantCulture)
            Write-Host "Successfully parsed date with format: $format"
            break  # Exit the loop if parsing is successful
        }
        catch {
            Write-Host "Failed to parse date with format $format"
        }
    }
    
    if ($parsedDate) {
        try {
            # Attempt to set the system time to the parsed date
            Set-Date -Date $parsedDate
            Write-Host "Time successfully synchronized: $parsedDate"
        }
        catch {
            # Log any errors that occur during the time-setting process
            Write-Host "Error while setting the time: $_"
        }
    }
    else {
        # Inform the user if none of the known formats could parse the date
        Write-Host "Failed to parse the received date with any of the known formats."
    }
}
else {
    # Inform the user if the time couldn't be retrieved from the internet
    Write-Host "Failed to retrieve current time from the internet."
}

# Display the current system time for verification
Write-Host "Current system time: $(Get-Date)"
