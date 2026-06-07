# szu-sports-booking skill \u52a0\u8f7d .env \u5230\u5f53\u524d PowerShell \u4f1a\u8bdd
#
# \u7528\u6cd5 (. \u8868\u793a source, \u4e0d\u662f\u65b0\u5f00 child process):
#   . .\agents\skills\szu-sports-booking\scripts\load_env.ps1
#
# \u52a0\u8f7d .env \u540e, \u8fd0\u884c booking api \u5c31\u80fd\u81ea\u52a8\u8bfb\u5230\u51ed\u8bc1:
#   python -m booking.cli api -s \u7f51\u7403 -t 19:00-20:00 --dry-run

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $SkillDir ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Host "[X] \u672a\u627e\u5230 $EnvFile" -ForegroundColor Red
    Write-Host "  \u8bf7\u590d\u5236\u4e26\u7f16\u8f91: cp $SkillDir\.env.example $EnvFile" -ForegroundColor Yellow
    return
}

# \u89e3\u6790 KEY=VALUE \u5e76\u5bfc\u51fa
$count = 0
Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    if ($line -match "^([^=]+)=(.*)$") {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        # \u53bb\u6389\u5305\u88f9\u5f15\u53f7
        if ($value -match '^"(.*)"$') { $value = $matches[1] }
        Set-Item -Path "Env:$key" -Value $value
        $count++
    }
}

Write-Host "[OK] \u5df2\u52a0\u8f7d $count \u4e2a\u73af\u5883\u53d8\u91cf\u4ece $EnvFile" -ForegroundColor Green
if ($env:SZU_USERNAME) {
    Write-Host "     SZU_USERNAME=$env:SZU_USERNAME" -ForegroundColor Gray
    $suffix = $env:SZU_USERNAME.Substring([Math]::Max(0, $env:SZU_USERNAME.Length - 4))
    $pwdKey = "SZU_PASSWORD_$suffix"
    if (Test-Path "Env:$pwdKey") {
        Write-Host "     $pwdKey=********" -ForegroundColor Gray
    }
}
