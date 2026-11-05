Write-Host "=== Deployment Setup Script for Anvarli Event Managers Website ==="

# 1. Ensure Git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed. Please install Git for Windows before proceeding."
    exit 1
}

# 2. Initialize a new Git repository if not already initialized
if (-not (Test-Path ".git")) {
    git init
    Write-Host "Initialized a new Git repository."
} else {
    Write-Host "Git repository already initialized."
}

# 3. Create .gitignore (if missing)
$gitignorePath = Join-Path (Get-Location) ".gitignore"
if (-not (Test-Path $gitignorePath)) {
    @(
        "# Python caches"
        "__pycache__/"
        "*.pyc"
        "*.pyo"
        "*.pyd"
        "*.env"
        "venv/"
        "env/"
        "*.sqlite3"
        "wedding.db"
        "# Node / npm artifacts (not used but safe)"
        "node_modules/"
        "# OS files"
        "Thumbs.db"
        "Desktop.ini"
        "# Uploads folder (keep empty placeholder)"
        "assets/uploads/"
    ) | Set-Content -Encoding UTF8 $gitignorePath
    Write-Host ".gitignore created."
} else {
    Write-Host ".gitignore already exists."
}

# 4. Install Python dependencies (use a virtual environment)
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "Virtual environment created."
}
# Activate venv
$activateScript = "venv\\Scripts\\Activate.ps1"
if (Test-Path $activateScript) {
    . $activateScript
    Write-Host "Virtual environment activated."
} else {
    Write-Error "Could not find activation script for virtual environment."
    exit 1
}
# Upgrade pip and install requirements
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
    Write-Host "Python dependencies installed."
} else {
    Write-Warning "requirements.txt not found – skipping Python package install."
}

# 5. Prepare environment variables
# Copy .env.example to .env (user must fill in values)
if (Test-Path ".env.example") {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host ".env file created from template – please edit it with your Supabase credentials and any other secrets."
    } else {
        Write-Host ".env already exists."
    }
} else {
    Write-Warning ".env.example not found – ensure you create a .env file manually."
}

# 6. Seed Supabase admin user (requires Supabase credentials in .env)
if (Test-Path "seed_supabase_admin.py") {
    Write-Host "Seeding admin user in Supabase…"
    python seed_supabase_admin.py
} else {
    Write-Warning "seed_supabase_admin.py not found – skip admin seeding."
}

# 7. Commit and push to GitHub
# Prompt the user for repository URL
$repoUrl = Read-Host "Enter your GitHub repository HTTPS URL (e.g., https://github.com/username/repo.git)"
if ($repoUrl) {
    git add .
    git commit -m "Initial commit – ready for Vercel deployment"
    git remote add origin $repoUrl
    git branch -M main
    git push -u origin main
    Write-Host "Code pushed to GitHub."
} else {
    Write-Warning "No repository URL provided – skipping push."
}

# 8. Vercel deployment (requires Vercel CLI and login)
Write-Host "--- Optional Vercel Deployment ---"
if (Get-Command vercel -ErrorAction SilentlyContinue) {
    Write-Host "Vercel CLI is installed."
    $vercelLogin = Read-Host "Do you want to deploy now with Vercel CLI? (y/n)"
    if ($vercelLogin -eq 'y') {
        # Ensure Vercel project is linked or create a new one
        vercel link || vercel
        # Set required environment variables on Vercel (you can also set them via dashboard)
        Write-Host "Make sure to add SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_STORAGE_BUCKET to your Vercel project environment variables."
        # Deploy
        vercel --prod
    } else {
        Write-Host "You can deploy later via the Vercel dashboard by importing the GitHub repository."
    }
} else {
    Write-Warning "Vercel CLI not found. Install it with: npm i -g vercel (requires Node.js)."
}

Write-Host "=== Setup complete. Follow any remaining manual steps described in README.md. ==="
