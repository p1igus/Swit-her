#!/usr/bin/env python3
import sys, os, threading, time, traceback
import rumps, Quartz, objc
from AppKit import NSPasteboard, NSStringPboardType, NSUserDefaults

# Логирование ошибок для диагностики
LOG_PATH = os.path.expanduser('~/Library/Logs/Swit-her.log')

def log_error(msg, exc=None):
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            t = time.strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{t}] {msg}\n")
            if exc:
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) + "\n")
            f.flush()
    except Exception:
        pass

def global_excepthook(exctype, value, tb):
    log_error(f"Uncaught exception: {value}", value)
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_excepthook
if hasattr(threading, 'excepthook'):
    threading.excepthook = lambda args: log_error(f"Thread exception in {args.thread.name}: {args.exc_value}", args.exc_value)

# Константы для клавиш
CMD = Quartz.kCGEventFlagMaskCommand
OPT = Quartz.kCGEventFlagMaskAlternate
SHIFT = Quartz.kCGEventFlagMaskShift
CTRL = Quartz.kCGEventFlagMaskControl

# Маркер для буфера обмена
_MARKER = '\x03LS\x03'

# Таймауты (в секундах)
DEBOUNCE_TIMEOUT = 0.3
KEY_DELAY = 0.02
SELECTION_KEY_DELAY = 0.012
SELECTION_STEP_PAUSE = 0.008
CLIPBOARD_TIMEOUT = 0.12
SELECTION_COPY_ATTEMPTS = 3
PASTE_DELAY = 0.08
SWITCH_DELAY = 0.15
MAX_TOKEN_LENGTH = 128

# Таблицы конвертации раскладок
RU_EN = {
    'й':'q','ц':'w','у':'e','к':'r','е':'t','н':'y','г':'u','ш':'i','щ':'o','з':'p','х':'[','ъ':']',
    'ф':'a','ы':'s','в':'d','а':'f','п':'g','р':'h','о':'j','л':'k','д':'l','ж':';','э':"'",
    'я':'z','ч':'x','с':'c','м':'v','и':'b','т':'n','ь':'m','б':',','ю':'.', '.':'/',
    'Й':'Q','Ц':'W','У':'E','К':'R','Е':'T','Н':'Y','Г':'U','Ш':'I','Щ':'O','З':'P','Х':'{','Ъ':'}',
    'Ф':'A','Ы':'S','В':'D','А':'F','П':'G','Р':'H','О':'J','Л':'K','Д':'L','Ж':':','Э':'"',
    'Я':'Z','Ч':'X','С':'C','М':'V','И':'B','Т':'N','Ь':'M','Б':'<','Ю':'>',',':'^',
    'ё':'\\','Ё':'|','№':'#',
}
EN_RU = {v:k for k,v in RU_EN.items()}
EN_RU.update({
    '@':'"',  # Shift+2: @ → "
    '$':'%',  # Shift+4: $ → %
    '%':':',  # Shift+5: % → :
    '&':'.',  # Shift+7: & → .
    '*':';',  # Shift+8: * → ;
})

def detect_layout(text):
    ambiguous = set(RU_EN) & set(EN_RU)
    for ch in text:
        if ch in ambiguous:
            continue
        if ch in RU_EN:
            return 'ru'
        if ch in EN_RU:
            return 'en'
    return 'unknown'

def convert_text(text):
    layout = detect_layout(text)
    table = RU_EN if layout=='ru' else (EN_RU if layout=='en' else None)
    if not table: return text
    return ''.join(table.get(ch, ch) for ch in text)

def get_clipboard():
    with objc.autorelease_pool():
        pb = NSPasteboard.generalPasteboard()
        try:
            from AppKit import NSPasteboardTypeString
            content = pb.stringForType_(NSPasteboardTypeString)
            if content is not None:
                return content
        except Exception:
            pass
        return pb.stringForType_(NSStringPboardType) or ''

def set_clipboard(text):
    with objc.autorelease_pool():
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        try:
            from AppKit import NSPasteboardTypeString
            pb.setString_forType_(text, NSPasteboardTypeString)
        except Exception:
            pb.setString_forType_(text, NSStringPboardType)

