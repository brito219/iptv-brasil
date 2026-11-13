#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

git pull --quiet
python3 curate.py
git add --all

if git diff --cached --quiet; then
    echo "sem mudancas"
    exit 0
fi

git commit --quiet --message "chore: atualiza lista ($(date +%F))"
git push --quiet origin main
echo "lista atualizada e publicada"
