#!/bin/bash
# build.sh — собирает Swit-her.app
# Запускать из папки swit-her/

set -e

echo "=== Swit-her — сборка .app ==="
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
APP_NAME="Swit-her.app"
if [ -d "dist/$APP_NAME" ]; then
echo "✅ Готово: dist/$APP_NAME"
echo ""
echo "Следующие шаги:"
echo ""
echo "1. Скопируй в /Applications:"
echo " cp -r dist/$APP_NAME /Applications/"
    echo ""
echo "2. Запусти приложение:"
echo " open /Applications/Swit-her.app"
echo ""
echo "3. Выдай разрешение Accessibility:"
echo " Системные настройки → Конфиденциальность и безопасность"
echo " → Универсальный доступ → нажми '+' → выбери Swit-her.app"
echo ""
echo "4. Перезапусти Swit-her.app"
    echo ""
    echo "После этого нажимай Option для переключения раскладки!"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi
