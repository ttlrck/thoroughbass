"""
Thorough-Bass Composition System
Based on Niedt's Musical Guide, Parts I-III (1700/1721/1717)

Architecture:
  - Note         : egy hang (pitch + octave)
  - Figure       : egy basszusfigura (pl. 6, 7, 6/4, stb.)
  - BassNote     : egy basszushang + figurak
  - Chord        : egy teljes akkord (4 szolam: S, A, T, B)
  - NiedtRuleEngine : Niedt szabályainak motorja
  - ThoroughBassRealizer : basszusvonal -> teljes 4 szolamu kiiras

Hasznalat:
  from key_module import Key
  from thorough_bass import *

  key = Key('C')           # C-dur
  realizer = ThoroughBassRealizer(key=key)
  chords = realizer.realize(bass_line)
"""

from key_module import Key
from midiutil import MIDIFile

# ─────────────────────────────────────────────
# 1. ALAPOK: hangok, intervallumok
# ─────────────────────────────────────────────

PITCH_CLASSES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

ENHARMONIC = {
    'Db': 'C#', 'D#': 'Eb', 'E#': 'F',
    'Fb': 'E',  'Gb': 'F#', 'G#': 'Ab',
    'A#': 'Bb', 'Cb': 'B',  'B#': 'C'
}

def normalize_pitch(pitch):
    return ENHARMONIC.get(pitch, pitch)

def pitch_to_semitone(pitch):
    pitch = normalize_pitch(pitch)
    return PITCH_CLASSES.index(pitch)

def semitone_interval(pitch_a, pitch_b):
    a = pitch_to_semitone(pitch_a)
    b = pitch_to_semitone(pitch_b)
    diff = b - a
    if diff > 6:
        diff -= 12
    elif diff < -6:
        diff += 12
    return diff


# ─────────────────────────────────────────────
# 2. NOTE
# ─────────────────────────────────────────────

class Note:
    def __init__(self, pitch, octave):
        self.pitch = normalize_pitch(pitch)
        self.octave = octave

    def to_midi(self):
        return (self.octave + 1) * 12 + pitch_to_semitone(self.pitch)

    def __repr__(self):
        return "{}{}".format(self.pitch, self.octave)

    def __eq__(self, other):
        return self.pitch == other.pitch and self.octave == other.octave


# ─────────────────────────────────────────────
# 3. FIGURE
# ─────────────────────────────────────────────

class Figure:
    def __init__(self, intervals):
        self.intervals = sorted(intervals)

    @classmethod
    def from_string(cls, s):
        if not s or s.strip() == '':
            return cls([])
        intervals = [int(x.strip()) for x in s.split('/')]
        return cls(intervals)

    def is_empty(self):
        return len(self.intervals) == 0

    def is_sixth(self):
        s = set(self.intervals)
        return s == {6} or s == {3, 6}

    def is_sixth_four(self):
        s = set(self.intervals)
        return 6 in s and 4 in s

    def is_seventh(self):
        return 7 in self.intervals

    def __repr__(self):
        if self.is_empty():
            return 'Fig(0)'
        return "Fig({})".format('/'.join(str(i) for i in self.intervals))


# ─────────────────────────────────────────────
# 4. BASS NOTE
# ─────────────────────────────────────────────

class BassNote:
    def __init__(self, note, figure=None, duration=1.0):
        self.note = note
        self.figure = figure if figure is not None else Figure([])
        self.duration = duration

    def __repr__(self):
        return "BassNote({}, {}, dur={})".format(
            self.note, self.figure, self.duration)


# ─────────────────────────────────────────────
# 5. CHORD
# ─────────────────────────────────────────────

class Chord:
    def __init__(self, bass, tenor, alto, soprano):
        self.bass    = bass
        self.tenor   = tenor
        self.alto    = alto
        self.soprano = soprano

    def voices(self):
        return [self.bass, self.tenor, self.alto, self.soprano]

    def upper_voices(self):
        return [self.tenor, self.alto, self.soprano]

    def __repr__(self):
        return "Chord(S:{} A:{} T:{} B:{})".format(
            self.soprano, self.alto, self.tenor, self.bass)


# ─────────────────────────────────────────────
# 6. RULE ENGINE
# ─────────────────────────────────────────────

class NiedtRuleEngine:
    RIGHT_HAND_MIN_MIDI = (3 + 1) * 12 + pitch_to_semitone('A')   # 57 = A3
    RIGHT_HAND_MAX_MIDI = (5 + 1) * 12 + pitch_to_semitone('E')   # 76 = E5

    def apply_rule_viii_5(self, bass_step_semitones, figure):
        """Ch. VIII Rule 5: félhang lefele lépés az előzőhöz képest -> 6-os akkord."""
        if bass_step_semitones == -1 and figure.is_empty():
            return Figure([6])
        return figure

    def resolve_figure(self, bass_note, prev_bass=None):
        figure = bass_note.figure
        if prev_bass is not None:
            step = semitone_interval(prev_bass.note.pitch, bass_note.note.pitch)
            figure = self.apply_rule_viii_5(step, figure)
        if figure.is_empty():
            figure = Figure([3, 5])
        return figure

    def check_parallel_fifths_octaves(self, chord_a, chord_b):
        violations = []
        voice_names = ['bass', 'tenor', 'alto', 'soprano']
        va = chord_a.voices()
        vb = chord_b.voices()

        for i in range(len(va)):
            for j in range(i + 1, len(va)):
                ai, aj = va[i].to_midi(), va[j].to_midi()
                bi, bj = vb[i].to_midi(), vb[j].to_midi()

                # HA NINCS MOZGÁS, NINCS HIBA
                # (Barokk szabály: ha mindkét szólam helyben marad, nem párhuzam)
                if ai == bi and aj == bj:
                    continue

                # Intervallumok kiszámítása
                int_a = abs(ai - aj) % 12
                int_b = abs(bi - bj) % 12

                # CSAK AKKOR HIBA, HA:
                # 1. Az intervallum kvint (7) vagy oktáv (0) volt az előzőben IS
                # 2. Az intervallum kvint vagy oktáv maradt az újban IS
                # 3. ÉS a hangok ténylegesen elmozdultak (ezt fentebb a continue már kezeli)
                if int_a == int_b and int_a in (0, 7):
                    # Kiegészítés: csak akkor hiba, ha ugyanabba az irányba mozogtak
                    # (Ez a "párhuzamos" mozgás definíciója)
                    direction_i = bi - ai
                    direction_j = bj - aj
                    
                    if (direction_i > 0 and direction_j > 0) or (direction_i < 0 and direction_j < 0):
                        kind = 'kvint' if int_a == 7 else 'oktav'
                        violations.append(f"Parhuzamos {kind}: {voice_names[i]}-{voice_names[j]}")
        return violations

    def is_seventh_prepared(self, seventh_note, prev_chord):
        for voice in prev_chord.voices():
            if voice.pitch == seventh_note.pitch:
                return True
        return False


# ─────────────────────────────────────────────
# 7. REALIZER
# ─────────────────────────────────────────────

