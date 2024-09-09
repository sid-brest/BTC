# Enables PowerShell remoting on the local computer.
# -Force: Suppresses confirmation prompts.
# -SkipNetworkProfileCheck: Allows remoting on all network profiles.
Enable-PSRemoting -Force -SkipNetworkProfileCheck

# Adds a computer to the list of trusted hosts for PowerShell remoting.
# Replace "Computername" with the actual name or IP address of the remote computer.
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "Computername"