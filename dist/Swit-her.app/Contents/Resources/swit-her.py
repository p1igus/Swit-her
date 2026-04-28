#!/usr/bin/env python3
import sys, threading, time
import rumps, Quartz
from AppKit import NSPasteboard, NSStringPboardType, NSUserDefaults
from Quartz import CoreGraphics as CG

RU_EN = {
    'й':'q','ц':'w','у':'e','к':'r','е':'t','н':'y','г':'u','ш':'i','щ':'o','з':'p','х':'[','ъ':']',
    'ф':'a','ы':'s','в':'d','а':'f','п':'g','р':'h','о':'j','л':'k','д':'l','ж':';','э':"'",
    'я':'z','ч':'x','с':'c','м':'v','и':'b','т':'n','ь':'m','б':',','ю':'.', '.':'/',
    'Й':'Q','Ц':'W','У':'E','К':'R','Е':'T','Н':'Y','Г':'U','Ш':'I','Щ':'O','З':'P','Х':'{','Ъ':'}',
    'Ф':'A','Ы':'S','В':'D','А':'F','П':'G','Р':'H','О':'J','Л':'K','Д':'L','Ж':':','Э':'"',
    'Я':'Z','Ч':'X','С':'C','М':'V','И':'B','Т':'N','Ь':'M','Б':'<','Ю':'>',',':'?',
}
EN_RU = {v:k for k,v in RU_EN.items()}

def detect_layout(text):
    for ch in text:
        if ch in RU_EN: return 'ru'
        if ch in EN_RU: return 'en'
    return 'unknown'

def convert_text(text):
    layout = detect_layout(text)
    table = RU_EN if layout=='ru' else (EN_RU if layout=='en' else None)
    if not table: return text
    return ''.join(table.get(ch, ch) for ch in text)

def get_clipboard():
    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_(NSStringPboardType) or ''

def set_clipboard(text):
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSStringPboardType)

def send_key(keycode, flags=0):
    e = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
    if flags: Quartz.CGEventSetFlags(e, flags)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e)
    time.sleep(0.02)
    e2 = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e2)
    time.sleep(0.03)

CMD=Quartz.kCGEventFlagMaskCommand
OPT=Quartz.kCGEventFlagMaskAlternate
SHIFT=Quartz.kCGEventFlagMaskShift
_MARKER='\x03LS\x03'

def get_current_input_source():
    try:
        from AppKit import NSTextInputContext
        context = NSTextInputContext.currentInputContext()
        if context:
            source_id = context.selectedKeyboardInputSource()
            if source_id:
                return str(source_id)
    except:
        pass
    
    try:
        from CoreFoundation import TISCopyCurrentKeyboardInputSource, TISGetInputSourceProperty, kTISPropertyInputSourceID
        source = TISCopyCurrentKeyboardInputSource()
        if source:
            source_id = TISGetInputSourceProperty(source, kTISPropertyInputSourceID)
            if source_id:
                return str(source_id)
    except:
        pass
    
    return None

def switch_to_next_input_source():
    try:
        from CoreFoundation import TISSelectNextInputSource
        TISSelectNextInputSource()
        time.sleep(0.1)
    except:
        send_key(49, CMD)
        time.sleep(0.15)

def get_input_source_language(source_id=None):
    if source_id is None:
        source_id = get_current_input_source() or ''
    source_id = source_id.lower()
    if 'russian' in source_id or '.ru' in source_id:
        return 'ru'
    if any(x in source_id for x in ['us', 'abc', 'british', 'australian', 'english', 'ukelele']):
        return 'en'
    return None

def switch_to_target_language(target_lang, max_attempts=5):
    try:
        from CoreFoundation import TISSelectNextInputSource
        for _ in range(max_attempts):
            current_lang = get_input_source_language()
            if current_lang == target_lang:
                return
            TISSelectNextInputSource()
            time.sleep(0.15)
    except Exception:
        send_key(49, CMD)
        time.sleep(0.15)

def switch_input_source():
    switch_to_next_input_source()

def force_tsm_sync():
    """Форсирует TSM перечитать текущий источник ввода через Shift-tap"""
    e_down = Quartz.CGEventCreateKeyboardEvent(None, 56, True)
    Quartz.CGEventSetFlags(e_down, Quartz.kCGEventFlagMaskShift)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e_down)
    time.sleep(0.02)
    e_up = Quartz.CGEventCreateKeyboardEvent(None, 56, False)
    Quartz.CGEventSetFlags(e_up, 0)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, e_up)
    time.sleep(0.05)

def switch_layout():
    original = get_clipboard()
    set_clipboard(_MARKER)
    send_key(8, CMD); time.sleep(0.12)
    selected = get_clipboard()
    if not (selected and selected != _MARKER and selected.strip()):
        send_key(123, OPT|SHIFT); time.sleep(0.1)
        send_key(8, CMD); time.sleep(0.12)
        selected = get_clipboard()
    if not selected or selected == _MARKER or not selected.strip():
        set_clipboard(original)
        switch_input_source()
        return
    
    layout = detect_layout(selected)
    converted = convert_text(selected)
    
    if converted == selected:
        set_clipboard(original)
        switch_input_source()
        return
    
    target_lang = 'en' if layout == 'ru' else 'ru'
    
    set_clipboard(converted); time.sleep(0.05)
    send_key(9, CMD); time.sleep(0.08)
    set_clipboard(original)
    time.sleep(0.05)
    switch_to_target_language(target_lang)
    time.sleep(0.08)
    force_tsm_sync()

