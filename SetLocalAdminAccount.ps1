# Function to get computers
$ErrorActionPreference = "Stop"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

# Ensure the required module is available
if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.LocalAccounts)) {
    Write-Host "The Microsoft.PowerShell.LocalAccounts module is not available. This script may not work correctly on this system."
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
                    Write-Host "Administrator account ($adminName) has been enabled on $env:COMPUTERNAME"
                } else {
                    Write-Host "Administrator account ($adminName) is already enabled on $env:COMPUTERNAME"
                }

                # Set the password
                $password = ConvertTo-SecureString "Wh1202Dq!" -AsPlainText -Force
                try {
                    Set-LocalUser -Name $adminName -Password $password -ErrorAction Stop
                    Write-Host "Password set for Administrator account ($adminName) on $env:COMPUTERNAME"
                } catch {
                    Write-Host "Failed to set password for Administrator account ($adminName) on $env:COMPUTERNAME: $_"
                }

                # Set "Password never expires" option
                try {
                    Set-LocalUser -Name $adminName -PasswordNeverExpires $true -ErrorAction Stop
                    Write-Host "'Password never expires' option enabled for Administrator account ($adminName) on $env:COMPUTERNAME"
                } catch {
                    Write-Host "Failed to set 'Password never expires' option for Administrator account ($adminName) on $env:COMPUTERNAME: $_"
                }
            } else {
                Write-Host "Administrator account not found on $env:COMPUTERNAME"
            }
        }
        return $true
    }
    catch {
        Write-Host "Error processing Administrator account on $ComputerName":" $_"
        return $false
    }
}

# Main script execution
foreach ($computer in $computers) {
    Write-Host "Connecting to $computer..."

    # Check if the computer is accessible
    if (Test-Connection -ComputerName $computer -Count 1 -Quiet) {
        # Enable Administrator account, set password, and configure "Password never expires"
        $adminAccountProcessed = Enable-AdminAccount -ComputerName $computer

        if ($adminAccountProcessed) {
            Write-Host "Administrator account processed on $computer."
        } else {
            Write-Host "Failed to process Administrator account on $computer."
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}