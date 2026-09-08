#!/bin/bash
# Git Pre-commit Hook for Linux/macOS/Git Bash
echo "[Quality Gate] Running Architecture & Quality Checks..."
python scripts/check_all.py
if [ $? -ne 0 ]; then
    echo "[Quality Gate] Commit rejected due to quality check failures!"
    exit 1
fi
echo "[Quality Gate] All checks passed!"
exit 0