_last_trigger = 0.0
_tap_ok = False
_opt_was_pressed = False
_ctrl_was_pressed = False
_trigger_key = 'alt'

def set_trigger_key(key):
    global _trigger_key
    _trigger_key = key
    defaults = NSUserDefaults.standardUserDefaults()
    defaults.setObject_forKey_(key, 'LayoutSwitcherTriggerKey')
    defaults.synchronize()

def load_trigger_key():
    global _trigger_key
    defaults = NSUserDefaults.standardUserDefaults()
    saved = defaults.stringForKey_('LayoutSwitcherTriggerKey')
    if saved in ['alt', 'ctrl']:
        _trigger_key = saved

def event_callback(proxy, event_type, event, refcon):
    global _last_trigger, _opt_was_pressed, _ctrl_was_pressed
    
    if event_type == Quartz.kCGEventKeyDown:
        # Если нажата любая клавиша пока зажат модификатор - сбрасываем флаг
        if _opt_was_pressed:
            _opt_was_pressed = False
        if _ctrl_was_pressed:
            _ctrl_was_pressed = False
    
    elif event_type == Quartz.kCGEventFlagsChanged:
        flags = Quartz.CGEventGetFlags(event)
        is_opt_pressed = bool(flags & Quartz.kCGEventFlagMaskAlternate)
        is_ctrl_pressed = bool(flags & Quartz.kCGEventFlagMaskControl)
        has_cmd = bool(flags & Quartz.kCGEventFlagMaskCommand)
        has_shift = bool(flags & Quartz.kCGEventFlagMaskShift)
        
        if _trigger_key == 'alt':
            has_other_mods = has_cmd or is_ctrl_pressed or has_shift
            if is_opt_pressed and not has_other_mods:
                _opt_was_pressed = True
            elif is_opt_pressed and has_other_mods:
                _opt_was_pressed = False
            elif _opt_was_pressed and not is_opt_pressed and not has_other_mods:
                _opt_was_pressed = False
                now = time.time()
                if now - _last_trigger > 0.3:
                    _last_trigger = now
                    threading.Thread(target=switch_layout, daemon=True).start()
            elif not is_opt_pressed:
                _opt_was_pressed = False
        else:
            has_other_mods = has_cmd or is_opt_pressed or has_shift
            if is_ctrl_pressed and not has_other_mods:
                _ctrl_was_pressed = True
            elif is_ctrl_pressed and has_other_mods:
                _ctrl_was_pressed = False
            elif _ctrl_was_pressed and not is_ctrl_pressed and not has_other_mods:
                _ctrl_was_pressed = False
                now = time.time()
                if now - _last_trigger > 0.3:
                    _last_trigger = now
                    threading.Thread(target=switch_layout, daemon=True).start()
            elif not is_ctrl_pressed:
                _ctrl_was_pressed = False
    
    return event

def start_tap():
    global _tap_ok
    mask = (Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged) | 
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown))
    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
        0, mask, event_callback, None)
    if not tap:
        print("❌ Event Tap не создан — нет разрешения Accessibility")
        _tap_ok = False
        return
    _tap_ok = True
    print("✅ Event Tap создан")
    src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), src, Quartz.kCFRunLoopDefaultMode)
    Quartz.CGEventTapEnable(tap, True)
    Quartz.CFRunLoopRun()

class LayoutSwitcherApp(rumps.App):
    def __init__(self):
        super().__init__('⊷', quit_button='Выйти')
        load_trigger_key()
        self.key_alt = rumps.MenuItem('Alt (Option)', callback=self.set_alt)
        self.key_ctrl = rumps.MenuItem('Ctrl', callback=self.set_ctrl)
        self.update_checkmarks()
        self.menu = [
            rumps.MenuItem('Swit-her активен'), None,
            rumps.MenuItem('Переключить сейчас', callback=self.do_switch), None,
            rumps.MenuItem('Клавиша переключения:'),
            self.key_alt,
            self.key_ctrl,
        ]
        self._timer = rumps.Timer(self.check_tap, 1)
        self._timer.start()

    def update_checkmarks(self):
        self.key_alt.state = 1 if _trigger_key == 'alt' else 0
        self.key_ctrl.state = 1 if _trigger_key == 'ctrl' else 0

    def set_alt(self, _):
        set_trigger_key('alt')
        self.update_checkmarks()

    def set_ctrl(self, _):
        set_trigger_key('ctrl')
        self.update_checkmarks()

    def check_tap(self, t):
        t.stop()
        if not _tap_ok:
            from AppKit import NSAlert
            alert = NSAlert.alloc().init()
            alert.setMessageText_('Swit-her — нет доступа')
            alert.setInformativeText_(
                'Открой: Системные настройки → Конфиденциальность\n'
                '→ Универсальный доступ\n'
                'Добавь Swit-her.app и включи переключатель.\n'
                'Затем перезапусти приложение.')
            alert.runModal()

    def do_switch(self, _):
        threading.Thread(target=switch_layout, daemon=True).start()

if __name__ == '__main__':
    threading.Thread(target=start_tap, daemon=True).start()
    time.sleep(0.5)
    LayoutSwitcherApp().run()
