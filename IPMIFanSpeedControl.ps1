# Путь к IPMICFG-Win.exe (замените на актуальный путь)
$ipmicfg = "C:\Path\To\IPMICFG-Win.exe"

# Функция для выполнения IPMI команд
function Invoke-IPMI {
    param (
        [string[]]$args
    )
    & $ipmicfg $args
}

# Функция для получения температуры CPU
function Get-CPUTemperature {
    $output = Invoke-IPMI -raw 0x04 0x2d 0x01
    return [int]($output -split " ")[-1]
}

# Функция для получения температуры дисков
function Get-DiskTemperatures {
    $temps = @()
    $disks = Get-WmiObject Win32_DiskDrive | Where-Object { $_.MediaType -eq "Fixed hard disk media" }
    foreach ($disk in $disks) {
        $smartData = Get-WmiObject -Namespace root\wmi -Class MSStorageDriver_ATAPISmartData -Filter "InstanceName like '%$($disk.PNPDeviceID)%'"
        if ($smartData) {
            $temp = $smartData.VendorSpecific[194]
            if ($temp) {
                $temps += $temp
            }
        }
    }
    return $temps
}

# Функция для установки скорости вентиляторов
function Set-FanSpeed {
    param (
        [int]$speed
    )
    $hexSpeed = [convert]::ToString($speed, 16).PadLeft(2, '0')
    Invoke-IPMI -raw 0x30 0x70 0x66 0x01 0x00 "0x$hexSpeed"
    Invoke-IPMI -raw 0x30 0x70 0x66 0x01 0x01 "0x$hexSpeed"
}

# Основная логика скрипта
$cpuTemp = Get-CPUTemperature
$diskTemps = Get-DiskTemperatures

$maxTemp = ($cpuTemp, ($diskTemps | Measure-Object -Maximum).Maximum) | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum

if ($maxTemp -ge 50) {
    # Установка оптимального режима
    Invoke-IPMI -raw 0x30 0x45 0x01 0x00
    Write-Output "Температура высокая ($maxTemp°C). Установлен оптимальный режим вентиляторов."
} else {
    # Установка скорости вентиляторов на 15%
    Set-FanSpeed -speed 15
    Write-Output "Температура нормальная ($maxTemp°C). Скорость вентиляторов установлена на 15%."
}