class ThoroughBassRealizer:
    """
    Basszusvonalbol teljes 4 szolamu kiirast general Niedt szabalyai szerint.
    A hangnemet Key objektumkent kapja meg -> diatonikus szamitas.
    """

    def __init__(self, key=None, rule_engine=None):
        # Alapertelmezett hangnem: C-dur
        self.key = key if key is not None else Key('C')
        self.rules = rule_engine if rule_engine is not None else NiedtRuleEngine()

    def realize(self, bass_line):
        chords = []
        prev_bass = None
        prev_chord = None

        for bass_note in bass_line:
            resolved_figure = self.rules.resolve_figure(bass_note, prev_bass)
            chord = self._build_chord(bass_note.note, resolved_figure, prev_chord)

            if prev_chord is not None:
                violations = self.rules.check_parallel_fifths_octaves(
                    prev_chord, chord)
                if violations:
                    print("  ! Szolam hiba: {}".format(violations))

            chords.append(chord)
            prev_bass = bass_note
            prev_chord = chord

        return chords

    # ── Segédfüggvények ──────────────────────────────────────

    def _diatonic_pc_above(self, bass_pitch, interval):
        """
        Diatonikus celhhang pitch class-a az adott hangnemben.
        Pl. C-durban: _diatonic_pc_above('D', 6) -> 'B'
            G-durban: _diatonic_pc_above('D', 3) -> 'F#'
        """
        return self.key.diatonic_note(bass_pitch, interval)

    def _diatonic_pc_below(self, bass_pitch, interval):
        """
        Diatonikus celhang pitch class-a LEFELE szamolva.
        Szextakkordnal: basszus a terc, az alaphang = basszus - 3.
        Pl. C-durban: basszus=E, interval=3 -> alaphang=C
            G-durban: basszus=F#, interval=3 -> alaphang=D
        """
        # Megkeressük a basszus pozicioját a skálában
        bass_base = bass_pitch[0] if len(bass_pitch) > 1 else bass_pitch
        scale = self.key.scale
        bass_pos = None
        for i, note in enumerate(scale):
            note_base = note[0] if len(note) > 1 else note
            if note_base == bass_base:
                bass_pos = i
                break
        if bass_pos is None:
            bass_pos = 0

        # Lefele szamolas: (interval-1) fokkal lejjebb
        target_pos = (bass_pos - (interval - 1)) % 7
        return scale[target_pos]

    def _pick_voice(self, pitch, ref_midi, direction, min_midi, max_midi):
        """
        Az adott pitch class legjobb hangjat valasztja ki ellenmozgas szerint.
        direction: -1 = lefele, +1 = felfele, 0 = legkozelebbi
        """
        pc = pitch_to_semitone(pitch)
        candidates = []
        for octave in range(2, 7):
            midi = (octave + 1) * 12 + pc
            if min_midi <= midi <= max_midi:
                candidates.append((midi, Note(pitch, octave)))

        if not candidates:
            return Note(pitch, 4)

        if direction == -1:
            # Basszus felfele -> felső szólamok lefele preferalt
            below = [(m, n) for m, n in candidates if m <= ref_midi]
            pool = sorted(below, key=lambda x: abs(x[0] - ref_midi)) if below \
                   else sorted(candidates, key=lambda x: abs(x[0] - ref_midi))
        elif direction == +1:
            # Basszus lefele -> felső szólamok felfele preferalt
            above = [(m, n) for m, n in candidates if m >= ref_midi]
            pool = sorted(above, key=lambda x: abs(x[0] - ref_midi)) if above \
                   else sorted(candidates, key=lambda x: abs(x[0] - ref_midi))
        else:
            pool = sorted(candidates, key=lambda x: abs(x[0] - ref_midi))

        return pool[0][1]

    def _sort_and_fix(self, notes, min_midi, max_midi):
        """
        Rendezi T < A < S, szétvalasztja az azonos szólamokat,
        es ellenorzi a tartomanyt.
        """
        notes.sort(key=lambda n: n.to_midi())

        # Azonos magassagu szólamok szétvalasztasa
        for i in range(len(notes) - 1, 0, -1):
            if notes[i].to_midi() == notes[i-1].to_midi():
                n = notes[i]
                notes[i] = Note(n.pitch, n.octave + 1)

        # Tartomany
        for i, n in enumerate(notes):
            if n.to_midi() > max_midi:
                notes[i] = Note(n.pitch, n.octave - 1)
            elif n.to_midi() < min_midi:
                notes[i] = Note(n.pitch, n.octave + 1)

        return notes

    # ── Fo akkordépítő logika ─────────────────────────────────

    def _build_chord(self, bass, figure, prev_chord=None):
        """
        Akkordepites Niedt szabályai szerint, diatonikusan az adott hangnemben.

        Kettőzési szabályok:
          Alap harmas (3/5) : alaphangot kettőzzük
          Szextakkord (6)   : alaphang + kvint (terc TILOS, oktav TILOS)
          Kvartszext (6/4)  : kvintet (= basszust) kettőzzük
          Szeptim (7)       : terc + szeptim (kvint elhagyva)
        """
        RIGHT_MIN = NiedtRuleEngine.RIGHT_HAND_MIN_MIDI
        RIGHT_MAX = NiedtRuleEngine.RIGHT_HAND_MAX_MIDI

        # Ellenmozgas iránya
        if prev_chord is not None:
            step = bass.to_midi() - prev_chord.bass.to_midi()
            direction = -1 if step > 0 else (+1 if step < 0 else 0)
        else:
            direction = 0

        # Referencia hangok
        if prev_chord is not None:
            ref_t = prev_chord.tenor.to_midi()
            ref_a = prev_chord.alto.to_midi()
            ref_s = prev_chord.soprano.to_midi()
        else:
            ref_t = Note('C', 4).to_midi()
            ref_a = Note('E', 4).to_midi()
            ref_s = Note('G', 4).to_midi()

        # ── SZEXTAKKORD (6) ──────────────────────────────────
        # Basszus = terc, felső szólamok = alaphang + kvint
        # Oktav TILOS (Niedt Ch. VIII Rule 2)
        if figure.is_sixth():
            root_pc  = self._diatonic_pc_below(bass.pitch, 3)  # alaphang
            fifth_pc = self._diatonic_pc_above(root_pc, 5)     # kvint

            # 3 szolam: alaphang (T), kvint (A), alaphang (S) - kettőzés
            t_note = self._pick_voice(root_pc,  ref_t, direction, RIGHT_MIN, RIGHT_MAX)
            a_note = self._pick_voice(fifth_pc, ref_a, direction, RIGHT_MIN, RIGHT_MAX)
            s_note = self._pick_voice(root_pc,  ref_s, direction, RIGHT_MIN, RIGHT_MAX)

            upper = self._sort_and_fix([t_note, a_note, s_note], RIGHT_MIN, RIGHT_MAX)
            return Chord(bass=bass, tenor=upper[0], alto=upper[1], soprano=upper[2])

        # ── KVARTSZEXT AKKORD (6/4) ───────────────────────────
        # Basszus = kvint, Niedt szerint a kvartot (alaphangot) kettőzzük
        if figure.is_sixth_four():
            root_pc  = self._diatonic_pc_below(bass.pitch, 5)  # alaphang
            third_pc = self._diatonic_pc_above(root_pc, 3)     # terc
            # fifth_pc = bass.pitch                            # kvint = basszus

            # T: alaphang (kettőzés), A: terc, S: alaphang (kettőzés)
            t_note = self._pick_voice(root_pc,  ref_t, direction, RIGHT_MIN, RIGHT_MAX)
            a_note = self._pick_voice(third_pc, ref_a, direction, RIGHT_MIN, RIGHT_MAX)
            s_note = self._pick_voice(root_pc,  ref_s, direction, RIGHT_MIN, RIGHT_MAX)

            upper = self._sort_and_fix([t_note, a_note, s_note], RIGHT_MIN, RIGHT_MAX)
            return Chord(bass=bass, tenor=upper[0], alto=upper[1], soprano=upper[2])

        # ── SZEPTIMAKKORD (7) ─────────────────────────────────
        # Terc + szeptim, kvint elhagyva (Niedt Ch. IX Rule 1)
        if figure.is_seventh():
            third_pc   = self._diatonic_pc_above(bass.pitch, 3)
            seventh_pc = self._diatonic_pc_above(bass.pitch, 7)

            # T: terc, A: szeptim, S: terc (kettőzés)
            t_note = self._pick_voice(third_pc,   ref_t, direction, RIGHT_MIN, RIGHT_MAX)
            a_note = self._pick_voice(seventh_pc, ref_a, direction, RIGHT_MIN, RIGHT_MAX)
            s_note = self._pick_voice(third_pc,   ref_s, direction, RIGHT_MIN, RIGHT_MAX)

            upper = self._sort_and_fix([t_note, a_note, s_note], RIGHT_MIN, RIGHT_MAX)
            return Chord(bass=bass, tenor=upper[0], alto=upper[1], soprano=upper[2])

        # ── ALAP HARMAS (3/5) ────────────────────────────────
        # Alaphangot kettőzzük: T=terc, A=kvint, S=alaphang
        third_pc = self._diatonic_pc_above(bass.pitch, 3)
        fifth_pc = self._diatonic_pc_above(bass.pitch, 5)

        t_note = self._pick_voice(third_pc,  ref_t, direction, RIGHT_MIN, RIGHT_MAX)
        a_note = self._pick_voice(fifth_pc,  ref_a, direction, RIGHT_MIN, RIGHT_MAX)
        s_note = self._pick_voice(bass.pitch, ref_s, direction, RIGHT_MIN, RIGHT_MAX)

        upper = self._sort_and_fix([t_note, a_note, s_note], RIGHT_MIN, RIGHT_MAX)
        return Chord(bass=bass, tenor=upper[0], alto=upper[1], soprano=upper[2])

