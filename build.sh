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

APP_NAME="Swit-her.app"
DMG_NAME="Swit-her"

create_dmg() {
    echo ""
    echo "📦 Создаём .dmg..."

    local dmg_temp="/tmp/${DMG_NAME}-temp.dmg"
    local dmg_final="dist/${DMG_NAME}.dmg"
    local source_dir="dist"
    local vol_name="${DMG_NAME}"

    rm -f "$dmg_temp" "$dmg_final"

    hdiutil create "$dmg_temp" \
        -volname "$vol_name" \
        -fs HFS+ \
        -fsargs "-c c=64,a=16,e=16" \
        -format UDRW \
        -size 100M \
        > /dev/null 2>&1

    local dev_entry=$(hdiutil attach -readwrite -noverify -noautoopen "$dmg_temp" 2>&1 | grep -E '/dev/disk[0-9]+' | head -1 | awk '{print $1}')

    sleep 0.5

    cp -r "$source_dir/${APP_NAME}" "/Volumes/${vol_name}/"

    bless --folder "/Volumes/${vol_name}" --openfolder "$source_dir"

    hdiutil detach "$dev_entry" > /dev/null 2>&1

    hdiutil convert "$dmg_temp" -format UDZO -imagekey zlib-level=9 -o "$dmg_final" > /dev/null 2>&1

    rm -f "$dmg_temp"

    echo "✅ DMG: dist/${DMG_NAME}.dmg"
}

if [ -d "dist/$APP_NAME" ]; then
    create_dmg
    echo ""
    echo "Следующие шаги:"
    echo ""
    echo "1. Открой DMG и перетащи ${APP_NAME} в Applications:"
    echo "   open dist/${DMG_NAME}.dmg"
    echo ""
    echo "2. Выдай разрешение Accessibility:"
    echo "   Системные настройки → Конфиденциальность и безопасность"
    echo "   → Универсальный доступ → нажми '+' → выбери Swit-her.app"
    echo ""
    echo "3. Перезапусти Swit-her.app"
    echo ""
    echo "После этого нажимай Option для переключения раскладки!"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi
