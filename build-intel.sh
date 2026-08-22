#!/bin/bash
# build-intel.sh — собирает Swit-her.app для Intel Mac (macOS 10.15 Catalina+)
# Запускать из папки swit-her/

set -e

echo "=== Swit-her — сборка для Intel Mac (macOS 10.15+) ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv-build-intel"
DIST_DIR="dist-intel"

echo "🐍 Создаём виртуальное окружение x86_64..."
rm -rf "$VENV_DIR" "$DIST_DIR"
arch -x86_64 /usr/bin/python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Python: $(python --version) ($(arch))"
echo "Путь:   $(which python)"
echo ""

echo "📦 Устанавливаем зависимости..."
pip install --quiet --upgrade pip
pip install --quiet rumps pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz py2app

echo ""
echo "🔨 Собираем .app с целевой версией macOS 10.15+..."
export MACOSX_DEPLOYMENT_TARGET=10.15
export ARCHFLAGS="-arch x86_64"
python setup.py py2app --dist-dir "$DIST_DIR" 2>&1

deactivate
rm -rf "$VENV_DIR"

APP_NAME="Swit-her.app"
DMG_NAME="Swit-her-Intel"

fix_info_plist() {
    echo ""
    echo "🔧 Исправляем Info.plist..."
    local plist="${DIST_DIR}/${APP_NAME}/Contents/Info.plist"
    /usr/bin/defaults delete "$plist" PythonInfoDict 2>/dev/null || true
    echo "✅ Info.plist исправлен"
}

remove_pyc_files() {
    echo ""
    echo "🧹 Удаляем .pyc файлы..."
    find "${DIST_DIR}/${APP_NAME}" -name "*.pyc" -delete 2>/dev/null || true
    echo "✅ .pyc файлы удалены"
}

sign_app() {
    echo ""
    echo "🔏 Удаляем старую подпись..."
    codesign --remove-signature "${DIST_DIR}/${APP_NAME}" 2>/dev/null || true
    
    echo "🔏 Подписываем приложение заново..."
    if codesign --force --deep -s - "${DIST_DIR}/${APP_NAME}" 2>/dev/null; then
        echo "✅ Подпись применена"
    else
        echo "⚠️  Ошибка подписи"
    fi
}

create_pkg() {
    echo ""
    echo "📦 Создаём .pkg для Intel Mac..."

    local pkg_final="dist/${DMG_NAME}.pkg"
    local pkg_root="/tmp/${DMG_NAME}-pkg-root"
    local pkg_scripts="/tmp/${DMG_NAME}-pkg-scripts"
    local pkg_component="/tmp/${DMG_NAME}-component.pkg"

    mkdir -p dist
    # Очищаем временные файлы
    rm -rf "$pkg_root" "$pkg_scripts" "$pkg_component" "$pkg_final"

    # Создаём структуру для PKG
    mkdir -p "$pkg_root/Applications" "$pkg_scripts"

    # Копируем приложение и скрипты
    cp -R "${DIST_DIR}/${APP_NAME}" "$pkg_root/Applications/"
    cp postinstall.sh "$pkg_scripts/postinstall"
    chmod +x "$pkg_scripts/postinstall"

    # Создаём component PKG
    pkgbuild --root "$pkg_root" \
        --scripts "$pkg_scripts" \
        --identifier "com.user.swither.intel" \
        --version "1.0.2" \
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
    echo "📦 Создаём .dmg для Intel Mac..."

    local dmg_final="dist/${DMG_NAME}.dmg"
    local dmg_dir="/tmp/${DMG_NAME}-dmg"
    local vol_name="${DMG_NAME}"

    mkdir -p dist
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
    rm -rf "$DIST_DIR"

    echo "✅ DMG: dist/${DMG_NAME}.dmg"
}

if [ -d "${DIST_DIR}/$APP_NAME" ]; then
    fix_info_plist
    remove_pyc_files
    sign_app
    create_pkg
    create_dmg
    echo ""
    echo "📋 Готово! Создан установщик для Intel Mac (macOS 10.15+):"
    echo "• dist/${DMG_NAME}.dmg"
    echo "• dist/${DMG_NAME}.pkg"
else
    echo "❌ Сборка не удалась. Смотри ошибки выше."
fi
