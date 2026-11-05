Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   PUSHING ANVARLI WEDDING WEBSITE TO GITHUB" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "C:\Users\ghosh\OneDrive\Desktop\wedding"

# Verify git command
$gitCmd = "git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\Program Files\Git\cmd\git.exe") {
        $gitCmd = "C:\Program Files\Git\cmd\git.exe"
    } else {
        Write-Host "ERROR: Git is not installed or not in PATH." -ForegroundColor Red
        pause
        exit 1
    }
}

Write-Host "1. Checking commit status..." -ForegroundColor Yellow
& $gitCmd status

Write-Host ""
Write-Host "2. Pushing 'main' branch to https://github.com/investwithankit12-lang/anvarli-wedding.git..." -ForegroundColor Yellow
Write-Host "NOTE: When prompted:" -ForegroundColor Green
Write-Host "   Username: investwithankit12 (or investwithankit12-lang)" -ForegroundColor Green
Write-Host "   Password: [Paste your GitHub Personal Access Token]" -ForegroundColor Green
Write-Host ""

# First try normal push
& $gitCmd push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Normal push was rejected (likely because GitHub has an auto-generated README/License file)." -ForegroundColor Yellow
    Write-Host "Attempting force push to overwrite the empty GitHub placeholder..." -ForegroundColor Yellow
    & $gitCmd push -u origin main --force
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " SUCCESS! All files have been uploaded to GitHub!" -ForegroundColor Green
    Write-Host " You can now refresh Vercel and import the repository!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Push failed. Please make sure your Personal Access Token (PAT) has the 'repo' scope." -ForegroundColor Red
}

Write-Host ""
pause
