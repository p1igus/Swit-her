#!/usr/bin/env python3
import importlib.util
import sys
import types
from pathlib import Path


def load_app():
    rumps = types.ModuleType('rumps')
    rumps.App = object
    quartz = types.ModuleType('Quartz')
    quartz.CoreGraphics = types.SimpleNamespace()
    quartz.kCGEventFlagMaskCommand = 1
    quartz.kCGEventFlagMaskAlternate = 2
    quartz.kCGEventFlagMaskShift = 4
    quartz.kCGEventFlagMaskControl = 8
    appkit = types.ModuleType('AppKit')
    appkit.NSPasteboard = appkit.NSUserDefaults = appkit.NSStringPboardType = object()

    modules = {'rumps': rumps, 'Quartz': quartz, 'AppKit': appkit}
    previous = {name: sys.modules.get(name) for name in modules}
    sys.modules.update(modules)
    try:
        spec = importlib.util.spec_from_file_location('swit_her', Path(__file__).with_name('swit-her.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name, old_module in previous.items():
            if old_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old_module


class FakeTime:
    now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, delay):
        self.now += delay


def test_delayed_copy_is_retried(app):
    copied = [None, 'n', 'tn', 'dtn', 'bdtn', 'hbdtn', 'ghbdtn', ' ghbdtn']
    attempt = -1
    keys = []

    def set_clipboard(_):
        nonlocal attempt
        attempt += 1

    app.time = FakeTime()
    app.set_clipboard = set_clipboard
    app.get_clipboard = lambda: app._MARKER if copied[attempt] is None else copied[attempt]
    app.send_key = lambda keycode, flags=0, delay=0: keys.append((keycode, flags))

    selected = app.select_token_left()
    assert selected == 'ghbdtn'
    assert app.convert_text(selected) == 'привет'
    assert keys.count((123, app.SHIFT)) == 7


def test_failed_copy_clears_temporary_selection(app):
    keys = []
    app.time = FakeTime()
    app.set_clipboard = lambda _: None
    app.get_clipboard = lambda: app._MARKER
    app.send_key = lambda keycode, flags=0, delay=0: keys.append((keycode, flags))

    assert app.select_token_left() == ''
    assert keys[-1] == (124, 0)


if __name__ == '__main__':
    app = load_app()
    test_delayed_copy_is_retried(app)
    test_failed_copy_clears_temporary_selection(app)
    print('ok')
