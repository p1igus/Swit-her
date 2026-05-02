#!/bin/bash
# postinstall.sh — скрипт, который запускается после установки PKG
# Снимает карантин с установленного приложения

set -e

APP_NAME="Swit-her.app"
INSTALL_DIR="/Applications"
INSTALL_PATH="$INSTALL_DIR/$APP_NAME"

echo "Снимаем карантин с $INSTALL_PATH..."
xattr -rd com.apple.quarantine "$INSTALL_PATH" 2>/dev/null || true

echo "Установка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Открой Системные настройки → Конфиденциальность и безопасность → Универсальный доступ"
echo "2. Нажми '+' и выбери Swit-her из папки Applications"
echo "3. Запусти Swit-her"
echo ""
echo "Готово! Нажимай Option для переключения раскладки!"

exit 0
