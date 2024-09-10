# Define the remote computer name
$remoteComputer = "GerdtR1"

# Define the firewall rules
$firewallRules = @(
    @{Name="Veeam Backup Service"; Protocol="TCP"; LocalPort="10001"},
    @{Name="Veeam Enterprise Manager"; Protocol="TCP"; LocalPort="9392"},
    @{Name="Veeam Backup Catalog Service"; Protocol="TCP"; LocalPort="9401"},
    @{Name="Veeam Data Transfer"; Protocol="TCP"; LocalPort="2500-3300"},
    @{Name="Veeam Backup PowerShell"; Protocol="TCP"; LocalPort="6160"},
    @{Name="Veeam VMware ESXi"; Protocol="TCP"; LocalPort="902,903"},
    @{Name="Veeam Windows SMB"; Protocol="TCP"; LocalPort="445"},
    @{Name="Veeam Agent for Linux"; Protocol="UDP"; LocalPort="6161"}
    
)

# Function to add firewall rules
function Add-VeeamFirewallRules {
    param (
        [string]$ComputerName,
        [array]$Rules,
        [string]$Profile
    )

    Invoke-Command -ComputerName $ComputerName -ScriptBlock {
        param($Rules, $Profile)
        
        foreach ($rule in $Rules) {
            $existingRule = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue

            if (-not $existingRule) {
                New-NetFirewallRule -DisplayName $rule.Name `
                                    -Direction Inbound `
                                    -Profile $Profile `
                                    -Action Allow `
                                    -Protocol $rule.Protocol `
                                    -LocalPort $rule.LocalPort
                Write-Host "Added firewall rule: $($rule.Name) for $Profile profile"
            } else {
                Write-Host "Firewall rule already exists: $($rule.Name)"
            }
        }
    } -ArgumentList $Rules, $Profile
}

# Add rules for Domain profile
Add-VeeamFirewallRules -ComputerName $remoteComputer -Rules $firewallRules -Profile "Domain"

# Add rules for Private profile
Add-VeeamFirewallRules -ComputerName $remoteComputer -Rules $firewallRules -Profile "Private"

Write-Host "Firewall rules for Veeam Backup & Replication have been added to $remoteComputer for Domain and Private profiles."