# Function to get valid computer name
function Get-ValidComputerName {
    do {
        $computerName = Read-Host "Enter the name of the remote computer"
        if ([string]::IsNullOrWhiteSpace($computerName)) {
            Write-Host "Computer name cannot be empty. Please try again."
        } elseif (-not (Test-Connection -ComputerName $computerName -Count 1 -Quiet)) {
            Write-Host "Unable to reach $computerName. Please check the name and try again."
        } else {
            return $computerName
        }
    } while ($true)
}

# Get remote computer name from user
$remoteComputer = Get-ValidComputerName

# Define the firewall rules
$firewallRules = @(
    @{Name="FusionInventory Agent"; Protocol="TCP"; LocalPort="62354"}    
)

# Function to add firewall rules
function Add-VeeamFirewallRules {
    param (
        [string]$ComputerName,
        [array]$Rules,
        [string]$NetworkProfile  # Changed from $Profile to $NetworkProfile
    )

    Invoke-Command -ComputerName $ComputerName -ScriptBlock {
        param($Rules, $NetworkProfile)  # Changed parameter name here as well
        
        foreach ($rule in $Rules) {
            $existingRule = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue

            if (-not $existingRule) {
                New-NetFirewallRule -DisplayName $rule.Name `
                                    -Direction Inbound `
                                    -Profile $NetworkProfile `  # Updated here
                                    -Action Allow `
                                    -Protocol $rule.Protocol `
                                    -LocalPort $rule.LocalPort
                Write-Host "Added firewall rule: $($rule.Name) for $NetworkProfile profile"  # Updated here
            } else {
                Write-Host "Firewall rule already exists: $($rule.Name)"
            }
        }
    } -ArgumentList $Rules, $NetworkProfile  # Updated argument name here
}

# Add rules for Domain profile
Add-VeeamFirewallRules -ComputerName $remoteComputer -Rules $firewallRules -NetworkProfile "Domain"

# Add rules for Private profile
Add-VeeamFirewallRules -ComputerName $remoteComputer -Rules $firewallRules -NetworkProfile "Private"

Write-Host "Firewall rules have been added to $remoteComputer for Domain and Private profiles."
