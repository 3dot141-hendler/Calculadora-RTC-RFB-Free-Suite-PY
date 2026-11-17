<#
.SYNOPSIS
    Git Flow Setup Script - Calculadora RTC RFB Free Suite PY
.DESCRIPTION
    Configura as branches obrigatórias: main, originals, development, staging.
    Use -ImportRfbRepos para clonar os códigos-fonte oficiais da RFB em references/ na branch originals.
#>
param(
    [switch]$ImportRfbRepos
)

$ErrorActionPreference = "Stop"

Write-Host ">> Inicializando repositório Git com branch padrão 'main'..." -ForegroundColor Cyan
git init -b main

git add .gitignore .env.example references/README.md
git commit -m "chore: initial monorepo structure"

Write-Host ">> Criando branch 'originals' para os fontes oficiais da Receita Federal..." -ForegroundColor Cyan
git checkout -b originals

function Import-ReferenceRepo {
    param([string]$RepoUrl, [string]$TargetDir)
    Write-Host ">> Importando referência oficial: $RepoUrl -> $TargetDir" -ForegroundColor Yellow
    if (Test-Path $TargetDir) { Remove-Item -Recurse -Force $TargetDir }
    git clone --depth 1 $RepoUrl $TargetDir
    if (Test-Path "$TargetDir\.git") { Remove-Item -Recurse -Force "$TargetDir\.git" }
}

if ($ImportRfbRepos) {
    Import-ReferenceRepo -RepoUrl "https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional.git" -TargetDir "references/simples"
    Import-ReferenceRepo -RepoUrl "https://github.com/ReceitaFederal/calculadora-rtc-regime-regular.git" -TargetDir "references/regime-regular"
    Import-ReferenceRepo -RepoUrl "https://github.com/ReceitaFederal/calculadora-rtc-gerador-danfse.git" -TargetDir "references/danfse"
    git add references/
    git commit -m "chore(originals): import official RFB reference repositories"
} else {
    git add references/
    git commit -m "chore(originals): initialize references directory structure"
}

Write-Host ">> Criando branch 'development' a partir de 'main'..." -ForegroundColor Cyan
git checkout main
git checkout -b development
git add .
git commit -m "feat: bootstrap Python/FastAPI backend, modular frontend and Docker suite"

Write-Host ">> Criando branch 'staging' a partir de 'development'..." -ForegroundColor Cyan
git checkout -b staging

Write-Host ">> Retornando para a branch ativa 'development'..." -ForegroundColor Cyan
git checkout development

Write-Host ">> Branches configuradas:" -ForegroundColor Green
git branch -a

