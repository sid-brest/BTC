# Stop the "EDeclaration (managed by AlwaysUpService)" service
Stop-Service -Name "EDeclaration (managed by AlwaysUpService)"

# Wait until the service is fully stopped
while ((Get-Service -Name "EDeclaration (managed by AlwaysUpService)").Status -ne "Stopped") {
    Start-Sleep -Seconds 1
}

# Define parameters
$sourceFolder = "C:\EDeclaration\edecl"  # Source folder for backup
$backupFolder = "C:\Backups"  # Folder to store backups
$maxDays = 30  # Maximum number of days to keep backups

# Create the backup folder if it doesn't exist
if (!(Test-Path -Path $backupFolder)) {
    New-Item -Path $backupFolder -ItemType Directory | Out-Null
}

# Create the archive name with the current date and time
$archiveName = "EDeclaration_$(Get-Date -Format "yyyy-MM-dd_HH-mm-ss").zip"
$archivePath = Join-Path -Path $backupFolder -ChildPath $archiveName

try {
    # Archive the folder, even if some files are locked
    Compress-Archive -Path $sourceFolder -DestinationPath $archivePath -Force -ErrorAction SilentlyContinue
} catch {
    # Output an error message if archiving fails
    Write-Host "Error archiving the 'EDeclaration' folder: $($_.Exception.Message)"
}

# Delete old archives that are older than the specified number of days
$oldArchives = Get-ChildItem -Path $backupFolder -Filter "EDeclaration_*.zip" | Where-Object { $_.CreationTime -lt (Get-Date).AddDays(-$maxDays) }
foreach ($archive in $oldArchives) {
    Remove-Item -Path $archive.FullName -Force
}

# Output a message indicating the backup process is complete and old archives are deleted
Write-Host "Backup of 'EDeclaration' folder completed. Old archives deleted."

# Restart the "EDeclaration (managed by AlwaysUpService)" service
Start-Service -Name "EDeclaration (managed by AlwaysUpService)"