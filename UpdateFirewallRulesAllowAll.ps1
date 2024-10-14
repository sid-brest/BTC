
# Function to get computers
function Get-ComputerList {
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    $defaultFilePath = Join-Path $scriptPath "computers.txt"

    if (Test-Path $defaultFilePath) {
        $filePath = $defaultFilePath
    } else {
        $filePath = Read-Host "Enter the path to computers.txt file (or press Enter to skip)"
        if ([string]::IsNullOrWhiteSpace($filePath)) {
            $filePath = $null
        } elseif (-not (Test-Path $filePath)) {
            Write-Host "File not found. Proceeding with manual input."
            $filePath = $null
        }
    }

    if ($filePath) {
        # Read the file and filter out lines starting with '#'
        return Get-Content -Path $filePath | Where-Object { $_ -notmatch '^\s*#' -and $_ -ne '' }
    } else {
        $computers = @()
        $count = 1
        do {
            $computer = Read-Host "Enter a computer name $count (or press Enter to finish)"
            if ($computer -ne "") {
                $computers += $computer
                $count++
            }
        } while ($computer -ne "")
        return $computers
    }
}

# Get the list of computers
$computers = Get-ComputerList

# Prompt for credentials once
$cred = Get-Credential

function Enable-RemoteAccess {
    param (
        [string]$ComputerName
    )

    try {
        # Check current WinRM status
        $winrmStatus = Invoke-Command -ComputerName $ComputerName -ScriptBlock { Get-Service WinRM } -ErrorAction Stop

        if ($winrmStatus.Status -ne 'Running') {
            Write-Host "WinRM service is not running on $ComputerName. Attempting to start..."
            Invoke-Command -ComputerName $ComputerName -ScriptBlock { 
                Start-Service WinRM
                Set-Service WinRM -StartupType Automatic
            }
        }

        # Configure WinRM to accept remote connections
        Invoke-Command -ComputerName $ComputerName -ScriptBlock {
            Enable-PSRemoting -Force
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force            
        }

        Write-Host "Remote access has been successfully enabled on $ComputerName"
        return $true
    }
    catch {
        Write-Host "Failed to enable remote access on $ComputerName. Error: $_"
        return $false
    }
}

function Add-FirewallRules {
    param (
        [string]$ComputerName
    )

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            # Add inbound rule
            New-NetFirewallRule -DisplayName "Allow All Inbound 192.168.1.0/24" `
                                -Direction Inbound `
                                -LocalAddress 192.168.1.0/24 `
                                -RemoteAddress 192.168.1.0/24 `
                                -Action Allow

            # Add outbound rule
            New-NetFirewallRule -DisplayName "Allow All Outbound 192.168.1.0/24" `
                                -Direction Outbound `
                                -LocalAddress 192.168.1.0/24 `
                                -RemoteAddress 192.168.1.0/24 `
                                -Action Allow

            Write-Host "Firewall rules have been added successfully on $env:COMPUTERNAME"
        }
        return $true
    }
    catch {
        Write-Host "Error adding firewall rules on $ComputerName":" $_"
        return $false
    }
}

# Main script execution
foreach ($computer in $computers) {
    Write-Host "Connecting to $computer..."

    # Check if the computer is accessible
    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        # Try to enable remote access if needed
        $remoteAccessEnabled = Enable-RemoteAccess -ComputerName $computer

        if ($remoteAccessEnabled) {
            # Add firewall rules
            $rulesAdded = Add-FirewallRules -ComputerName $computer

            if ($rulesAdded) {
                Write-Host "Firewall rules added successfully on $computer."
            } else {
                Write-Host "Failed to add firewall rules on $computer."
            }
        } else {
            Write-Host "Unable to enable remote access on $computer. Skipping..."
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}