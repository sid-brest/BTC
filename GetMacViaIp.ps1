param(
    [Parameter(Mandatory=$true)]
    [string]$IPAddress
)

# Clear the ARP cache
arp -d

# Ping the IP address to ensure it's in the ARP cache
ping -n 1 $IPAddress | Out-Null

# Get the MAC address from the ARP cache
$result = arp -a $IPAddress | Select-String $IPAddress

if ($result) {
    $macAddress = ($result -split '\s+')[2]
    Write-Output "The MAC address for IP $IPAddress is: $macAddress"
} else {
    Write-Output "Unable to find MAC address for IP $IPAddress"
}