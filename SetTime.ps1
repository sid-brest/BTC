# Script to synchronize system date and time with an online source
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
