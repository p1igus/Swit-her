#!/bin/bash
# install.sh — устанавливает зависимости и запускает Layout Switcher

set -e

echo "=== Layout Switcher — установка ==="

# Проверяем Python 3
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 не найден. Установи через: brew install python"
    exit 1
fi

PYTHON=$(command -v python3)
echo "✅ Python: $($PYTHON --version)"

# Проверяем pip
if ! $PYTHON -m pip --version &>/dev/null; then
    echo "❌ pip не найден"
    exit 1
fi

echo ""
echo "📦 Устанавливаем pyobjc..."
$PYTHON -m pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz --quiet

echo ""
echo "✅ Зависимости установлены."
echo ""
echo "⚠️  ВАЖНО: перед первым запуском нужно выдать разрешение на Accessibility:"
echo "   Системные настройки → Конфиденциальность и безопасность → Универсальный доступ"
echo "   → нажми '+' и добавь Terminal.app (или iTerm2)"
echo ""
echo "🚀 Запускаем..."
echo ""

$PYTHON "$(dirname "$0")/layout_switcher.py"
