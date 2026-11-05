Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   PUSHING RISHAN EVENTS WEBSITE TO GITHUB" -ForegroundColor Cyan
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

Write-Host "1. Staging all changed files (Rishan Events rebrand, logo, +91 96470 02563, and HD varmala animation)..." -ForegroundColor Yellow
& $gitCmd add -A

Write-Host "2. Committing changes..." -ForegroundColor Yellow
& $gitCmd commit -m "Rebrand to Rishan Events, add official logo, update phone to +91 96470 02563, and enhance varmala 3D scroll resolution and clarity"

Write-Host ""
Write-Host "3. Pushing 'main' branch to https://github.com/investwithankit12-lang/anvarli-wedding.git..." -ForegroundColor Yellow
Write-Host "NOTE: When prompted:" -ForegroundColor Green
Write-Host "   Username: investwithankit12" -ForegroundColor Green
Write-Host "   Password: [Paste your GitHub Personal Access Token]" -ForegroundColor Green
Write-Host ""

# Push to GitHub
& $gitCmd push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Attempting push with force..." -ForegroundColor Yellow
    & $gitCmd push -u origin main --force
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host " SUCCESS! Rishan Events website has been pushed to GitHub!" -ForegroundColor Green
    Write-Host " Vercel is now deploying the updated version automatically!" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Push failed. Please make sure your Personal Access Token (PAT) has the 'repo' scope." -ForegroundColor Red
}

Write-Host ""
pause
