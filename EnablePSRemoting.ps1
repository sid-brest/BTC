Enable-PSRemoting -Force -SkipNetWorkProfileCheck
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "Computername"