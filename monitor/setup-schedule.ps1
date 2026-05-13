param(
    [int]$IntervalMinutes = 30,
    [switch]$Remove
)

$taskName = "星元工具箱-站点监控"
$scriptPath = Join-Path $PSScriptRoot "check-sites.ps1"

if (-not (Test-Path $scriptPath)) {
    Write-Host "错误: 找不到 check-sites.ps1，请确保脚本在同一目录下" -ForegroundColor Red
    exit 1
}

if ($Remove) {
    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
        Write-Host "已删除定时任务: $taskName" -ForegroundColor Green
    } catch {
        Write-Host "任务不存在或删除失败: $_" -ForegroundColor Yellow
    }
    exit 0
}

$action = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-NoProfile -WindowStyle Hidden -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
    # Remove existing task first
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Write-Host "定时任务已创建: $taskName" -ForegroundColor Green
    Write-Host "  检测间隔: 每 $IntervalMinutes 分钟"
    Write-Host "  脚本路径: $scriptPath"
    Write-Host "  日志目录: $(Join-Path $PSScriptRoot 'logs')"
    Write-Host ""
    Write-Host "立即运行一次测试..." -ForegroundColor Cyan
    pwsh.exe -NoProfile -File $scriptPath
} catch {
    Write-Host "创建任务失败: $_" -ForegroundColor Red
    Write-Host "请以管理员身份运行此脚本" -ForegroundColor Yellow
}
