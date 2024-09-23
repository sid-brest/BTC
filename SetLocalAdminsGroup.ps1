# This script enables remote access and adds the 'LocalAdmins' group to the local Administrators group on multiple computers.
# It can read computer names from a file or accept manual input, and uses PowerShell remoting to perform these tasks.
# The script also logs all actions, errors, and successes to a log file.

# Get the script name without the .ps1 extension for the log file
$scriptName = [System.IO.Path]::GetFileNameWithoutExtension($MyInvocation.MyCommand.Name)
$logFile = Join-Path $PSScriptRoot "$scriptName.log"

# Function to write to both console and log file
function Write-Log {
    param (
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $logFile -Value $logMessage
}

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
            Write-Log "File not found. Proceeding with manual input."
            $filePath = $null
        }
    }

    if ($filePath) {
        Write-Log "Reading computer list from file: $filePath"
        return Get-Content -Path $filePath | Where-Object { $_ -notmatch '^\s*#' -and $_ -ne '' }
    } else {
        Write-Log "Manual input of computer names initiated."
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

$computers = Get-ComputerList

$cred = Get-Credential
Write-Log "Credentials obtained for remote access."

function Enable-RemoteAccess {
    param (
        [string]$ComputerName
    )

    try {
        $winrmStatus = Invoke-Command -ComputerName $ComputerName -ScriptBlock { Get-Service WinRM } -ErrorAction Stop

        if ($winrmStatus.Status -ne 'Running') {
            Write-Log "WinRM service is not running on $ComputerName. Attempting to start..."
            Invoke-Command -ComputerName $ComputerName -ScriptBlock { 
                Start-Service WinRM
                Set-Service WinRM -StartupType Automatic
            }
        }

        Invoke-Command -ComputerName $ComputerName -ScriptBlock {
            Enable-PSRemoting -Force
            Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
            Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB 1024
        }

        Write-Log "Remote access has been successfully enabled on $ComputerName"
        return $true
    }
    catch {
        Write-Log "Failed to enable remote access on $ComputerName. Error: $_"
        return $false
    }
}

function Add-LocalAdminsToAdministratorsGroup {
    param (
        [string]$ComputerName
    )

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            $domain = (Get-WmiObject Win32_ComputerSystem).Domain
            $adminGroupName = (Get-WmiObject -Class Win32_Group -Filter "SID='S-1-5-32-544'").Name
            $group = [ADSI]"WinNT://./$adminGroupName,group"
            $members = @($group.Invoke("Members"))
            $localAdminsExists = $members | ForEach-Object { $_.GetType().InvokeMember("Name", 'GetProperty', $null, $_, $null) } | Where-Object { $_ -eq "LocalAdmins" }

            if ($localAdminsExists) {
                $message = "LocalAdmins is already a member of the $adminGroupName group on $env:COMPUTERNAME"
            } else {
                $group.Add("WinNT://$domain/LocalAdmins,group")
                $message = "Successfully added LocalAdmins to the $adminGroupName group on $env:COMPUTERNAME"
            }
            Write-Output $message
        }
        Write-Log "Operation on $ComputerName":" $_"
        return $true
    }
    catch {
        Write-Log "Error adding LocalAdmins to the Administrators group on $ComputerName":" $_"
        return $false
    }
}

Write-Log "Script execution started."

foreach ($computer in $computers) {
    Write-Log "Connecting to $computer..."

    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        $remoteAccessEnabled = Enable-RemoteAccess -ComputerName $computer

        if ($remoteAccessEnabled) {
            $adminGroupUpdated = Add-LocalAdminsToAdministratorsGroup -ComputerName $computer

            if ($adminGroupUpdated) {
                Write-Log "LocalAdmins group processed on $computer."
            } else {
                Write-Log "Failed to process LocalAdmins group on $computer."
            }
        } else {
            Write-Log "Unable to enable remote access on $computer. Skipping..."
        }
    } else {
        Write-Log "$computer is not accessible."
    }
}

Write-Log "Script execution completed."