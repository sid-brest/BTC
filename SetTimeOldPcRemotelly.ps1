# This script synchronizes the system time with an internet time server.
# It fetches the current time from a web API, parses the response,
# and sets the system time accordingly.

# Function to retrieve the current time from an internet time server
function Get-CurrentInternetTime {
    # WorldTimeAPI endpoint that returns time based on the requester's IP
    $url = "http://worldtimeapi.org/api/ip"
    try {
        # Use Invoke-RestMethod to make a GET request and automatically parse the JSON response
        # This is more efficient than using WebClient and manual JSON parsing
        $response = Invoke-RestMethod -Uri $url -Method Get
        # Return the datetime field from the response
        return $response.datetime
    }
    catch {
        # If any error occurs (e.g., network issues, API changes), log it and return null
        Write-Host "Error fetching time from the internet: $_"
        return $null
    }
}

# Function to set the system time
# This is separated into its own function for better modularity and reusability
function Set-SystemTime {
    param ([DateTime]$newTime)
    try {
        # Attempt to set the system time
        # Note: This operation requires administrative privileges
        Set-Date -Date $newTime
        Write-Host "Time successfully synchronized: $newTime"
    }
    catch {
        # Log any errors that occur during the time-setting process
        Write-Host "Error setting the time: $_"
    }
}

# Fetch the current time from the internet
$currentDateTime = Get-CurrentInternetTime

if ($currentDateTime) {
    Write-Host "Received time: $currentDateTime"
    
    # Define an array of possible date formats
    # These formats cover various possibilities that the API might return
    # They are ordered from most specific to least specific for efficiency
    $formats = @(
        "yyyy-MM-ddTHH:mm:ss.fffffffzzz",  # Format with 7 fractional seconds
        "yyyy-MM-ddTHH:mm:ss.ffffffzzz",   # Format with 6 fractional seconds
        "yyyy-MM-ddTHH:mm:ss.fffzzz",      # Format with 3 fractional seconds
        "yyyy-MM-ddTHH:mm:sszzz"           # Format without fractional seconds
    )
    
    $parsedDate = $null
    # Attempt to parse the received date string using each format
    foreach ($format in $formats) {
        # Use TryParseExact instead of ParseExact to avoid exceptions
        # This method returns a boolean indicating success and outputs the result to $parsedDate
        if ([DateTime]::TryParseExact($currentDateTime, $format, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::None, [ref]$parsedDate)) {
            Write-Host "Successfully parsed date with format: $format"
            break  # Exit the loop if parsing is successful
        }
    }
    
    if ($parsedDate) {
        # If parsing was successful, attempt to set the system time
        Set-SystemTime -newTime $parsedDate
    }
    else {
        # If parsing failed for all formats, inform the user
        Write-Host "Failed to parse the received date with any of the known formats."
    }
}
else {
    # Inform the user if the time couldn't be retrieved from the internet
    Write-Host "Failed to retrieve current time from the internet."
}

# Display the current system time for verification
# This allows the user to confirm whether the time was successfully updated
Write-Host "Current system time: $(Get-Date)"
