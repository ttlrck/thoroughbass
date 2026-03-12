"""
Key Module - Hangnem-modul
Niedt Thorough-Bass System

Feladata:
  - Az összes dúr és moll hangnem előjegyzésének tárolása
  - Diatonikus skála meghatározása adott hangnemhez
  - Diatonikus intervallum számítás (basszushang + figura -> célhang)
  - Kromatikus alterációk kezelése (#, b módosítók a figurákban)

Alapelv:
  Minden hangnem (dúr és moll egyaránt) egy dúr előjegyzéshez kötődik.
  A moll hangnemek a párhuzamos dúr skáláját használják alapként.
  Pl. a-moll = C-dúr skála, e-moll = G-dúr skála, stb.
"""

# ─────────────────────────────────────────────
# 1. ELŐJEGYZÉSEK
# ─────────────────────────────────────────────

# A keresztek sorrendben (kvintköre felfelé)
SHARPS_ORDER = ['F#', 'C#', 'G#', 'D#', 'A#', 'E#', 'B#']

# A bések sorrendben (kvintköre lefelé)
FLATS_ORDER  = ['Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb']

# Dúr hangnemek -> előjegyzés lista
KEY_SIGNATURES = {
    # Keresztes hangnemek
    'C':  [],
    'G':  ['F#'],
    'D':  ['F#', 'C#'],
    'A':  ['F#', 'C#', 'G#'],
    'E':  ['F#', 'C#', 'G#', 'D#'],
    'B':  ['F#', 'C#', 'G#', 'D#', 'A#'],
    'F#': ['F#', 'C#', 'G#', 'D#', 'A#', 'E#'],
    'C#': ['F#', 'C#', 'G#', 'D#', 'A#', 'E#', 'B#'],
    # Bés hangnemek
    'F':  ['Bb'],
    'Bb': ['Bb', 'Eb'],
    'Eb': ['Bb', 'Eb', 'Ab'],
    'Ab': ['Bb', 'Eb', 'Ab', 'Db'],
    'Db': ['Bb', 'Eb', 'Ab', 'Db', 'Gb'],
    'Gb': ['Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb'],
    'Cb': ['Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Fb'],
}

# Moll hangnem -> párhuzamos dúr
RELATIVE_MAJOR = {
    # Keresztes molok
    'a':  'C',
    'e':  'G',
    'b':  'D',
    'f#': 'A',
    'c#': 'E',
    'g#': 'B',
    'd#': 'F#',
    'a#': 'C#',
    # Bés molok
    'd':  'F',
    'g':  'Bb',
    'c':  'Eb',
    'f':  'Ab',
    'bb': 'Db',
    'eb': 'Gb',
    'ab': 'Cb',
}

# C-dúr alap skála (fehér billentyűk sorrendben)
C_MAJOR_SCALE = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

# Az alaphangok sorrendje a dúr skálában (C-től indulva)
# Megmutatja, melyik fokra esik az egyes hangok
SCALE_DEGREE_ORDER = {
    'C': 0, 'D': 1, 'E': 2, 'F': 3,
    'G': 4, 'A': 5, 'B': 6
}


# ─────────────────────────────────────────────
# 2. KEY osztály
# ─────────────────────────────────────────────

