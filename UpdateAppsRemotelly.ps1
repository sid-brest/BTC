# Script to upgrade all installed packages on a remote computer using winget

$scriptBlock = {
    # Set the output encoding to UTF-8 to ensure proper display of characters
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    # Run the winget command to upgrade all installed packages, including unknown ones,
    # and automatically accept source and package agreements
    $output = winget upgrade --all --include-unknown --accept-source-agreements --accept-package-agreements

    # Return the output of the winget command
    $output
}

# Invoke the script block on the specified remote computer and capture the output
$result = Invoke-Command -ComputerName "computername123" -ScriptBlock $scriptBlock

# Display the captured output
$result
