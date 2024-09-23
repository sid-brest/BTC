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
            Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB 1024
        }

        Write-Host "Remote access has been successfully enabled on $ComputerName"
        return $true
    }
    catch {
        Write-Host "Failed to enable remote access on $ComputerName. Error: $_"
        return $false
    }
}

function Add-SrvAdminsToAdministratorsGroup {
    param (
        [string]$ComputerName
    )

    try {
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            # Get the domain name
            $domain = (Get-WmiObject Win32_ComputerSystem).Domain

            # Determine the Administrators group name based on the system language
            $adminGroupName = (Get-WmiObject -Class Win32_Group -Filter "SID='S-1-5-32-544'").Name

            # Check if SrvAdmins is already in the Administrators group
            $group = [ADSI]"WinNT://./$adminGroupName,group"
            $members = @($group.Invoke("Members"))
            $SrvAdminsExists = $members | ForEach-Object { $_.GetType().InvokeMember("Name", 'GetProperty', $null, $_, $null) } | Where-Object { $_ -eq "SrvAdmins" }

            if ($SrvAdminsExists) {
                Write-Host "SrvAdmins is already a member of the $adminGroupName group on $env:COMPUTERNAME"
            } else {
                $group.Add("WinNT://$domain/SrvAdmins,group")
                Write-Host "Successfully added SrvAdmins to the $adminGroupName group on $env:COMPUTERNAME"
            }
        }
        return $true
    }
    catch {
        Write-Host "Error adding SrvAdmins to the Administrators group on $ComputerName":" $_"
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
            # Add SrvAdmins to the Administrators group
            $adminGroupUpdated = Add-SrvAdminsToAdministratorsGroup -ComputerName $computer

            if ($adminGroupUpdated) {
                Write-Host "SrvAdmins group processed on $computer."
            }
        } else {
            Write-Host "Unable to enable remote access on $computer. Skipping..."
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}