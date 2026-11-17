#!/usr/bin/env bash
# ==============================================================================
# Git Flow Setup Script - Calculadora RTC RFB Free Suite PY
# Configura as branches obrigatórias: main, originals, development, staging
# ==============================================================================
set -euo pipefail

echo ">> Inicializando repositório Git com branch padrão 'main'..."
git init -b main

# Commit inicial base (README / .gitignore)
git add .gitignore .env.example references/README.md
git commit -m "chore: initial monorepo structure"

echo ">> Criando branch 'originals' para os fontes oficiais da Receita Federal..."
git checkout -b originals

# Opcional: Clonar os repositórios oficiais da RFB dentro de references/ (sem .git interno)
clone_ref() {
  local repo_url="$1"
  local target_dir="$2"
  echo ">> Importando referência oficial: $repo_url -> $target_dir"
  rm -rf "$target_dir"
  git clone --depth 1 "$repo_url" "$target_dir"
  rm -rf "$target_dir/.git"
}

if [[ "${IMPORT_RFB_REPOS:-false}" == "true" ]]; then
  clone_ref "https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional.git" "references/simples"
  clone_ref "https://github.com/ReceitaFederal/calculadora-rtc-regime-regular.git" "references/regime-regular"
  clone_ref "https://github.com/ReceitaFederal/calculadora-rtc-gerador-danfse.git" "references/danfse"
  git add references/
  git commit -m "chore(originals): import official RFB reference repositories"
else
  git add references/
  git commit -m "chore(originals): initialize references directory structure"
fi

echo ">> Criando branch 'development' a partir de 'main'..."
git checkout main
git checkout -b development
git add .
git commit -m "feat: bootstrap Python/FastAPI backend, modular frontend and Docker suite"

echo ">> Criando branch 'staging' a partir de 'development'..."
git checkout -b staging

echo ">> Retornando para a branch ativa 'development'..."
git checkout development

echo ">> Branches configuradas:"
git branch -a

