# Fetch current date and time from an online source
$apiUrl = "http://worldtimeapi.org/api/timezone/etc/utc"
$response = Invoke-RestMethod -Uri $apiUrl
$currentDateTime = $response.datetime

# Parse the fetched date and time
$format = "yyyy-MM-ddTHH:mm:ss.ffffffK"
$parsedDate = [datetime]::ParseExact($currentDateTime, $format, $null)

# Set the system date and time
Set-Date -Date $parsedDate