def send_key(keycode, flags=0, delay=KEY_DELAY):
    """Отправляет нажатие и отпускание клавиши в сессионный поток событий"""
    try:
        e_down = Quartz.CGEventCreateKeyboardEvent(None, keycode, True)
        if flags:
            Quartz.CGEventSetFlags(e_down, flags)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, e_down)
        time.sleep(delay)
        
        e_up = Quartz.CGEventCreateKeyboardEvent(None, keycode, False)
        if flags:
            Quartz.CGEventSetFlags(e_up, flags)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, e_up)
        time.sleep(delay)
    except Exception as e:
        log_error(f"Error in send_key({keycode}): {e}", e)

def copy_selected_text(attempts=1):
    """Копирует выделение, повторяя попытку при задержке приложения."""
    for _ in range(attempts):
        set_clipboard(_MARKER)
        send_key(8, CMD, delay=SELECTION_KEY_DELAY)
        deadline = time.monotonic() + CLIPBOARD_TIMEOUT
        while time.monotonic() < deadline:
            candidate = get_clipboard()
            if candidate and candidate != _MARKER:
                return candidate
            time.sleep(0.005)
    return None

def select_token_left():
    """Выделяет непробельный фрагмент непосредственно слева от курсора посимвольно."""
    selected = ''
    while len(selected) < MAX_TOKEN_LENGTH:
        send_key(123, SHIFT, delay=SELECTION_KEY_DELAY)
        time.sleep(SELECTION_STEP_PAUSE)
        candidate = copy_selected_text(SELECTION_COPY_ATTEMPTS)

        if candidate is None:
            send_key(124, delay=KEY_DELAY)
            return ''
        if candidate == selected:
            return selected
        if candidate[:1].isspace():
            send_key(124, SHIFT, delay=SELECTION_KEY_DELAY)
            return candidate[1:]
        selected = candidate
    return selected

def select_word_left():
    """Надежно выделяет слово или токен непосредственно слева от курсора."""
    # 1. Быстрое атомарное выделение целого слова через Option + Shift + Left
    send_key(123, OPT | SHIFT, delay=SELECTION_KEY_DELAY)
    time.sleep(0.01)
    word = copy_selected_text(attempts=2)
    
    if word and word.strip():
        # Если слово выделено, проверяем, нет ли слева символов пунктуации раскладки
        selected = word
        punct_keys = set(",.;'[]/\\`~@#$%^&*")
        while len(selected) < MAX_TOKEN_LENGTH:
            send_key(123, SHIFT, delay=SELECTION_KEY_DELAY)
            time.sleep(0.005)
            candidate = copy_selected_text(attempts=1)
            if not candidate or candidate == selected:
                break
            if candidate[:1].isspace():
                send_key(124, SHIFT, delay=SELECTION_KEY_DELAY)
                return candidate[1:]
            if candidate[0] not in punct_keys and not candidate[0].isalnum():
                send_key(124, SHIFT, delay=SELECTION_KEY_DELAY)
                return candidate[1:]
            selected = candidate
        return selected

    # 2. Если Option + Shift + Left не сработал, используем посимвольный захват
    return select_token_left()

_carbon = None
_kTISPropertyInputSourceID = None

def _init_carbon():
    global _carbon, _kTISPropertyInputSourceID
    if _carbon is None:
        try:
            import ctypes
            _carbon = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Carbon.framework/Carbon')
            _carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
            _carbon.TISCopyCurrentKeyboardInputSource.argtypes = []
            _carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
            _carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            _carbon.TISCreateInputSourceList.restype = ctypes.c_void_p
            _carbon.TISCreateInputSourceList.argtypes = [ctypes.c_void_p, ctypes.c_bool]
            _carbon.TISSelectInputSource.restype = ctypes.c_int32
            _carbon.TISSelectInputSource.argtypes = [ctypes.c_void_p]
            _kTISPropertyInputSourceID = ctypes.c_void_p.in_dll(_carbon, 'kTISPropertyInputSourceID')
        except Exception as e:
            log_error(f"Error loading Carbon framework: {e}", e)
            _carbon = False

