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

    # Поиск libffi.8.dylib в стандартных местах
    local libffi_src=""
    local candidates=(
        "/Users/pligus/anaconda3/lib/libffi.8.dylib"
        "/opt/homebrew/opt/libffi/lib/libffi.8.dylib"
        "/usr/local/opt/libffi/lib/libffi.8.dylib"
    )
    
    for candidate in "${candidates[@]}"; do
        if [ -f "$candidate" ]; then
            libffi_src="$candidate"
            break
        fi
    done

    # Копируем libffi если найден
    if [ -n "$libffi_src" ]; then
        if [ ! -f "$frameworks/libffi.8.dylib" ]; then
            cp "$libffi_src" "$frameworks/"
            install_name_tool -id "@rpath/libffi.8.dylib" "$frameworks/libffi.8.dylib"
            echo "✅ libffi.8.dylib скопирован из $libffi_src"
        else
            echo "✅ libffi.8.dylib уже есть"
        fi
    else
        echo "⚠️  libffi.8.dylib не найден, приложение может не запуститься"
    fi

    # Исправляем ссылку в _ctypes.so
    local ctypes_so="dist/${APP_NAME}/Contents/Resources/lib/python3.11/lib-dynload/_ctypes.so"
    if [ -f "$ctypes_so" ]; then
        install_name_tool -change "@rpath/libffi.8.dylib" "@executable_path/../Frameworks/libffi.8.dylib" "$ctypes_so"
        echo "✅ _ctypes.so теперь ссылается на Frameworks/libffi.8.dylib"
    fi
}

remove_pyc_files() {
    echo ""
    echo "🧹 Удаляем .pyc файлы..."
    find "dist/${APP_NAME}" -name "*.pyc" -delete 2>/dev/null || true
    echo "✅ .pyc файлы удалены"
}

sign_app() {
    echo ""
    echo "🔏 Удаляем старую подпись..."
    codesign --remove-signature "dist/${APP_NAME}" 2>/dev/null || true
    
    echo "🔏 Подписываем приложение заново..."
    if codesign --force --deep -s - "dist/${APP_NAME}" 2>/dev/null; then
        echo "✅ Подпись применена"
    else
        echo "⚠️  Ошибка подписи"
    fi
}

create_pkg() {
    echo ""
    echo "📦 Создаём .pkg..."

    local pkg_final="dist/${DMG_NAME}.pkg"
    local pkg_root="/tmp/${DMG_NAME}-pkg-root"
    local pkg_scripts="/tmp/${DMG_NAME}-pkg-scripts"
    local pkg_component="/tmp/${DMG_NAME}-component.pkg"

    # Очищаем временные файлы
    rm -rf "$pkg_root" "$pkg_scripts" "$pkg_component" "$pkg_final"

    # Создаём структуру для PKG
    mkdir -p "$pkg_root/Applications" "$pkg_scripts"

    # Копируем приложение и скрипты
    cp -R "dist/${APP_NAME}" "$pkg_root/Applications/"
    cp postinstall.sh "$pkg_scripts/postinstall"
    chmod +x "$pkg_scripts/postinstall"

    # Создаём component PKG
    pkgbuild --root "$pkg_root" \
        --scripts "$pkg_scripts" \
        --identifier "com.user.swither" \
        --version "1.0.1" \
        --install-location "/" \
        "$pkg_component" > /dev/null 2>&1

    # Создаём финальный PKG
    productbuild --package "$pkg_component" "$pkg_final" > /dev/null 2>&1

    # Очищаем временные файлы
    rm -rf "$pkg_root" "$pkg_scripts" "$pkg_component"

    echo "✅ PKG: dist/${DMG_NAME}.pkg"
}

create_dmg() {
    echo ""
    echo "📦 Создаём .dmg..."

    local dmg_final="dist/${DMG_NAME}.dmg"
    local dmg_dir="/tmp/${DMG_NAME}-dmg"
    local vol_name="${DMG_NAME}"

    # Очищаем старые файлы
    rm -f "$dmg_final"
    rm -rf "$dmg_dir"

    # Создаём структуру DMG
    mkdir "$dmg_dir"
    cp "dist/${DMG_NAME}.pkg" "$dmg_dir/"
    cp INSTALL.txt "$dmg_dir/"
    ln -s /Applications "$dmg_dir/Applications"

    # Создаём DMG
    hdiutil create -srcfolder "$dmg_dir" \
        -volname "$vol_name" \
        -fs HFS+ \
        -format UDZO \
        -imagekey zlib-level=9 \
        -ov \
        "$dmg_final" > /dev/null 2>&1

    # Очищаем временные файлы
    rm -rf "$dmg_dir"

    echo "✅ DMG: dist/${DMG_NAME}.dmg"
}

if [ -d "dist/$APP_NAME" ]; then
    fix_info_plist
    fix_libraries
    sign_app
    create_pkg
    create_dmg
    echo ""
    echo "📋 Инструкции для пользователя:"
    echo ""
    echo "1. Открой dist/${DMG_NAME}.dmg"
    echo "2. Дважды кликни на '${DMG_NAME}.pkg'"
    echo "3. Если macOS блокирует установку, кликни ПКМ → Открыть"
    echo "4. Следуй инструкциям установщика"
    echo ""
    echo "Готово! Нажимай Option для переключения раскладки!"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi