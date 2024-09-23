# This script manages the Administrator account on multiple remote computers.
# It performs the following tasks:
# 1. Enables the Administrator account if it's disabled
# 2. Sets a predefined password for the Administrator account
# 3. Configures the "Password never expires" option for the Administrator account
# The script can read computer names from a file or accept manual input.
# It uses PowerShell remoting to perform these tasks and logs all actions to a file.

# Set error action preference to stop script execution on any error
$ErrorActionPreference = "Stop"

# Set the execution policy for the current process to allow running scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

# Check if the required module is available
if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.LocalAccounts)) {
    Write-Host "The Microsoft.PowerShell.LocalAccounts module is not available. This script may not work correctly on this system."
}

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

# Function to get the list of computers from a file or manual input
function Get-ComputerList {
    # Determine the script's directory
    $scriptPath = $PSScriptRoot
    if (-not $scriptPath) {
        $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    # Set the default path for the computers.txt file
    $defaultFilePath = Join-Path $scriptPath "computers.txt"

    # Check if the default file exists
    if (Test-Path $defaultFilePath) {
        $filePath = $defaultFilePath
    } else {
        # Prompt user for file path if default file doesn't exist
        $filePath = Read-Host "Enter the path to computers.txt file (or press Enter to skip)"
        if ([string]::IsNullOrWhiteSpace($filePath)) {
            $filePath = $null
        } elseif (-not (Test-Path $filePath)) {
            Write-Log "File not found. Proceeding with manual input."
            $filePath = $null
        }
    }

    if ($filePath) {
        # Read computer names from file, excluding comments and empty lines
        Write-Log "Reading computer list from file: $filePath"
        return Get-Content -Path $filePath | Where-Object { $_ -notmatch '^\s*#' -and $_ -ne '' }
    } else {
        # Manual input of computer names
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

# Get the list of computers
$computers = Get-ComputerList

# Prompt for credentials once to use for all remote connections
$cred = Get-Credential
Write-Log "Credentials obtained for remote access."

# Function to enable Administrator account, set password, and configure "Password never expires"
function Enable-AdminAccount {
    param (
        [string]$ComputerName
    )

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            # Try to get the Administrator account (works for both English and Russian systems)
            $adminAccount = Get-LocalUser | Where-Object {$_.SID -like '*-500'}

            if ($adminAccount) {
                $adminName = $adminAccount.Name

                # Enable the account if it's disabled
                if (-not $adminAccount.Enabled) {
                    Enable-LocalUser -Name $adminName
                    Write-Output "Administrator account ($adminName) has been enabled on $env:COMPUTERNAME"
                } else {
                    Write-Output "Administrator account ($adminName) is already enabled on $env:COMPUTERNAME"
                }

                # Set the password
                $password = ConvertTo-SecureString "Wh1202Dq!" -AsPlainText -Force
                try {
                    Set-LocalUser -Name $adminName -Password $password -ErrorAction Stop
                    Write-Output "Password set for Administrator account ($adminName) on $env:COMPUTERNAME"
                } catch {
                    Write-Output "Failed to set password for Administrator account ($adminName) on $env:COMPUTERNAME: $_"
                }

                # Set "Password never expires" option
                try {
                    Set-LocalUser -Name $adminName -PasswordNeverExpires $true -ErrorAction Stop
                    Write-Output "'Password never expires' option enabled for Administrator account ($adminName) on $env:COMPUTERNAME"
                } catch {
                    Write-Output "Failed to set 'Password never expires' option for Administrator account ($adminName) on $env:COMPUTERNAME: $_"
                }
            } else {
                Write-Output "Administrator account not found on $env:COMPUTERNAME"
            }
        }
        return $true
    }
    catch {
        Write-Log "Error processing Administrator account on $ComputerName":" $_"
        return $false
    }
}

# Main script execution
Write-Log "Script execution started."

foreach ($computer in $computers) {
    Write-Log "Connecting to $computer..."

    # Check if the computer is accessible
    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        # Enable Administrator account, set password, and configure "Password never expires"
        $adminAccountProcessed = Enable-AdminAccount -ComputerName $computer

        if ($adminAccountProcessed) {
            Write-Log "Administrator account processed on $computer."
        } else {
            Write-Log "Failed to process Administrator account on $computer."
        }
    } else {
        Write-Log "$computer is not accessible."
    }
}

Write-Log "Script execution completed."