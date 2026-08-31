$ErrorActionPreference = "Stop"

$InstallRoot = Join-Path $env:LOCALAPPDATA "AI-Interview-Coach"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $InstallRoot ".venv"
$EnvPath = Join-Path $InstallRoot ".env"
$LauncherPath = Join-Path $InstallRoot "start_ai_interview.bat"
$LiteratureLauncherPath = Join-Path $InstallRoot "start_literature_translation.bat"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "AI Interview Coach.lnk"
$LiteratureShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "文献阅读翻译模拟.lnk"

function Find-Python {
    $candidates = @(
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "python"; Args = @() }
    )
    foreach ($candidate in $candidates) {
        try {
            & $candidate.Command @($candidate.Args) --version 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    throw "Python 3 was not found. Install Python 3.9-3.13 and enable Add Python to PATH."
}

Write-Host "Installing AI Interview Coach..." -ForegroundColor Cyan
$python = Find-Python
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null

$copyItems = @("app.py", "app_ui.py", "app_ui.css", "requirements.txt", ".env.example", "README.md", "start_literature_translation.bat", "modules", "components")
foreach ($item in $copyItems) {
    $source = Join-Path $SourceRoot $item
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination $InstallRoot -Recurse -Force
    }
}
New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot "data") | Out-Null

if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    & $python.Command @($python.Args) -m venv $VenvPath
}
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r (Join-Path $InstallRoot "requirements.txt")

if (-not (Test-Path $EnvPath)) {
    Copy-Item (Join-Path $InstallRoot ".env.example") $EnvPath
}
$existing = Get-Content -Raw $EnvPath
if ($existing -match "your_api_key_here") {
    $secureKey = Read-Host "Enter your SiliconFlow API Key" -AsSecureString
    $key = [System.Net.NetworkCredential]::new("", $secureKey).Password
    if ([string]::IsNullOrWhiteSpace($key)) { throw "API Key cannot be empty." }
    $existing = $existing -replace "DEEPSEEK_API_KEY=.*", ("DEEPSEEK_API_KEY=" + $key.Trim())
    [System.IO.File]::WriteAllText($EnvPath, $existing, [System.Text.UTF8Encoding]::new($false))
}

@"
@echo off
cd /d "%~dp0"
"$VenvPython" -m streamlit run app_ui.py
"@ | Set-Content -Path $LauncherPath -Encoding ASCII

if (Test-Path (Join-Path $InstallRoot "start_literature_translation.bat")) {
    Copy-Item (Join-Path $InstallRoot "start_literature_translation.bat") $LiteratureLauncherPath -Force
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $env:ComSpec
$shortcut.Arguments = "/c `"$LauncherPath`""
$shortcut.WorkingDirectory = $InstallRoot
$shortcut.Description = "AI 学术面试教练"
$shortcut.Save()

if (Test-Path $LiteratureLauncherPath) {
    $literatureShortcut = $shell.CreateShortcut($LiteratureShortcutPath)
    $literatureShortcut.TargetPath = $env:ComSpec
    $literatureShortcut.Arguments = "/c `"$LiteratureLauncherPath`""
    $literatureShortcut.WorkingDirectory = $InstallRoot
    $literatureShortcut.Description = "预推免英文文献阅读翻译模拟"
    $literatureShortcut.Save()
}

Write-Host "Installation complete. Desktop shortcuts: AI Interview Coach; 文献阅读翻译模拟" -ForegroundColor Green
Start-Process -FilePath $env:ComSpec -ArgumentList "/c `"$LauncherPath`""
