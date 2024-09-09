# Parameters
$sourceFile = "\\path\to\file\example.txt"  # Source file for backup
$backupFolder = "C:\Backups"  # Folder to store backups
$maxDays = 30  # Maximum number of days to keep backups

# Create the backup folder if it doesn't exist
if (!(Test-Path -Path $backupFolder)) {
    New-Item -Path $backupFolder -ItemType Directory | Out-Null
}

# Create the archive name with the current date and time
$archiveName = "FILE_$(Get-Date -Format "yyyy-MM-dd_HH-mm-ss").zip"
$archivePath = Join-Path -Path $backupFolder -ChildPath $archiveName

try {
    # Archive the file
    Compress-Archive -Path $sourceFile -DestinationPath $archivePath -Force -ErrorAction Stop
    Write-Host "File successfully archived: $archivePath"
} catch {
    # Output an error message if archiving fails
    Write-Host "Error archiving the file 'example.txt': $($_.Exception.Message)"
}

# Delete old archives, keeping those created on the first day of each month
$oldArchives = Get-ChildItem -Path $backupFolder -Filter "FILE_*.zip" | Where-Object {
    $_.CreationTime -lt (Get-Date).AddDays(-$maxDays) -and
    $_.CreationTime.Day -ne 1  # Do not delete archives created on the first day of the month
}

foreach ($archive in $oldArchives) {
    Remove-Item -Path $archive.FullName -Force
    Write-Host "Deleted old archive: $($archive.Name)"
}

# Output a message indicating the backup process is complete and old archives are deleted
Write-Host "Backup of 'example.txt' file completed. Old archives deleted, keeping archives from the first day of each month."