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

# Prompt for the path to the folder containing installers
$installerPath = Read-Host "Enter the path to the folder containing installers"

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

function Install-SilentApps {
    param (
        [string]$ComputerName,
        [string]$InstallerPath
    )

    try {
        # Create a temporary folder on the remote computer
        $remoteTemp = Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            $tempPath = Join-Path $env:TEMP "SilentInstalls"
            if (-not (Test-Path $tempPath)) {
                New-Item -ItemType Directory -Path $tempPath | Out-Null
            }
            return $tempPath
        }

        # Copy installers to the remote computer
        Copy-Item -Path "$InstallerPath\*" -Destination $remoteTemp -ToSession (New-PSSession -ComputerName $ComputerName -Credential $cred)

        # Install applications
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            param($remoteTemp)
            
            Get-ChildItem $remoteTemp -File | ForEach-Object {
                $installer = $_.FullName
                if ($_.Extension -eq ".msi") {
                    Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /qn" -Wait -NoNewWindow
                }
                elseif ($_.Extension -eq ".exe") {
                    Start-Process $installer -ArgumentList "/S" -Wait -NoNewWindow
                }
                Write-Host "Installed $($_.Name) on $env:COMPUTERNAME"
            }
        } -ArgumentList $remoteTemp

        # Clean up temporary folder
        Invoke-Command -ComputerName $ComputerName -Credential $cred -ScriptBlock {
            param($remoteTemp)
            Remove-Item -Path $remoteTemp -Recurse -Force
        } -ArgumentList $remoteTemp

        Write-Host "All applications have been installed on $ComputerName"
        return $true
    }
    catch {
        Write-Host "Error installing applications on $ComputerName":" $_"
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
            # Install silent applications
            $appsInstalled = Install-SilentApps -ComputerName $computer -InstallerPath $installerPath

            if ($appsInstalled) {
                Write-Host "Applications installed successfully on $computer."
            } else {
                Write-Host "Failed to install applications on $computer."
            }
        } else {
            Write-Host "Unable to enable remote access on $computer. Skipping..."
        }
    } else {
        Write-Host "$computer is not accessible."
    }
}