#!/usr/bin/env python3
"""
Last-Letter Helper overlay

This version focuses on the "last letter" word game flow instead of WordBomb.
It keeps the overlay lightweight: no panic button, no automatic typing, just
live suggestions that respect the last letter of the previously submitted word.
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
        self.original_set = set(words)
        self.reset_round()

    def reset_round(self):
        self._set = set(self.original_set)
        self._list = sorted(self._set)

    @staticmethod
    def _difficulty_score(word: str) -> int:
        uncommon = set("jqxzv")
        return sum(1 for c in word if c in uncommon)

    def suggest(self, required_prefix: str, letters: str, limit=5, used=None):
        if used is None:
            used = set()
        letters = letters or ""
        required_prefix = required_prefix or ""

        # Ensure we always respect the last-letter rule.
        if required_prefix:
            if letters.startswith(required_prefix):
                prefix = letters
            else:
                prefix = required_prefix + letters
        else:
            prefix = letters

        prefix_results = [w for w in self._list
                          if w.startswith(prefix)
                          and w not in used]
        prefix_mode = True

        # If nothing matches the current buffer, fall back to the required letter only
        # so the player always sees at least one valid option when it exists.
        if not prefix_results and required_prefix:
            prefix_mode = False
            prefix_results = [w for w in self._list
                              if w.startswith(required_prefix)
                              and w not in used]

        results_sorted = sorted(prefix_results,
                                key=lambda x: (len(x), self._difficulty_score(x), x))
        return results_sorted[:limit], prefix_mode

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

    def __init__(self,suggester):
        super().__init__()
        self.suggester = suggester
        self.buffer = ""
        self.words_found = 0
        self.longest_word = 0
        self.used_words = set()
        self.required_prefix = None
        self.hidden_mode = False
        self.kcontroller = KController()
        self._build_ui()
        self.update_signal.connect(self.on_update_signal)
        self.show()

    # -------------------- _build_ui --------------------
    def _build_ui(self):
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint|QtCore.Qt.FramelessWindowHint|QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.container = GlowFrame(self)
        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(18,18,18,18)
        layout.setSpacing(4)
        self.header_label = QtWidgets.QLabel("Last-Letter Helper")
        font_header = QtGui.QFont("Segoe UI",12,QtGui.QFont.Bold)
        self.header_label.setFont(font_header)
        self.header_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.header_label)
        stats_layout = QtWidgets.QHBoxLayout()
        self.required_label = QtWidgets.QLabel("Start letters: ?")
        self.required_label.setStyleSheet("color:#ffaa00; background: transparent;")
        font_required = QtGui.QFont("Segoe UI",11,QtGui.QFont.Bold)
        self.required_label.setFont(font_required)
        stats_layout.addWidget(self.required_label)

        self.score_label = QtWidgets.QLabel("Score: 0 | Langste: 0")
        self.score_label.setStyleSheet("color:#ffaa00; background: transparent;")
        self.score_label.setFont(font_required)
        self.score_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        stats_layout.addWidget(self.score_label)
        layout.addLayout(stats_layout)

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
        self.status_label = QtWidgets.QLabel("F7: hide/show | F6: new round | F8: quit | Enter: submit/reset")
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

        if key_char=="BACKSPACE":
            self.buffer = self.buffer[:-1]
        elif key_char=="ENTER":
            submitted = self.buffer.lower()
            if submitted.isalpha() and submitted:
                self.used_words.add(submitted)
                self.suggester.remove_word(submitted)
                self.words_found += 1
                self.longest_word = max(self.longest_word, len(submitted))
                if len(submitted) >= 2:
                    self.required_prefix = submitted[-2:]
                else:
                    self.required_prefix = submitted[-1]
                self.buffer = self.required_prefix
            else:
                self.buffer = ""
        else:
            if re.match(r"[a-z]", key_char):
                self.buffer += key_char.lower()
        self.update_ui()

    # -------------------- update UI --------------------
    def update_ui(self):
        self.buffer_label.setText(f"typed: {self.buffer or '(empty)'}")
        suggestions, prefix_mode = self.suggester.suggest(self.required_prefix, self.buffer.lower(), SUGGESTION_COUNT, self.used_words)
        best_word = suggestions[0] if suggestions else None
        self.container.contains_mode = not prefix_mode
        self.container.word_length = len(best_word) if best_word else len(self.buffer)
        self.container.ready_for_fire = bool(suggestions)

        self.required_label.setText(f"Start letters: {self.required_prefix or '?'}")
        self.score_label.setText(f"Score: {self.words_found} | Langste: {self.longest_word}")

        # next letter hint
        typed_word = self.buffer.lower()
        if self.required_prefix and typed_word and not typed_word.startswith(self.required_prefix):
            next_hint = f"Start met '{self.required_prefix}'"
            self.next_letter_label.setStyleSheet("color:#ff5555; background: transparent;")
        elif not suggestions and self.required_prefix:
            next_hint = "Geen woorden meer"
            self.next_letter_label.setStyleSheet("color:#ff5555; background: transparent;")
        elif not suggestions:
            next_hint = "Type om te starten"
            self.next_letter_label.setStyleSheet("color:#ffaa00; background: transparent;")
        else:
            if len(typed_word) < len(best_word):
                next_hint = best_word[len(typed_word)]
            else:
                next_hint = "Druk op Enter"
            self.next_letter_label.setStyleSheet("color:#00ff88; background: transparent;")
        self.next_letter_label.setText(next_hint)

        # suggestions display
        colored_words = []
        for word in suggestions:
            colored = ""
            for i,c in enumerate(word):
                if i < len(typed_word) and word.startswith(typed_word):
                    colored += f"<span style='color:#00ff88; font-weight:700'>{c}</span>"
                elif typed_word and typed_word in word and c.lower() in typed_word:
                    colored += f"<span style='color:#3399ff; font-weight:700'>{c}</span>"
                elif self.required_prefix and i < len(self.required_prefix) and c.lower() == self.required_prefix[i]:
                    colored += f"<span style='color:#ffaa00; font-weight:700'>{c}</span>"
                else:
                    colored += f"<span style='color:#ff5555'>{c}</span>"
            if word == best_word:
                colored = f"<span style='background-color:rgba(255,215,0,0.12); padding:2px 4px;'>{colored}</span>"
            colored_words.append(colored)
        warning_suffix = " | Geen geldige woorden meer" if (self.required_prefix and not colored_words) else ""
        self.status_label.setText(f"F7: hide/show | F6: new round | F8: quit | Enter: submit/reset{warning_suffix}")
        self.suggest_label.setText("<span style='color:#ffffff'>no matches</span>" if not colored_words else "<br>".join(colored_words))

        # glow
        self.container.set_glow(bool(best_word))

    # -------------------- global key handler --------------------
    def start_new_round(self):
        self.suggester.reset_round()
        self.used_words = set()
        self.words_found = 0
        self.longest_word = 0
        self.required_prefix = None
        self.buffer = ""
        self.update_ui()

    def handle_key(self,key):
        try:
            if hasattr(key,'char') and key.char and re.match(r"[a-zA-Z]",key.char):
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
            elif key==keyboard.Key.f6:
                self.start_new_round()
        except Exception as e:
            print("Key handling error:",e)

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


