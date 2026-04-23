#!/bin/bash
# build.sh — собирает LayoutSwitcher.app
# Запускать из папки layout_switcher/

set -e

echo "=== Layout Switcher — сборка .app ==="
echo ""

PYTHON=$(command -v python3)
echo "Python: $($PYTHON --version)"
echo "Путь:   $PYTHON"
echo ""

echo "📦 Устанавливаем зависимости..."
$PYTHON -m pip install --quiet rumps pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz py2app

echo ""
echo "🔨 Собираем .app..."
$PYTHON setup.py py2app 2>&1

echo ""
if [ -d "dist/LayoutSwitcher.app" ]; then
    echo "✅ Готово: dist/LayoutSwitcher.app"
    echo ""
    echo "Следующие шаги:"
    echo ""
    echo "1. Скопируй в /Applications:"
    echo "   cp -r dist/LayoutSwitcher.app /Applications/"
    echo ""
    echo "2. Запусти приложение:"
    echo "   open /Applications/LayoutSwitcher.app"
    echo ""
    echo "3. Выдай разрешение Accessibility:"
    echo "   Системные настройки → Конфиденциальность и безопасность"
    echo "   → Универсальный доступ → нажми '+' → выбери LayoutSwitcher.app"
    echo ""
    echo "4. Перезапусти LayoutSwitcher.app"
    echo ""
    echo "После этого нажимай Option для переключения раскладки!"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi
