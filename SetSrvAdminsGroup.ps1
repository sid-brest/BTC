<#
.SYNOPSIS
This PowerShell script automates the process of adding the 'SrvAdmins' group to the local Administrators group on multiple remote computers.
It also ensures that WinRM (Windows Remote Management) is enabled on these computers to facilitate remote administration.

.DESCRIPTION
The script performs the following main tasks:
1. Retrieves a list of target computers from a file or manual input.
2. Enables WinRM on each computer if it's not already running.
3. Adds the 'SrvAdmins' domain group to the local Administrators group on each computer.
4. Logs all actions, errors, and successes to a file named after the script (without the .ps1 extension).

.NOTES
Ensure you have the necessary permissions to modify remote computers and add groups to the Administrators group.
#>

# Initialize logging
$scriptName = [System.IO.Path]::GetFileNameWithoutExtension($MyInvocation.MyCommand.Name)
$logFile = Join-Path $PSScriptRoot "$scriptName.log"

function Write-Log {
    param($message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $message"
    Add-Content -Path $logFile -Value $logMessage
    Write-Host $logMessage
}

# Function to get computers
function Get-ComputerList {
    # Determine the script's directory
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    
    # Set the default path for the servers.txt file
    $defaultFilePath = Join-Path $scriptPath "servers.txt"

    # Check if the default file exists, otherwise prompt for a file path
    if (Test-Path $defaultFilePath) {
        $filePath = $defaultFilePath
    } else {
        $filePath = Read-Host "Enter the path to servers.txt file (or press Enter to skip)"
        if ([string]::IsNullOrWhiteSpace($filePath)) {
            $filePath = $null
        } elseif (-not (Test-Path $filePath)) {
            Write-Log "File not found. Proceeding with manual input."
            $filePath = $null
        }
    }

    # If a file path is provided, read the computers from the file
    if ($filePath) {
        # Read the file and filter out comment lines and empty lines
        return Get-Content -Path $filePath | Where-Object { $_ -notmatch '^\s*#' -and $_ -ne '' }
    } else {
        # If no file is provided, prompt for manual input of computer names
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

# Prompt for credentials once to use for remote operations
$cred = Get-Credential

function Enable-RemoteAccess {
    param (
        [string]$ComputerName
    )

    try {
        # Check the current status of the WinRM service
        $winrmStatus = Invoke-Command -ComputerName $ComputerName -ScriptBlock { Get-Service WinRM } -ErrorAction Stop

        # If WinRM is not running, start it and set it to start automatically
        if ($winrmStatus.Status -ne 'Running') {
            Write-Log "WinRM service is not running on $ComputerName. Attempting to start..."
            Invoke-Command -ComputerName $ComputerName -ScriptBlock { 
                Start-Service WinRM
                Set-Service WinRM -StartupType Automatic
            }
        }

        # Configure WinRM to accept remote connections
        Invoke-Command -ComputerName $ComputerName -ScriptBlock {
            # Enable PowerShell remoting
            Enable-PSRemoting -Force
            # Allow all hosts in the TrustedHosts list (consider security implications)
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force            
        }

        Write-Log "Remote access has been successfully enabled on $ComputerName"
        return $true
    }
    catch {
        Write-Log "Failed to enable remote access on $ComputerName. Error: $_"
        return $false
    }
}

function Add-SrvAdminsToAdministratorsGroup {
    param (
        [string]$ComputerName
    )

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            # Get the domain name of the current computer
            $domain = (Get-WmiObject Win32_ComputerSystem).Domain

            # Determine the Administrators group name based on the system language
            $adminGroupName = (Get-WmiObject -Class Win32_Group -Filter "SID='S-1-5-32-544'").Name

            # Get the Administrators group
            $group = [ADSI]"WinNT://./$adminGroupName,group"
            
            # Check if SrvAdmins is already in the Administrators group
            $members = @($group.Invoke("Members"))
            $SrvAdminsExists = $members | ForEach-Object { $_.GetType().InvokeMember("Name", 'GetProperty', $null, $_, $null) } | Where-Object { $_ -eq "SrvAdmins" }

            if ($SrvAdminsExists) {
                Write-Host "SrvAdmins is already a member of the $adminGroupName group on $env:COMPUTERNAME"
            } else {
                # Add SrvAdmins to the Administrators group
                $group.Add("WinNT://$domain/SrvAdmins,group")
                Write-Host "Successfully added SrvAdmins to the $adminGroupName group on $env:COMPUTERNAME"
            }
        }
        return $true
    }
    catch {
        Write-Log "Error adding SrvAdmins to the Administrators group on $ComputerName: $_"
        return $false
    }
}

# Main script execution
foreach ($computer in $computers) {
    Write-Log "Connecting to $computer..."

    # Check if the computer is accessible
    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        # Try to enable remote access if needed
        $remoteAccessEnabled = Enable-RemoteAccess -ComputerName $computer

        if ($remoteAccessEnabled) {
            # Add SrvAdmins to the Administrators group
            $adminGroupUpdated = Add-SrvAdminsToAdministratorsGroup -ComputerName $computer

            if ($adminGroupUpdated) {
                Write-Log "SrvAdmins group processed on $computer."
            }
        } else {
            Write-Log "Unable to enable remote access on $computer. Skipping..."
        }
    } else {
        Write-Log "$computer is not accessible."
    }
}