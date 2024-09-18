# SetTime.ps1

$scriptBlock = {
function Get-CurrentInternetTime {
    $url = "http://worldtimeapi.org/api/ip"
    try {
        $response = (New-Object System.Net.WebClient).DownloadString($url)
        Write-Host "Полученный ответ: $response"
        
        if ($response -match '"datetime":"([^"]+)"') {
            return $matches[1]
        }
    }
    catch {
        Write-Host "Ошибка при получении времени из интернета: $_"
    }
    return $null
}

$currentDateTime = Get-CurrentInternetTime

if ($currentDateTime) {
    Write-Host "Полученное время: $currentDateTime"
    
    # Добавляем новый формат, соответствующий полученной дате
    $formats = @(
        "yyyy-MM-ddTHH:mm:ss.ffffffzzz",
        "yyyy-MM-ddTHH:mm:ss.fffffffzzz",
        "yyyy-MM-ddTHH:mm:sszzz",
        "yyyy-MM-ddTHH:mm:ss.fffzzz"
    )
    
    $parsedDate = $null
    foreach ($format in $formats) {
        try {
            $parsedDate = [datetime]::ParseExact($currentDateTime, $format, [System.Globalization.CultureInfo]::InvariantCulture)
            Write-Host "Успешно разобрана дата с форматом: $format"
            break
        }
        catch {
            Write-Host "Не удалось разобрать дату с форматом $format"
        }
    }
    
    if ($parsedDate) {
        try {
            Set-Date -Date $parsedDate
            Write-Host "Время успешно синхронизировано: $parsedDate"
        }
        catch {
            Write-Host "Ошибка при установке времени: $_"
        }
    }
    else {
        Write-Host "Не удалось разобрать полученную дату ни с одним из известных форматов."
    }
}
else {
    Write-Host "Не удалось получить текущее время из интернета."
}

# Вывод текущего системного времени для проверки
Write-Host "Текущее системное время: $(Get-Date)"
}

# Execute the script block on the specified remote computer
Invoke-Command -ComputerName "computername" -ScriptBlock $scriptBlock