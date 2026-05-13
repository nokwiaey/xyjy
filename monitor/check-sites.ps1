param(
    [int]$TimeoutSec = 15,
    [switch]$Json,
    [switch]$Quiet
)

$sites = @(
    @{ Name = "GitHub（主站）";       Url = "https://nokwiaey.github.io/xyjy/" }
    @{ Name = "Cloudflare（副站）";    Url = "https://xyjy.dfly.site/" }
    @{ Name = "帽子云（镜像站）";       Url = "https://xyjy-rbw5h01el.maozi.io/" }
    @{ Name = "Vercel（镜像站）";      Url = "https://xyjy-tools.vercel.app/" }
    @{ Name = "Netlify（镜像站）";      Url = "https://xyjy.netlify.app/" }
)

$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$dateStr = Get-Date -Format "yyyy-MM-dd"
$csvFile = Join-Path $logDir "response-log.csv"
$isNewFile = -not (Test-Path $csvFile)

$results = foreach ($site in $sites) {
    $start = Get-Date
    try {
        $response = Invoke-WebRequest -Uri $site.Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        $elapsed = [math]::Round(((Get-Date) - $start).TotalMilliseconds, 0)
        $statusCode = [int]$response.StatusCode
        $ok = ($statusCode -ge 200 -and $statusCode -lt 400)
    } catch {
        $elapsed = [math]::Round(((Get-Date) - $start).TotalMilliseconds, 0)
        $statusCode = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode.value__ } else { 0 }
        $ok = $false
    }

    [PSCustomObject]@{
        Name       = $site.Name
        Url        = $site.Url
        StatusCode = $statusCode
        TimeMs     = $elapsed
        OK         = $ok
    }

    if (-not $Quiet) {
        $icon = if ($ok) { "✓" } else { "✗" }
        $color = if ($ok) { "Green" } else { "Red" }
        Write-Host "$icon " -NoNewline -ForegroundColor $color
        Write-Host ("{0,-18} {1,6}ms  HTTP {2}" -f $site.Name, $elapsed, $statusCode) -ForegroundColor $color
    }
}

# Append to CSV log (create with header if new file)
foreach ($r in $results) {
    $row = [PSCustomObject]@{
        Timestamp  = $timestamp
        Date       = $dateStr
        Name       = $r.Name
        Url        = $r.Url
        StatusCode = $r.StatusCode
        TimeMs     = $r.TimeMs
        OK         = $r.OK
    }
    $row | Export-Csv -Path $csvFile -NoTypeInformation -Append
}

# Generate daily summary JSON
$jsonFile = Join-Path $logDir "latest.json"
$summary = @{
    checkedAt  = $timestamp
    totalSites = $results.Count
    okSites    = ($results | Where-Object OK).Count
    avgTimeMs  = [math]::Round(($results | Measure-Object TimeMs -Average).Average, 0)
    sites      = $results
}
$summary | ConvertTo-Json -Depth 3 | Set-Content -Path $jsonFile -Encoding UTF8

if ($Json) {
    $summary | ConvertTo-Json -Depth 3
}

# Summary line
if (-not $Quiet) {
    $okCount = ($results | Where-Object OK).Count
    $total = $results.Count
    $avg = [math]::Round(($results | Measure-Object TimeMs -Average).Average, 0)
    Write-Host ""
    Write-Host ("{0}/{1} 站点正常, 平均响应 {2}ms | {3}" -f $okCount, $total, $avg, $timestamp)
}
