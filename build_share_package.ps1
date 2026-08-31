$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Out = Join-Path $Root "dist\AIInterviewCoach-Windows"
$Zip = Join-Path $Root "dist\AIInterviewCoach-Windows.zip"

if (Test-Path $Out) { Remove-Item -LiteralPath $Out -Recurse -Force }
if (Test-Path $Zip) { Remove-Item -LiteralPath $Zip -Force }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

Copy-Item -LiteralPath (Join-Path $Root "app.py") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "app_ui.py") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "app_ui.css") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "requirements.txt") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root ".env.example") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "SHARING.md") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "install_windows.ps1") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "install_windows.bat") -Destination $Out -Force
Copy-Item -LiteralPath (Join-Path $Root "start_literature_translation.bat") -Destination $Out -Force

foreach ($folder in @("modules", "components")) {
    $sourceFolder = Join-Path $Root $folder
    $targetFolder = Join-Path $Out $folder
    New-Item -ItemType Directory -Force -Path $targetFolder | Out-Null
    Get-ChildItem -LiteralPath $sourceFolder -Recurse -File | Where-Object {
        $_.FullName -notmatch "\\__pycache__\\" -and $_.Extension -ne ".pyc"
    } | ForEach-Object {
        $relative = $_.FullName.Substring($sourceFolder.Length).TrimStart("\\")
        $target = Join-Path $targetFolder $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $target -Force
    }
}
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "Package created: $Zip" -ForegroundColor Green