# MIDI fájlba mentés segédfüggvény

    def save_to_midi(self, chords, filename="output.mid"):
        midi = MIDIFile(1)  # Egy sáv
        midi.addTempo(0, 0, 100)
        
        time = 0
        for chord in chords:
            duration = 2  # Alapértelmezett hossz (pl. félhang)
            for note in chord.voices():
                midi.addNote(0, 0, note.to_midi(), time, duration, 80)
            time += duration
            
        with open(filename, "wb") as output_file:
            midi.writeFile(output_file)
        print(f"--- MIDI fájl elmentve: {filename} ---")


# ─────────────────────────────────────────────
# 8. TESZT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Niedt Thorough-Bass System (diatonikus) ===\n")

    engine = NiedtRuleEngine()

    # ── 1. C-dur ────────────────────────────────────────────
    print("1. C-dur basszusvonal:")
    key_C = Key('C')
    realizer_C = ThoroughBassRealizer(key=key_C)
    bass_line_1 = [
        BassNote(Note('C', 3), Figure.from_string('')),
        BassNote(Note('D', 3), Figure.from_string('6')),
        BassNote(Note('E', 3), Figure.from_string('')),
        BassNote(Note('F', 3), Figure.from_string('')),
        BassNote(Note('G', 3), Figure.from_string('')),
        BassNote(Note('Ab', 3), Figure.from_string('6')),
        BassNote(Note('G', 3), Figure.from_string('')),
        BassNote(Note('C', 3), Figure.from_string('')),
    ]
    chords_1 = realizer_C.realize(bass_line_1)
    for i, chord in enumerate(chords_1):
        bn = bass_line_1[i]
        prev = bass_line_1[i-1] if i > 0 else None
        fig = engine.resolve_figure(bn, prev)
        print("  {} {:10s} -> {}".format(bn.note, str(fig), chord))

    print()

    # ── 2. G-dur (ellenorzes: D fole 3 = F#) ────────────────
    print("2. G-dur basszusvonal (F# ellenorzese):")
    key_G = Key('G')
    realizer_G = ThoroughBassRealizer(key=key_G)
    bass_line_2 = [
        BassNote(Note('G', 3), Figure.from_string('')),
        BassNote(Note('A', 3), Figure.from_string('6')),
        BassNote(Note('B', 3), Figure.from_string('')),
        BassNote(Note('D', 3), Figure.from_string('')),
        BassNote(Note('G', 3), Figure.from_string('')),
    ]
    chords_2 = realizer_G.realize(bass_line_2)
    for i, chord in enumerate(chords_2):
        bn = bass_line_2[i]
        prev = bass_line_2[i-1] if i > 0 else None
        fig = engine.resolve_figure(bn, prev)
        print("  {} {:10s} -> {}".format(bn.note, str(fig), chord))

    print()

    # ── 3. a-moll (= C-dur skala) ───────────────────────────
    print("3. a-moll basszusvonal (C-dur skala alapjan):")
    key_a = Key('a')
    realizer_a = ThoroughBassRealizer(key=key_a)
    bass_line_3 = [
        BassNote(Note('A', 3), Figure.from_string('')),
        BassNote(Note('B', 3), Figure.from_string('6')),
        BassNote(Note('C', 3), Figure.from_string('')),
        BassNote(Note('E', 3), Figure.from_string('7')),
        BassNote(Note('A', 3), Figure.from_string('')),
    ]
    chords_3 = realizer_a.realize(bass_line_3)
    for i, chord in enumerate(chords_3):
        bn = bass_line_3[i]
        prev = bass_line_3[i-1] if i > 0 else None
        fig = engine.resolve_figure(bn, prev)
        print("  {} {:10s} -> {}".format(bn.note, str(fig), chord))

    print()

    # ── 4. Kvartszext teszt C-durban ────────────────────────
    print("4. Kvartszext akkord C-durban (G 6/4 = C alaphang):")
    bass_line_4 = [
        BassNote(Note('C', 3), Figure.from_string('')),
        BassNote(Note('G', 3), Figure.from_string('6/4')),
        BassNote(Note('G', 3), Figure.from_string('')),
        BassNote(Note('C', 3), Figure.from_string('')),
    ]
    chords_4 = realizer_C.realize(bass_line_4)
    for i, chord in enumerate(chords_4):
        bn = bass_line_4[i]
        prev = bass_line_4[i-1] if i > 0 else None
        fig = engine.resolve_figure(bn, prev)
        print("  {} {:10s} -> {}".format(bn.note, str(fig), chord))

    print()

    # ── 5. Szólamtartomany ellenorzés ───────────────────────
    print("5. Szólamtartomany ellenorzés (A3-E5):")
    all_tests = [
        ("C-dur", chords_1), ("G-dur", chords_2),
        ("a-moll", chords_3), ("Kvartszext", chords_4)
    ]
    for name, chords in all_tests:
        ok = all(
            NiedtRuleEngine.RIGHT_HAND_MIN_MIDI <= chord.tenor.to_midi() and
            chord.soprano.to_midi() <= NiedtRuleEngine.RIGHT_HAND_MAX_MIDI and
            chord.tenor.to_midi() <= chord.alto.to_midi() <= chord.soprano.to_midi()
            for chord in chords
        )
        print("  {}: {}".format(name, "OK" if ok else "PROBLEMA"))

# MIDI fájlok generálása
    print("\nMIDI fájlok generálása...")
    realizer_C.save_to_midi(chords_1, "niedt_C_dur.mid")
    realizer_G.save_to_midi(chords_2, "niedt_G_dur.mid")