def get_current_input_source():
    _init_carbon()
    if _carbon:
        try:
            source = _carbon.TISCopyCurrentKeyboardInputSource()
            if source:
                prop = _carbon.TISGetInputSourceProperty(source, _kTISPropertyInputSourceID.value)
                if prop:
                    return str(objc.objc_object(c_void_p=prop))
        except Exception as e:
            log_error(f"Error getting current input source: {e}", e)
    return None

def switch_to_next_input_source():
    """Переключает на следующий источник ввода"""
    send_key(49, CMD)
    time.sleep(SWITCH_DELAY)

def get_input_source_language(source_id=None):
    if source_id is None:
        source_id = get_current_input_source() or ''
    source_id = source_id.lower()
    if 'russian' in source_id or '.ru' in source_id:
        return 'ru'
    if any(x in source_id for x in ['us', 'abc', 'british', 'australian', 'english', 'ukelele']):
        return 'en'
    return None

def switch_to_target_language(target_lang):
    """Переключает раскладку на целевой язык через Carbon TIS API"""
    _init_carbon()
    if _carbon:
        try:
            source_list_ref = _carbon.TISCreateInputSourceList(None, False)
            if source_list_ref:
                source_list = objc.objc_object(c_void_p=source_list_ref)
                for s in source_list:
                    s_ptr = objc.pyobjc_id(s)
                    prop = _carbon.TISGetInputSourceProperty(s_ptr, _kTISPropertyInputSourceID.value)
                    if prop:
                        sid = str(objc.objc_object(c_void_p=prop)).lower()
                        if target_lang == 'ru' and ('russian' in sid or '.ru' in sid):
                            _carbon.TISSelectInputSource(s_ptr)
                            return
                        elif target_lang == 'en' and any(x in sid for x in ['abc', 'us', 'british', 'australian', 'english', 'ukelele']):
                            _carbon.TISSelectInputSource(s_ptr)
                            return
        except Exception as e:
            log_error(f"Error switching input source via Carbon: {e}", e)
    # Запасной вариант переключения через горячую клавишу
    send_key(49, CMD)
    time.sleep(SWITCH_DELAY)

def switch_input_source():
    """Переключает на следующий источник ввода"""
    switch_to_next_input_source()

def force_tsm_sync():
    """Форсирует TSM перечитать текущий источник ввода через Shift-tap"""
    try:
        e_down = Quartz.CGEventCreateKeyboardEvent(None, 56, True)
        Quartz.CGEventSetFlags(e_down, SHIFT)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, e_down)
        time.sleep(KEY_DELAY)
        
        e_up = Quartz.CGEventCreateKeyboardEvent(None, 56, False)
        Quartz.CGEventSetFlags(e_up, 0)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, e_up)
        time.sleep(0.05)
    except Exception as e:
        log_error(f"Error in force_tsm_sync: {e}", e)

def _do_switch_layout():
    original = get_clipboard()
    selected = copy_selected_text()
    if not selected or not selected.strip():
        selected = select_word_left()
    
    if not selected or not selected.strip():
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
    
    set_clipboard(converted)
    time.sleep(0.05)
    send_key(9, CMD)
    time.sleep(PASTE_DELAY)
    set_clipboard(original)
    time.sleep(0.05)
    switch_to_target_language(target_lang)
    time.sleep(PASTE_DELAY)
    force_tsm_sync()

def switch_layout():
    """Основная функция переключения раскладки и конвертации текста с защитой от сбоев"""
    try:
        with objc.autorelease_pool():
            _do_switch_layout()
    except Exception as e:
        log_error(f"Error in switch_layout: {e}", e)

_last_trigger = 0.0
_tap_ok = False
_opt_was_pressed = False
_ctrl_was_pressed = False
_trigger_key = 'alt'

def set_trigger_key(key):
    global _trigger_key
    _trigger_key = key
    try:
        defaults = NSUserDefaults.standardUserDefaults()
        defaults.setObject_forKey_(key, 'LayoutSwitcherTriggerKey')
        defaults.synchronize()
    except Exception as e:
        log_error(f"Error saving trigger key: {e}", e)

def load_trigger_key():
    global _trigger_key
    try:
        defaults = NSUserDefaults.standardUserDefaults()
        saved = defaults.stringForKey_('LayoutSwitcherTriggerKey')
        if saved in ['alt', 'ctrl']:
            _trigger_key = saved
    except Exception as e:
        log_error(f"Error loading trigger key: {e}", e)

