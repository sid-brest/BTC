$scriptBlock = {
    # Set the output encoding to UTF-8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    # Run the winget command
    $output = winget upgrade --all --include-unknown --accept-source-agreements --accept-package-agreements

    # Return the output
    $output
}

# Invoke the command on the remote computer and capture the output
$result = Invoke-Command -ComputerName "computername123" -ScriptBlock $scriptBlock

# Display the output
$result