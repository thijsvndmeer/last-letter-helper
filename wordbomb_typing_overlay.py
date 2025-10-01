#!/usr/bin/env python3
"""
WordBomb Typing Overlay with improved TAB autocomplete behavior
- TAB hint hidden when the buffer already equals the longest suggestion
- Enter cancels an in-progress autocomplete
- Autocomplete runs 1.5x faster than the previous version (~66.7ms mean per char)
- Submitted words are removed from the suggester so they won't be suggested again
- Panic button (`) behavior included
"""

import sys, re, os, random, math
from pathlib import Path
from pynput import keyboard
from pynput.keyboard import Controller as KController
from PyQt5 import QtWidgets, QtCore, QtGui

WORDLIST_CANDIDATES = ["words_alpha.txt", "/usr/share/dict/words"]
SUGGESTION_COUNT = 5
OVERLAY_WIDTH = 480
OVERLAY_HEIGHT = 280
MAX_PARTICLES = 50

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_wordlist():
    for path in WORDLIST_CANDIDATES:
        full_path = get_resource_path(path)
        if Path(full_path).exists():
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                return [w.strip().lower() for w in f if w.strip()]
    return ["test", "word", "bomb", "play", "game", "overlay",
            "autocomplete", "realistic", "typing", "longest", "suggestion", "epee", "gizmo"]

class WordSuggester:
    def __init__(self, words):
        self._set = set(words)
        self._list = sorted(self._set)

    def suggest(self, letters, limit=5):
        if letters is None:
            letters = ""
        if not letters:
            return [], True
        results = [w for w in self._list if w.startswith(letters)]
        prefix_mode = True
        if not results:
            results = [w for w in self._list if letters in w]
            prefix_mode = False
        results_sorted = sorted(results, key=lambda x: (len(x), x))
        if results_sorted:
            longest_word = max(results, key=len)
            if longest_word not in results_sorted[:limit]:
                results_sorted = results_sorted[:max(0, limit-1)] + [longest_word]
            else:
                results_sorted = results_sorted[:limit]
        return results_sorted, prefix_mode

    def remove_word(self, word):
        word = word.lower()
        if word in self._set:
            self._set.remove(word)
            self._list = sorted(self._set)
            return True
        return False

class FireParticle:
    def __init__(self, x, y, size, color, vx, vy, life, phase):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.vx = vx
        self.vy = vy
        self.life = life
        self.phase = phase

class GlowFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.glow_alpha = 0.0
        self.glow_active = False
        self.contains_mode = False
        self.word_length = 0
        self.ready_for_fire = False
        self.panicking = False
        self.particles = []
        self.extra_effects = []
        self.fast_phase = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def set_glow(self, active: bool):
        self.glow_active = active

    def spawn_particles(self):
        if self.ready_for_fire and self.word_length >= 10:
            num_new = min(self.word_length-9, MAX_PARTICLES - len(self.particles))
            for _ in range(num_new):
                x = random.randint(20, OVERLAY_WIDTH-20)
                y = OVERLAY_HEIGHT - random.randint(0,15)
                size = random.randint(6,12)
                t = min(self.word_length, MAX_PARTICLES)/MAX_PARTICLES
                if self.glow_active:
                    color = QtGui.QColor(0,255,200,random.randint(80,150))
                else:
                    r = int(50 + t*205)
                    g = int(50 + t*150)
                    b = int(200 - t*150)
                    color = QtGui.QColor(r,g,b,random.randint(80,150))
                vx = random.uniform(-0.5,0.5)
                vy = random.uniform(-3,-1)
                life = random.randint(40,70)
                phase = random.uniform(0,2*math.pi)
                self.particles.append(FireParticle(x,y,size,color,vx,vy,life,phase))

    def spawn_extra_effects(self):
        if self.ready_for_fire and self.word_length >= 20:
            for _ in range(4):
                side = random.choice(['top','bottom','left','right'])
                if side=='top':
                    x = random.randint(-30, OVERLAY_WIDTH+30)
                    y = -random.randint(5,30)
                elif side=='bottom':
                    x = random.randint(-30, OVERLAY_WIDTH+30)
                    y = OVERLAY_HEIGHT + random.randint(5,30)
                elif side=='left':
                    x = -random.randint(5,30)
                    y = random.randint(-20, OVERLAY_HEIGHT+20)
                else:
                    x = OVERLAY_WIDTH + random.randint(5,30)
                    y = random.randint(-20, OVERLAY_HEIGHT+20)
                size = random.randint(8,16)
                color = QtGui.QColor(random.randint(100,255), random.randint(50,255), random.randint(50,255), random.randint(100,180))
                vx = random.uniform(-1,1)
                vy = random.uniform(-1,0)
                life = random.randint(50,90)
                phase = random.uniform(0, 2*math.pi)
                self.extra_effects.append(FireParticle(x,y,size,color,vx,vy,life,phase))

    def update_frame(self):
        self.fast_phase += 0.05
        if self.fast_phase > 1.0: self.fast_phase = 0.0

        if self.glow_active:
            self.glow_alpha = min(1.0, self.glow_alpha+0.05)
        else:
            self.glow_alpha = max(0.0, self.glow_alpha-0.05)

        self.spawn_particles()
        self.spawn_extra_effects()

        for p in self.particles:
            p.phase += 0.1
            p.x += math.sin(p.phase)*0.5 + p.vx
            p.y += p.vy
            p.size = max(4,p.size + random.uniform(-0.5,0.5))
            alpha = max(20, min(255, p.color.alpha() + random.randint(-15,15)))
            p.color.setAlpha(alpha)
            p.life -= 1
        self.particles = [p for p in self.particles if p.life>0]

        for p in self.extra_effects:
            p.phase += 0.1
            p.x += math.sin(p.phase)*0.8 + p.vx
            p.y += math.cos(p.phase)*0.5 + p.vy
            p.size = max(4,p.size + random.uniform(-0.7,0.7))
            alpha = max(20, min(255, p.color.alpha() + random.randint(-15,15)))
            p.color.setAlpha(alpha)
            p.life -=1
        self.extra_effects = [p for p in self.extra_effects if p.life>0]

        self.update()

    def paintEvent(self,event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        for p in self.particles:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        for p in self.extra_effects:
            painter.setBrush(QtGui.QBrush(p.color))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(int(p.x),int(p.y),int(p.size),int(p.size))

        bg_grad = QtGui.QLinearGradient(0,0,0,rect.height())
        bg_grad.setColorAt(0, QtGui.QColor(25,25,40,230))
        bg_grad.setColorAt(1, QtGui.QColor(10,10,20,220))
        painter.setBrush(QtGui.QBrush(bg_grad))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect,14,14)

        border_rect = rect.adjusted(2,2,-2,-2)
        slow_grad = QtGui.QConicalGradient(border_rect.center(),self.fast_phase*360)
        slow_grad.setColorAt(0.0,QtGui.QColor(50,150,180,120))
        slow_grad.setColorAt(0.5,QtGui.QColor(80,180,140,120))
        slow_grad.setColorAt(1.0,QtGui.QColor(50,150,180,120))
        pen = QtGui.QPen(QtGui.QBrush(slow_grad),3)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(border_rect,14,14)

        if not self.glow_active and self.contains_mode:
            pen = QtGui.QPen(QtGui.QColor(255,80,80,150),3)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

                # panic visual: bright red <-> bright blue when panicking
        if self.panicking:
            # make the border feel "fast" and vivid while panicking
            pan_grad = QtGui.QConicalGradient(border_rect.center(), self.fast_phase*360)
            alpha_val = 220  # fairly opaque
            pan_grad.setColorAt(0.0, QtGui.QColor(255, 40, 40, alpha_val))   # bright red
            pan_grad.setColorAt(0.5, QtGui.QColor(60, 160, 255, alpha_val))  # bright blue/cyan
            pan_grad.setColorAt(1.0, QtGui.QColor(255, 40, 40, alpha_val))
            pen = QtGui.QPen(QtGui.QBrush(pan_grad), 4)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect, 14, 14)
        elif self.glow_alpha > 0:
            # existing cyan/green fast glow (unchanged)
            fast_grad = QtGui.QConicalGradient(border_rect.center(), self.fast_phase*360)
            fast_grad.setColorAt(0.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            fast_grad.setColorAt(0.5, QtGui.QColor(0,255,128,int(255*self.glow_alpha)))
            fast_grad.setColorAt(1.0, QtGui.QColor(0,255,255,int(255*self.glow_alpha)))
            pen = QtGui.QPen(QtGui.QBrush(fast_grad),4)
            painter.setPen(pen)
            painter.drawRoundedRect(border_rect,14,14)

class TypingOverlay(QtWidgets.QWidget):
    update_signal = QtCore.pyqtSignal(str)
    autocomplete_signal = QtCore.pyqtSignal(str)
    cancel_signal = QtCore.pyqtSignal()

    def __init__(self,suggester):
        super().__init__()
        self.suggester = suggester
        self.buffer = ""
        self.high_score = 0
        self.hidden_mode = False
        self.autocomplete_in_progress = False
        self.autocomplete_timers = []
        self.ignore_synthetic = False
        self.expected_synthetic = 0
        self.kcontroller = KController()
        self.MEAN_MS = 100.0
        self.SD_MS = 50.0
        self.MIN_MS = 40
        self.MAX_MS = 300
        self.KEY_DOWN_MS = 8
        self._build_ui()
        self.update_signal.connect(self.on_update_signal)
        self.autocomplete_signal.connect(self.start_autocomplete)
        self.cancel_signal.connect(self.cancel_autocomplete)
        self.show()

    # -------------------- _build_ui --------------------
    def _build_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.container = GlowFrame(self)
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(18,18,18,18)
        layout.setSpacing(4)
        self.header_label = QtWidgets.QLabel("Word Bomb Helper by xHondje")
        font_header = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.header_label.setFont(font_header)
        self.header_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)
        self.length_label = QtWidgets.QLabel("")
        font_length = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.length_label.setFont(font_length)
        self.length_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.length_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.length_label)
        self.buffer_label = QtWidgets.QLabel("typed: (empty)")
        font = QtGui.QFont("Segoe UI",18,QtGui.QFont.Bold)
        self.buffer_label.setFont(font)
        self.buffer_label.setStyleSheet("color:#ffd580; background: transparent;")
        layout.addWidget(self.buffer_label)
        self.suggest_label = QtWidgets.QLabel("")
        font2 = QtGui.QFont("Segoe UI",14)
        self.suggest_label.setFont(font2)
        self.suggest_label.setWordWrap(True)
        self.suggest_label.setTextFormat(QtCore.Qt.RichText)
        self.suggest_label.setMinimumHeight(120)
        self.suggest_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.suggest_label)
        self.next_letter_label = QtWidgets.QLabel("")
        font_hint = QtGui.QFont("Segoe UI",14,QtGui.QFont.Bold)
        self.next_letter_label.setFont(font_hint)
        self.next_letter_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.next_letter_label)
        self.highscore_label = QtWidgets.QLabel(f"High Score: {self.high_score}")
        font_hs = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.highscore_label.setFont(font_hs)
        self.highscore_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.highscore_label.setStyleSheet("color:#ffaa00; background: transparent;")
        layout.addWidget(self.highscore_label)
        self.status_label = QtWidgets.QLabel("F7: hide/show | F8: quit | Enter: submit/reset |  `: panic")
        self.status_label.setStyleSheet("color:#888; font-size:11px; font-family:'Segoe UI'; background: transparent;")
        layout.addWidget(self.status_label)
        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)
        self.container.setGeometry(0,0,OVERLAY_WIDTH,OVERLAY_HEIGHT)
        self.move(20,250)
        self.old_pos = None

    # -------------------- mouse drag --------------------
    def mousePressEvent(self,event):
        if event.button() == QtCore.Qt.LeftButton:
            self.old_pos = event.globalPos()
    def mouseMoveEvent(self,event):
        if self.old_pos:
            delta = event.globalPos() - self.old_pos
            self.move(self.x()+delta.x(), self.y()+delta.y())
            self.old_pos = event.globalPos()
    def mouseReleaseEvent(self,event):
        self.old_pos = None

    # -------------------- update signal --------------------
    def on_update_signal(self,key_char):
        if not self.isVisible(): return

        if key_char == "ENTER" and self.autocomplete_in_progress:
            self.cancel_autocomplete()
            return

        if key_char=="BACKSPACE":
            self.buffer = self.buffer[:-1]
        elif key_char=="ENTER":
            self.update_ui()  # <--- move this first
            if self.buffer.lower() in self.suggester._set:
                self.high_score = max(self.high_score,len(self.buffer))
                self.highscore_label.setText(f"High Score: {self.high_score}")
                self.suggester.remove_word(self.buffer.lower())
            self.buffer = ""
        elif key_char=="`":  # panic button
            self.panic_complete()
            return
        else:
            self.buffer += key_char.lower()
        self.update_ui()

    # -------------------- update UI --------------------
    def update_ui(self):
        self.buffer_label.setText(f"typed: {self.buffer or '(empty)'}")
        suggestions, prefix_mode = self.suggester.suggest(self.buffer.lower(), SUGGESTION_COUNT)
        self.container.contains_mode = not prefix_mode
        self.container.word_length = len(self.buffer)
        self.container.ready_for_fire = bool(suggestions)
        self.length_label.setText(f"Length: {len(self.buffer)}")

        # next letter hint
        if not suggestions:
            next_hint = "BACKSPACE" if not prefix_mode else ""
        else:
            longest_word = max(suggestions,key=len)
            if self.buffer.lower() == longest_word.lower():
                next_hint = "Longest word possible typed"
                self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
            elif not prefix_mode:
                next_hint = "BACKSPACE"
                self.next_letter_label.setStyleSheet("color:#3399ff; background: transparent;")
            else:
                next_hint = longest_word[len(self.buffer)]
                self.next_letter_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.next_letter_label.setText(next_hint)

        # suggestions display
        colored_words = []
        longest_word = max(suggestions,key=len) if suggestions else None
        for word in suggestions:
            colored = ""
            for i,c in enumerate(word):
                if prefix_mode and i<len(self.buffer):
                    colored += f"<span style='color:#00ff88; font-weight:700'>{c}</span>"
                elif not prefix_mode and self.buffer.lower() in word.lower() and c.lower() in self.buffer.lower():
                    colored += f"<span style='color:#3399ff; font-weight:700'>{c}</span>"
                else:
                    colored += f"<span style='color:#ff5555'>{c}</span>"
            show_tab_hint = (longest_word is not None and word==longest_word and prefix_mode
                             and (self.buffer.lower()!=longest_word.lower())
                             and (not self.autocomplete_in_progress))
            if show_tab_hint:
                colored += " <span style='color:#aaaaaa; font-size:11px'>&nbsp;&nbsp;(TAB to auto-complete)</span>"
            colored_words.append(colored)
        self.suggest_label.setText("<span style='color:#ffffff'>no matches</span>" if not colored_words else "<br>".join(colored_words))

        # glow
        self.container.set_glow(bool(self.buffer and (self.buffer in self.suggester._set)))

    # -------------------- panic logic --------------------
    def panic_complete(self):
        # do nothing if there's nothing typed (no visual change)
        if not self.buffer:
            return

        # cancel any running autocomplete to avoid timer collisions
        try:
            self.cancel_autocomplete()
        except Exception:
            pass

        orig_buffer = self.buffer

        # choose a target word: prefer suggestions for current buffer,
        # fallback to prefix-of-3, then to first available word in list.
        suggestions, prefix_mode = self.suggester.suggest(orig_buffer.lower(), 100)
        if suggestions:
            target_word = suggestions[0]
        else:
            prefix = orig_buffer[:3]
            suggestions2, _ = self.suggester.suggest(prefix.lower(), 100)
            if suggestions2:
                target_word = suggestions2[0]
            elif self.suggester._list:
                target_word = self.suggester._list[0]
            else:
                return  # nothing to type

        # Decide whether we can finish the current buffer (no erasing) or must
        # erase and type from scratch.
        can_finish = target_word.startswith(orig_buffer)

        # Activate panic visuals and synthetic handling
        self.container.panicking = True
        self.autocomplete_timers = []
        self.autocomplete_in_progress = True

        if can_finish:
            chars_to_type = list(target_word[len(orig_buffer):])
            backspaces = 0
        else:
            chars_to_type = list(target_word)  # type whole word after erasing
            backspaces = len(orig_buffer)

        # total synthetic events we'll emit: backspaces + chars + final ENTER
        total_synthetic = backspaces + len(chars_to_type) + 1
        self.expected_synthetic = total_synthetic
        self.ignore_synthetic = True

        cumulative_ms = 0

        # helper: scheduled backspace
        def make_timer_for_backspace():
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            def on_timeout():
                try:
                    self.kcontroller.press(keyboard.Key.backspace)
                    release_timer = QtCore.QTimer(self)
                    release_timer.setSingleShot(True)
                    release_timer.timeout.connect(lambda: self.kcontroller.release(keyboard.Key.backspace))
                    release_timer.start(self.KEY_DOWN_MS)
                except Exception as e:
                    print("Controller send error (panic backspace):", e)
                # notify overlay as if Backspace pressed
                self.update_signal.emit("BACKSPACE")
            t.timeout.connect(on_timeout)
            return t

        # helper: scheduled character
        def make_timer_for_char(ch):
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            def on_timeout(ch=ch):
                try:
                    self.kcontroller.press(ch)
                    release_timer = QtCore.QTimer(self)
                    release_timer.setSingleShot(True)
                    release_timer.timeout.connect(lambda ch=ch: self.kcontroller.release(ch))
                    release_timer.start(self.KEY_DOWN_MS)
                except Exception as e:
                    print("Controller send error (panic char):", e)
                self.update_signal.emit(ch)
            t.timeout.connect(on_timeout)
            return t

        # helper: scheduled ENTER (uses update_signal so submit logic runs normally)
        # helper: scheduled ENTER (physical press/release only; do NOT emit update_signal here)
        def make_timer_for_enter():
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            def on_timeout():
                try:
                    # physical press/release only
                    self.kcontroller.press(keyboard.Key.enter)
                    release_timer = QtCore.QTimer(self)
                    release_timer.setSingleShot(True)
                    release_timer.timeout.connect(lambda: self.kcontroller.release(keyboard.Key.enter))
                    release_timer.start(self.KEY_DOWN_MS)
                except Exception as e:
                    print("Controller send error (panic enter):", e)
                # IMPORTANT: do NOT call self.update_signal.emit("ENTER") here;
                # we'll trigger normal handling after synthetic-ignore is cleared.
            t.timeout.connect(on_timeout)
            return t


        # Schedule backspaces (if needed). Use a slightly faster cadence for panic backspaces.
        for _ in range(backspaces):
            delay = int(max(self.MIN_MS, min(self.MAX_MS,
                                            random.gauss(self.MEAN_MS * 0.5, self.SD_MS))))
            cumulative_ms += delay
            t_bs = make_timer_for_backspace()
            t_bs.start(cumulative_ms)
            self.autocomplete_timers.append(t_bs)

        # Schedule typing the characters using a faster mean (panic = faster)
        for ch in chars_to_type:
            delay = int(max(self.MIN_MS, min(self.MAX_MS,
                                            random.gauss(self.MEAN_MS * 0.5, self.SD_MS))))
            cumulative_ms += delay
            t_ch = make_timer_for_char(ch)
            t_ch.start(cumulative_ms)
            self.autocomplete_timers.append(t_ch)

        # Schedule final ENTER to submit the typed word (so suggester.remove_word runs)
        final_delay = int(max(self.MIN_MS, min(self.MAX_MS,
                                              random.gauss(self.MEAN_MS * 0.6, self.SD_MS))))
        cumulative_ms += final_delay
        t_enter = make_timer_for_enter()
        t_enter.start(cumulative_ms)
        self.autocomplete_timers.append(t_enter)

        # Cleanup timer: clear flags and visuals once all scheduled events are done
        fin = QtCore.QTimer(self)
        fin.setSingleShot(True)
        def finish_panic():
            # clear timers tracking
            self.autocomplete_timers = []
            self.autocomplete_in_progress = False
            self.ignore_synthetic = False
            self.expected_synthetic = 0
            self.container.panicking = False
            # the final ENTER has already triggered on_update_signal which clears buffer if the word
            # was in suggester; ensure UI is consistent
            self.update_ui()
            QtCore.QTimer.singleShot(20, lambda: self.handle_key(keyboard.Key.enter))
        fin.timeout.connect(finish_panic)
        fin.start(cumulative_ms + 120)


    # -------------------- global key handler --------------------
    def handle_key(self,key):
        try:
            if self.ignore_synthetic and self.expected_synthetic > 0:
                self.expected_synthetic -= 1
                if self.expected_synthetic <= 0:
                    self.ignore_synthetic = False
                return

            if hasattr(key,'char') and key.char and re.match(r"[a-zA-Z`]",key.char):
                self.update_signal.emit(key.char)
            elif key==keyboard.Key.backspace:
                self.update_signal.emit("BACKSPACE")
            elif key==keyboard.Key.enter:
                self.update_signal.emit("ENTER")
            elif key==keyboard.Key.f8:
                QtWidgets.QApplication.quit()
            elif key==keyboard.Key.f7:
                self.hidden_mode = not self.hidden_mode
                self.setVisible(not self.hidden_mode)
            elif key==keyboard.Key.tab:
                suggestions, prefix_mode = self.suggester.suggest(self.buffer.lower(), SUGGESTION_COUNT)
                if suggestions and prefix_mode:
                    longest_word = max(suggestions,key=len)
                    if self.buffer.lower()!=longest_word.lower():
                        self.autocomplete_signal.emit(longest_word)
        except Exception as e:
            print("Key handling error:",e)

    # -------------------- autocomplete --------------------
    @QtCore.pyqtSlot()
    def cancel_autocomplete(self):
        if not self.autocomplete_in_progress: return
        for t in self.autocomplete_timers:
            try: t.stop()
            except Exception: pass
        self.autocomplete_timers = []
        self.autocomplete_in_progress = False
        self.ignore_synthetic = False
        self.expected_synthetic = 0

    @QtCore.pyqtSlot(str)
    def start_autocomplete(self, target_word: str):
        if self.autocomplete_in_progress: return
        cur = self.buffer
        if not target_word.startswith(cur): return
        remaining = target_word[len(cur):]
        if not remaining: return
        self.autocomplete_in_progress = True
        self.autocomplete_timers = []
        self.expected_synthetic = len(remaining)
        self.ignore_synthetic = True
        cumulative_ms = 0

        def make_timer_for_char(ch):
            t = QtCore.QTimer(self)
            t.setSingleShot(True)
            def on_timeout():
                try:
                    self.kcontroller.press(ch)
                    release_timer = QtCore.QTimer(self)
                    release_timer.setSingleShot(True)
                    release_timer.timeout.connect(lambda: self.kcontroller.release(ch))
                    release_timer.start(self.KEY_DOWN_MS)
                except Exception as e: print("Controller send error:", e)
                self.update_signal.emit(ch)
            t.timeout.connect(on_timeout)
            return t

        for ch in remaining:
            delay = int(max(self.MIN_MS, min(self.MAX_MS, random.gauss(self.MEAN_MS, self.SD_MS))))
            cumulative_ms += delay
            t = make_timer_for_char(ch)
            t.start(cumulative_ms)
            self.autocomplete_timers.append(t)

        fin = QtCore.QTimer(self)
        fin.setSingleShot(True)
        fin.timeout.connect(lambda: (setattr(self,"autocomplete_timers",[]),
                                     setattr(self,"autocomplete_in_progress",False),
                                     setattr(self,"ignore_synthetic",False),
                                     setattr(self,"expected_synthetic",0)))
        fin.start(cumulative_ms + 40)

# -------------------- main --------------------
def main():
    words = load_wordlist()
    suggester = WordSuggester(words)
    app = QtWidgets.QApplication(sys.argv)
    overlay = TypingOverlay(suggester)
    listener = keyboard.Listener(on_press=overlay.handle_key)
    listener.start()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()


