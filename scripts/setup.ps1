#Requires -Version 5.1
<#
.SYNOPSIS
    skill-mcp — one-shot first-time setup for Windows (PowerShell)

.DESCRIPTION
    Checks prerequisites, initialises .env, installs Python deps,
    seeds Qdrant, pushes Worker secrets, and deploys — in order.
    Run from the project root:  .\scripts\setup.ps1

.NOTES
    Prerequisites: Python 3.11+, Node.js 18+ (for wrangler), pip
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step { param([string]$msg) Write-Host "`n[setup] $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  OK  $msg"   -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  WARN $msg"  -ForegroundColor Yellow }
function Write-Fail { param([string]$msg) Write-Host "  FAIL $msg"  -ForegroundColor Red; exit 1 }

# ── Step 1 — Prerequisite checks ──────────────────────────────────────────────

Write-Step "Checking prerequisites ..."

try   { $py = python --version 2>&1; Write-OK "Python: $py" }
catch { Write-Fail "Python 3.11+ is required. Install from https://python.org" }

$pyVer = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>&1)
if ([version]$pyVer -lt [version]"3.11") {
    Write-Fail "Python 3.11+ required (found $pyVer). Upgrade from https://python.org"
}

try   { $node = node --version 2>&1; Write-OK "Node.js: $node" }
catch { Write-Fail "Node.js 18+ is required for wrangler. Install from https://nodejs.org" }

try   { npx wrangler --version 2>&1 | Out-Null; Write-OK "wrangler: available via npx" }
catch { Write-Fail "Cannot run 'npx wrangler'. Ensure Node.js is installed correctly." }

# ── Step 2 — Initialise .env ──────────────────────────────────────────────────

Write-Step "Setting up .env ..."

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Warn "Created .env from .env.example"
    Write-Host ""
    Write-Host "  Please fill in the following values in .env now:" -ForegroundColor Yellow
    Write-Host "    QDRANT_URL           — Qdrant Cloud cluster URL"
    Write-Host "    QDRANT_API_KEY       — Qdrant Cloud API key"
    Write-Host "    WORKERS_AI_ACCOUNT_ID — Cloudflare account ID"
    Write-Host "    WORKERS_AI_API_TOKEN  — Cloudflare API token (Workers AI Run permission)"
    Write-Host ""
    $resp = Read-Host "  Press ENTER when you have saved .env, or type 'skip' to continue anyway"
} else {
    Write-OK ".env already exists"
}

# ── Step 3 — Verify .env values ───────────────────────────────────────────────

Write-Step "Verifying .env values ..."

$required = @(
    @{ Key = "QDRANT_URL";            Desc = "Qdrant Cloud cluster URL" },
    @{ Key = "QDRANT_API_KEY";        Desc = "Qdrant Cloud API key" },
    @{ Key = "WORKERS_AI_ACCOUNT_ID"; Desc = "Cloudflare account ID" },
    @{ Key = "WORKERS_AI_API_TOKEN";  Desc = "Cloudflare API token" }
)

# Load .env manually (dotenv not yet installed)
$envVars = @{}
Get-Content ".env" | Where-Object { $_ -match "^\s*([^#=]+)=(.*)$" } | ForEach-Object {
    $parts = $_ -split "=", 2
    $envVars[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
}

$missing = @()
foreach ($r in $required) {
    if (-not $envVars.ContainsKey($r.Key) -or -not $envVars[$r.Key]) {
        $missing += "  • $($r.Key)  —  $($r.Desc)"
    }
}
if ($missing.Count -gt 0) {
    Write-Host "`n  Missing required values in .env:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host $_ }
    Write-Warn "Continuing anyway — seed and deploy may fail without these values."
} else {
    Write-OK "All required .env values are present"
}

# ── Step 4 — Install Python dependencies ──────────────────────────────────────

Write-Step "Installing Python dependencies (requirements.txt) ..."
python -m pip install -r requirements.txt --quiet
Write-OK "Python dependencies installed"

# ── Step 5 — Seed Qdrant ──────────────────────────────────────────────────────

Write-Step "Seeding Qdrant collections ..."
Write-Host "  (This embeds skill descriptors via Cloudflare Workers AI and upserts to Qdrant.)" -ForegroundColor Gray
python -m skill_mcp.seed.seed_skills
Write-OK "Qdrant seeding complete"

# ── Step 6 — Deploy to Cloudflare Workers ────────────────────────────────────

Write-Step "Deploying to Cloudflare Workers ..."
npx wrangler deploy
Write-OK "Worker deployed"

# ── Step 7 — Push secrets to Worker ──────────────────────────────────────────

Write-Step "Pushing secrets to Cloudflare Worker ..."

if ($envVars.ContainsKey("QDRANT_URL") -and $envVars["QDRANT_URL"]) {
    $envVars["QDRANT_URL"] | npx wrangler secret put QDRANT_URL
    Write-OK "QDRANT_URL secret set"
} else {
    Write-Warn "QDRANT_URL not found in .env — set manually: npx wrangler secret put QDRANT_URL"
}

if ($envVars.ContainsKey("QDRANT_API_KEY") -and $envVars["QDRANT_API_KEY"]) {
    $envVars["QDRANT_API_KEY"] | npx wrangler secret put QDRANT_API_KEY
    Write-OK "QDRANT_API_KEY secret set"
} else {
    Write-Warn "QDRANT_API_KEY not found in .env — set manually: npx wrangler secret put QDRANT_API_KEY"
}

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ✓ skill-mcp setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Your Worker is live. Add this to your MCP client config:" -ForegroundColor Cyan
Write-Host '  { "skill-mcp": { "type": "sse", "url": "https://skill-mcp.<your-subdomain>.workers.dev/sse" } }' -ForegroundColor White
Write-Host ""
Write-Host "  Local server (for script execution):" -ForegroundColor Cyan
Write-Host '  $env:MCP_TRANSPORT="streamable-http"; python -m skill_mcp.server' -ForegroundColor White
Write-Host ""
