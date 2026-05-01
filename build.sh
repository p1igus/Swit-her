#!/bin/bash
# build.sh — собирает Swit-her.app
# Запускать из папки swit-her/

set -e

echo "=== Swit-her — сборка .app ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-build"

echo "🐍 Создаём виртуальное окружение..."
rm -rf "$VENV_DIR"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Python: $(python --version)"
echo "Путь:   $(which python)"
echo ""

echo "📦 Устанавливаем зависимости..."
pip install --quiet --upgrade pip
pip install --quiet rumps pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz py2app

echo ""
echo "🔨 Собираем .app..."
rm -rf dist
python setup.py py2app 2>&1

deactivate
rm -rf "$VENV_DIR"

APP_NAME="Swit-her.app"
DMG_NAME="Swit-her"

sign_app() {
    echo ""
    echo "🔏 Подписываем приложение..."
    codesign -s - "dist/${APP_NAME}" 2>/dev/null || echo "⚠️  Ad-hoc подпись применена"
}

fix_info_plist() {
    echo ""
    echo "🔧 Исправляем Info.plist..."
    local plist="dist/${APP_NAME}/Contents/Info.plist"
    /usr/bin/defaults delete "$plist" PythonInfoDict 2>/dev/null || true
    echo "✅ Info.plist исправлен"
}

fix_libraries() {
    echo ""
    echo "📚 Копируем недостающие библиотеки..."
    local frameworks="dist/${APP_NAME}/Contents/Frameworks"

    local libffi_src=""
    for candidate in "/Users/pligus/anaconda3/lib/libffi.8.dylib" "/opt/homebrew/opt/libffi/lib/libffi.8.dylib" "/usr/local/opt/libffi/lib/libffi.8.dylib"; do
        if [ -f "$candidate" ]; then
            libffi_src="$candidate"
            break
        fi
    done

    if [ -n "$libffi_src" ] && [ ! -f "$frameworks/libffi.8.dylib" ]; then
        cp "$libffi_src" "$frameworks/"
        install_name_tool -id "@rpath/libffi.8.dylib" "$frameworks/libffi.8.dylib"
        echo "✅ libffi.8.dylib скопирован из $libffi_src"
    elif [ -f "$frameworks/libffi.8.dylib" ]; then
        echo "✅ libffi.8.dylib уже есть"
    else
        echo "⚠️  libffi.8.dylib не найден, приложение может не запуститься"
    fi

    local libffi_dylib="dist/${APP_NAME}/Contents/Resources/lib/python3.11/lib-dynload/_ctypes.so"
    if [ -f "$libffi_dylib" ]; then
        install_name_tool -change "@rpath/libffi.8.dylib" "@executable_path/../Frameworks/libffi.8.dylib" "$libffi_dylib"
        echo "✅ _ctypes.so теперь ссылается на Frameworks/libffi.8.dylib"
    fi
}

fix_and_resign() {
    fix_info_plist
    fix_libraries
    echo ""
    echo "🔏 Переподписываем приложение..."
    codesign -s - "dist/${APP_NAME}" 2>/dev/null || echo "⚠️  Ad-hoc подпись применена"
}

create_dmg() {
    echo ""
    echo "📦 Создаём .dmg..."

    local dmg_final="dist/${DMG_NAME}.dmg"
    local dmg_dir="/tmp/${DMG_NAME}-dmg"
    local vol_name="${DMG_NAME}"

    rm -f "$dmg_final"
    rm -rf "$dmg_dir"

    mkdir "$dmg_dir"
    cp -r "dist/${APP_NAME}" "$dmg_dir/"
    ln -s /Applications "$dmg_dir/Applications"

    hdiutil create -srcfolder "$dmg_dir" \
        -volname "$vol_name" \
        -fs HFS+ \
        -format UDZO \
        -imagekey zlib-level=9 \
        -ov \
        "$dmg_final" \
        > /dev/null 2>&1

    rm -rf "$dmg_dir"

    echo "✅ DMG: dist/${DMG_NAME}.dmg"
}

if [ -d "dist/$APP_NAME" ]; then
    fix_and_resign
    create_dmg
    echo ""
    echo "📋 Инструкции для пользователя:"
    echo ""
    echo "1. Открой dist/${DMG_NAME}.dmg"
    echo ""
    echo "2. Перетащи ${APP_NAME} на иконку 'Applications' слева в окне DMG"
    echo "   (или перетащи на папку /Applications в Finder)"
    echo ""
    echo "3. При первом запуске macOS может показать предупреждение:"
    echo "   'Приложение повреждено' → нажми ОК, затем в Терминале выполни:"
    echo "   xattr -rd com.apple.quarantine /Applications/${APP_NAME}"
    echo ""
    echo "4. Выдай разрешение Accessibility:"
    echo "   Системные настройки → Конфиденциальность и безопасность"
    echo "   → Универсальный доступ → нажми '+' → выбери ${APP_NAME}"
    echo ""
    echo "5. Перезапусти ${APP_NAME}"
    echo ""
    echo "Готово! Нажимай Option для переключения раскладки!"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi