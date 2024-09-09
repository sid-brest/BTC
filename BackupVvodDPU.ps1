# Define the parent directory where backups will be stored
$backupParentDirectory = "C:\Backups"

# Define the path to the pg_basebackup executable
$pgBaseBackupPath = "C:\Program Files\PostgreSQL\16\bin\pg_basebackup.exe"

# Define the PostgreSQL username
$username = "postgres"

# Define the PostgreSQL password
$password = "strongpassword"

# Define the database host
$dbhost = "localhost"

# Define the database port
$port = "5432"

# Get the current date and time in the specified format
$backupDate = Get-Date -Format "yyyyMMdd_HHmmss"

# Create the full path for the backup directory
$backupDirectory = Join-Path -Path $backupParentDirectory -ChildPath "vvod_dpu_$backupDate"

# Create the backup directory if it doesn't already exist
if (-not (Test-Path $backupDirectory)) {
    New-Item -ItemType Directory -Path $backupDirectory | Out-Null
}

# Create a secure string for the password
$securePassword = ConvertTo-SecureString $password -AsPlainText -Force

# Create a PSCredential object using the username and secure password
$credential = New-Object System.Management.Automation.PSCredential ($username, $securePassword)

# Set the PGPASSWORD environment variable to the plain text password
$env:PGPASSWORD = $password

try {
    # Define the arguments for the pg_basebackup command
    $backupArgs = "--pgdata=`"$backupDirectory`" --username=`"$username`" --host=`"$dbhost`" --port=`"$port`" --format=tar --compress=9"
    
    # Run the pg_basebackup command with the specified arguments
    Start-Process -FilePath $pgBaseBackupPath -ArgumentList $backupArgs -NoNewWindow -Wait
}
finally {
    # Clear the PGPASSWORD environment variable
    Remove-Item Env:\PGPASSWORD
}

# Define the number of days to keep backups
$olderThanDays = 30

# Get the list of backup folders older than the specified number of days
$backupFolders = Get-ChildItem -Path $backupParentDirectory | Where-Object { $_.PSIsContainer -and $_.CreationTime -lt (Get-Date).AddDays(-$olderThanDays) }

# Loop through each old backup folder and remove it
foreach ($folder in $backupFolders) {
    Write-Host "Removing backup folder: $($folder.FullName)"
    Remove-Item -Path $folder.FullName -Recurse -Force
}
