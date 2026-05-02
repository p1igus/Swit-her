"""
setup.py для сборки Layout Switcher как .app через py2app.

Запуск:
    python setup.py py2app
"""

from setuptools import setup

APP = ['swit-her.py']

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'switcher.png',
    'plist': {
        'CFBundleName': 'Swit-her',
        'CFBundleDisplayName': 'Swit-her',
        'CFBundleIdentifier': 'com.user.swither',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0',
        'LSUIElement': True,
        'NSAppleEventsUsageDescription': 'Swit-her нужен доступ для переключения раскладки.',
    },
    'packages': ['rumps'],
    'includes': [
        'AppKit',
        'Quartz',
        'CoreFoundation',
    ],
    'frameworks': [],
    'excludes': ['tkinter', 'test', 'unittest'],
    'strip': False,
}

setup(
    name='Swit-her',
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)