def handle_modifier_release(is_pressed, was_pressed, has_other_mods):
    """Обрабатывает отпускание модификатора и запускает переключение"""
    if was_pressed and not is_pressed and not has_other_mods:
        global _last_trigger
        now = time.time()
        if now - _last_trigger > DEBOUNCE_TIMEOUT:
            _last_trigger = now
            threading.Thread(target=switch_layout, daemon=True).start()
        return False
    return was_pressed

def event_callback(proxy, event_type, event, refcon):
    """Обработчик событий клавиатуры"""
    global _opt_was_pressed, _ctrl_was_pressed
    
    # Защита от автоотключения Event Tap операционной системой
    if event_type == Quartz.kCGEventTapDisabledByTimeout or event_type == Quartz.kCGEventTapDisabledByUserInput:
        if proxy is not None:
            Quartz.CGEventTapEnable(proxy, True)
        return event
    
    try:
        if event_type == Quartz.kCGEventKeyDown:
            _opt_was_pressed = False
            _ctrl_was_pressed = False
        
        elif event_type == Quartz.kCGEventFlagsChanged:
            flags = Quartz.CGEventGetFlags(event)
            is_opt_pressed = bool(flags & OPT)
            is_ctrl_pressed = bool(flags & CTRL)
            has_cmd = bool(flags & CMD)
            has_shift = bool(flags & SHIFT)
            
            if _trigger_key == 'alt':
                has_other_mods = has_cmd or is_ctrl_pressed or has_shift
                if is_opt_pressed and not has_other_mods:
                    _opt_was_pressed = True
                elif is_opt_pressed and has_other_mods:
                    _opt_was_pressed = False
                elif not is_opt_pressed:
                    _opt_was_pressed = handle_modifier_release(is_opt_pressed, _opt_was_pressed, has_other_mods)
            else:
                has_other_mods = has_cmd or is_opt_pressed or has_shift
                if is_ctrl_pressed and not has_other_mods:
                    _ctrl_was_pressed = True
                elif is_ctrl_pressed and has_other_mods:
                    _ctrl_was_pressed = False
                elif not is_ctrl_pressed:
                    _ctrl_was_pressed = handle_modifier_release(is_ctrl_pressed, _ctrl_was_pressed, has_other_mods)
    except Exception as e:
        log_error(f"Error in event_callback: {e}", e)
    
    return event

def start_tap():
    global _tap_ok
    try:
        mask = (Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged) | 
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown))
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap,
            0, mask, event_callback, None)
        if not tap:
            print("❌ Event Tap не создан — нет разрешения Accessibility")
            log_error("Event Tap could not be created - missing Accessibility permissions")
            _tap_ok = False
            return
        _tap_ok = True
        print("✅ Event Tap создан")
        src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetCurrent(), src, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(tap, True)
        Quartz.CFRunLoopRun()
    except Exception as e:
        log_error(f"Fatal error in start_tap: {e}", e)

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

def init_main_thread():
    """Прогревает подсистемы macOS (SkyLight, HIToolbox, TIS, Carbon) на главном потоке.
    Это критически необходимо для macOS 10.15 Catalina, где первая инициализация таблицы
    трансляции клавиш требует com.apple.main-thread (иначе libdispatch assertion crash).
    """
    try:
        # Прогрев SkyLight key_translate_initialize на главном потоке
        dummy_down = Quartz.CGEventCreateKeyboardEvent(None, 56, True)
        dummy_up = Quartz.CGEventCreateKeyboardEvent(None, 56, False)
        del dummy_down, dummy_up
        
        # Прогрев буфера обмена и Carbon TIS на главном потоке
        get_clipboard()
        _init_carbon()
        get_current_input_source()
    except Exception as e:
        log_error(f"Error during main thread warmup: {e}", e)

if __name__ == '__main__':
    init_main_thread()
    assert [convert_text(text) for text in (',tksq', 'rjhj,rf', 'dm_image')] == ['белый', 'коробка', 'вь_шьфпу']
    threading.Thread(target=start_tap, daemon=True).start()
    time.sleep(0.5)
    LayoutSwitcherApp().run()
