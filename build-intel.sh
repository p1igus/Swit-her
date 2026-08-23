#!/bin/bash
# build-intel.sh — собирает Swit-her.app для Intel Mac (macOS 10.15 Catalina и новее)
# Запускать из папки swit-her/

set -e

echo "=== Swit-her — сборка для Intel Mac (macOS 10.15+) ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CACHE_DIR="${SCRIPT_DIR}/.cache-intel-python"
PY_BIN="${CACHE_DIR}/python/bin/python3"
DIST_DIR="${SCRIPT_DIR}/dist-intel-build"
APP_NAME="Swit-her.app"
DMG_NAME="Swit-her-Intel"

# 1. Скачиваем автономный Python x86_64 с целевой версией macOS 10.9+
if [ ! -f "$PY_BIN" ]; then
    echo "📥 Загрузка автономного Python x86_64 (совместимого с macOS 10.15 Catalina)..."
    mkdir -p "$CACHE_DIR"
    curl -L -s "https://github.com/astral-sh/python-build-standalone/releases/download/20240415/cpython-3.11.9+20240415-x86_64-apple-darwin-install_only.tar.gz" | tar -xz -C "$CACHE_DIR"
    echo "✅ Python x86_64 загружен"
fi

echo "Python: $(arch -x86_64 "$PY_BIN" --version) (x86_64)"
echo ""

# 2. Устанавливаем необходимые зависимости
echo "📦 Устанавливаем зависимости..."
arch -x86_64 "$PY_BIN" -m pip install --quiet --upgrade pip
arch -x86_64 "$PY_BIN" -m pip install --quiet pillow rumps pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz pyinstaller

# 3. Собираем приложение через PyInstaller
echo ""
echo "🔨 Сборка приложения через PyInstaller..."
rm -rf "$DIST_DIR" build/Swit-her Swit-her.spec
arch -x86_64 "$PY_BIN" -m PyInstaller \
    --noconfirm \
    --windowed \
    --name "Swit-her" \
    --icon "switcher.png" \
    --osx-bundle-identifier "com.user.swither" \
    --distpath "$DIST_DIR" \
    swit-her.py > /dev/null 2>&1

rm -rf build/Swit-her Swit-her.spec

# 4. Настраиваем Info.plist
echo "🔧 Настраиваем Info.plist..."
local_plist="${DIST_DIR}/${APP_NAME}/Contents/Info.plist"
/usr/bin/plutil -replace LSUIElement -bool true "$local_plist"
/usr/bin/plutil -replace CFBundleShortVersionString -string "1.0.2" "$local_plist"
/usr/bin/plutil -replace CFBundleVersion -string "1.0.2" "$local_plist"
/usr/bin/plutil -replace NSAppleEventsUsageDescription -string "Swit-her нужен доступ для переключения раскладки." "$local_plist"
echo "✅ Info.plist настроен"

# 5. Подписываем приложение
echo ""
echo "🔏 Подписываем приложение..."
codesign --remove-signature "${DIST_DIR}/${APP_NAME}" 2>/dev/null || true
codesign --force --deep -s - "${DIST_DIR}/${APP_NAME}" 2>/dev/null || true
echo "✅ Подпись применена"

# 6. Создаём PKG
echo ""
echo "📦 Создаём .pkg для Intel Mac..."
mkdir -p dist
pkg_final="dist/${DMG_NAME}.pkg"
pkg_root="/tmp/${DMG_NAME}-pkg-root"
pkg_scripts="/tmp/${DMG_NAME}-pkg-scripts"
pkg_component="/tmp/${DMG_NAME}-component.pkg"

rm -rf "$pkg_root" "$pkg_scripts" "$pkg_component" "$pkg_final"
mkdir -p "$pkg_root/Applications" "$pkg_scripts"

cp -R "${DIST_DIR}/${APP_NAME}" "$pkg_root/Applications/"
cp postinstall.sh "$pkg_scripts/postinstall"
chmod +x "$pkg_scripts/postinstall"

pkgbuild --root "$pkg_root" \
    --scripts "$pkg_scripts" \
    --identifier "com.user.swither.intel" \
    --version "1.0.2" \
    --install-location "/" \
    "$pkg_component" > /dev/null 2>&1

productbuild --package "$pkg_component" "$pkg_final" > /dev/null 2>&1
rm -rf "$pkg_root" "$pkg_scripts" "$pkg_component"
echo "✅ PKG: dist/${DMG_NAME}.pkg"

# 7. Создаём DMG
echo ""
echo "📦 Создаём .dmg для Intel Mac..."
dmg_final="dist/${DMG_NAME}.dmg"
dmg_dir="/tmp/${DMG_NAME}-dmg"

rm -f "$dmg_final"
rm -rf "$dmg_dir"
mkdir "$dmg_dir"

cp "dist/${DMG_NAME}.pkg" "$dmg_dir/"
cp INSTALL.txt "$dmg_dir/"
ln -s /Applications "$dmg_dir/Applications"

hdiutil create -srcfolder "$dmg_dir" \
    -volname "${DMG_NAME}" \
    -fs HFS+ \
    -format UDZO \
    -imagekey zlib-level=9 \
    -ov \
    "$dmg_final" > /dev/null 2>&1

rm -rf "$dmg_dir" "$DIST_DIR" dist-installer
echo "✅ DMG: dist/${DMG_NAME}.dmg"

echo ""
echo "🎉 Сборка для Intel Mac (macOS 10.15+) готова!"
echo "• dist/${DMG_NAME}.dmg"
echo "• dist/${DMG_NAME}.pkg"