class Key:
    """
    Egyetlen hangnem reprezentációja.
    Megadható dúrban (pl. 'C', 'G', 'F#') vagy mollban (pl. 'a', 'e', 'f#').
    """

    def __init__(self, key_name):
        """
        key_name: pl. 'C', 'G', 'Bb', 'a', 'e', 'f#'
        Nagy betű = dúr, kis betű = moll.
        """
        self.key_name = key_name
        self.is_minor = key_name[0].islower()

        # A párhuzamos dúr meghatározása
        if self.is_minor:
            self.relative_major = RELATIVE_MAJOR.get(key_name)
            if self.relative_major is None:
                raise ValueError("Ismeretlen moll hangnem: {}".format(key_name))
            self.major_key = self.relative_major
        else:
            if key_name not in KEY_SIGNATURES:
                raise ValueError("Ismeretlen dúr hangnem: {}".format(key_name))
            self.major_key = key_name

        # Előjegyzés lista
        self.accidentals = KEY_SIGNATURES[self.major_key]

        # Diatonikus skála (7 hang, módosítókkal)
        self.scale = self._build_scale()

    def _build_scale(self):
        """
        Felépíti a diatonikus skálát az előjegyzés alapján.
        Visszaad egy 7 elemű listát: ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        módosítókkal, pl. G-dúrban: ['G', 'A', 'B', 'C', 'D', 'E', 'F#']
        """
        # Az alap C-dúr skálából indulunk
        base = C_MAJOR_SCALE[:]

        # Módosítjuk az előjegyzés szerint
        modified = []
        for note in base:
            # Megnézzük, hogy ez a hang módosítva van-e
            modified_note = note
            for acc in self.accidentals:
                # acc pl. 'F#' -> az alaphang 'F', módosító '#'
                acc_base = acc[0]
                acc_mod  = acc[1]
                if note == acc_base:
                    modified_note = acc
                    break
            modified.append(modified_note)

        # A skálát a tonika fokától rendezzük
        # (pl. G-dúr: G, A, B, C, D, E, F#)
        tonic = self.major_key[0]  # pl. 'G'
        tonic_idx = SCALE_DEGREE_ORDER.get(tonic, 0)
        rotated = modified[tonic_idx:] + modified[:tonic_idx]

        return rotated

    def diatonic_note(self, root_pitch, interval):
        """
        Adott hangból (root_pitch) felfelé számítva a diatonikus intervallum
        (1=unisono, 2=szekund, ... 8=oktáv) célhangját adja vissza
        pitch class-ként (string).

        Pl. Key('C').diatonic_note('C', 3) -> 'E'
            Key('G').diatonic_note('D', 3) -> 'F#'
            Key('C').diatonic_note('D', 6) -> 'B'
        """
        # Oktávon túli intervallumot visszavetítjük
        simple = interval
        while simple > 8:
            simple -= 7
        if simple < 1:
            simple = 1

        # Megkeressük a root_pitch helyzetét a skálában
        root_base = root_pitch[0] if len(root_pitch) > 1 else root_pitch
        # Normalizálás: a skálában mindig az alaphangra figyelünk
        # (a módosítót figyelmen kívül hagyjuk a pozíció kereséskor)
        root_pos = None
        for i, note in enumerate(self.scale):
            note_base = note[0] if len(note) > 1 else note
            if note_base == root_base:
                root_pos = i
                break

        if root_pos is None:
            # Ha nem találjuk a skálában (kromatikus hang),
            # a C-dúr skálából keresünk
            root_pos = SCALE_DEGREE_ORDER.get(root_base, 0)

        # A célhang pozíciója a skálában (0-alapú, ezért -1)
        target_pos = (root_pos + simple - 1) % 7

        return self.scale[target_pos]

    def semitones_for_interval(self, root_pitch, interval):
        """
        Az adott diatonikus intervallum félhangokban mért nagysága
        az adott hangnemben.

        Pl. Key('C').semitones_for_interval('C', 3) -> 4 (nagy terc)
            Key('a').semitones_for_interval('E', 3) -> 4 (nagy terc, E-dúr tercből)
            Key('C').semitones_for_interval('D', 3) -> 3 (kis terc, d-moll terc)
        """
        from thoroughbass.thorough_bass import pitch_to_semitone
        target = self.diatonic_note(root_pitch, interval)
        root_semi  = pitch_to_semitone(root_pitch)
        target_semi = pitch_to_semitone(target)
        diff = target_semi - root_semi
        if diff < 0:
            diff += 12
        return diff

    def __repr__(self):
        mode = 'moll' if self.is_minor else 'dur'
        return "Key({}, {}, skala: {})".format(
            self.key_name, mode, self.scale)


# ─────────────────────────────────────────────
# 3. TESZT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("=== Key Module teszt ===\n")

    # Dúr hangnemek skálái
    print("Dur hangnemek skalai:")
    for k in ['C', 'G', 'D', 'F', 'Bb', 'Eb']:
        key = Key(k)
        print("  {}-dur: {}".format(k, key.scale))

    print()

    # Moll hangnemek (párhuzamos dúr skálájával)
    print("Moll hangnemek skalai (paralel dur alapjan):")
    for k in ['a', 'e', 'b', 'd', 'g']:
        key = Key(k)
        print("  {}-moll (= {}-dur): {}".format(
            k, key.major_key, key.scale))

    print()

    # Diatonikus intervallum számítás
    print("Diatonikus intervallum szamitas:")
    tests = [
        ('C', 'C', 3),   # C-durban C fole terc = E
        ('C', 'C', 5),   # C-durban C fole kvint = G
        ('C', 'D', 6),   # C-durban D fole szext = B
        ('G', 'D', 3),   # G-durban D fole terc = F#
        ('G', 'G', 7),   # G-durban G fole szeptim = F#
        ('F', 'F', 3),   # F-durban F fole terc = A
        ('F', 'B', 5),   # F-durban Bb fole kvint = F (!)
        ('Bb','Bb', 3),  # Bb-durban Bb fole terc = D
    ]
    for key_name, root, interval in tests:
        key = Key(key_name)
        result = key.diatonic_note(root, interval)
        semis  = key.semitones_for_interval(root, interval)
        print("  {}-dur: {} fole {} = {} ({} felhang)".format(
            key_name, root, interval, result, semis))

    print()

    # Teljes hangnemkészlet ellenőrzése
    print("Teljes hangnemkeszlet - skalak helyessege:")
    all_keys = (
        list(KEY_SIGNATURES.keys()) +
        list(RELATIVE_MAJOR.keys())
    )
    for k in all_keys:
        try:
            key = Key(k)
            # Ellenőrzés: a skálának 7 különböző hangból kell állnia
            bases = [n[0] for n in key.scale]
            ok = len(set(bases)) == 7
            print("  {}: {} {}".format(
                k, key.scale, "OK" if ok else "HIBA"))
        except Exception as ex:
            print("  {}: HIBA - {}".format(k, ex))
