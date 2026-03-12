# Thoroughbass

A Python-based rule engine for realizing figured bass (thoroughbass / *generalbass*) according to the principles of **Friederich Erhardt Niedt** (*Musicalische Handleitung*, 1700/1710/1721).

## Overview

This project implements a systematic, rule-driven approach to four-voice thoroughbass realization. Given a bass line with figures, the engine produces soprano, alto, and tenor voices according to Niedt's explicit rules — with correct doubling, voice leading, and diatonic interval calculation in any major or minor key.

The long-term goal is a modular composition tool capable of generating baroque-style music in the manner of Bach's contemporaries, ultimately supporting fugue writing and other contrapuntal forms.

## Features

- **Full key support** — all 15 major keys and their relative minors (C, G, D, A, E, B, F#, C#, F, Bb, Eb, Ab, Db, Gb, Cb)
- **Diatonic interval calculation** — figures are interpreted within the current key, not chromatically
- **Niedt's doubling rules** — correctly implemented per chord type:
  - Root-position triad: root doubled
  - Sixth chord (6): root + fifth in upper voices; octave forbidden (Ch. VIII, Rule 2)
  - Six-four chord (6/4): fifth (= bass) doubled
  - Seventh chord (7): third added, fifth omitted (Ch. IX, Rule 1)
- **Automatic figure inference** — descending semitone step triggers sixth chord automatically (Ch. VIII, Rule 5)
- **Contrary motion** — upper voices move opposite to the bass (Ch. VI, Rules 5–6)
- **Voice range enforcement** — right hand stays within Niedt's prescribed compass (a–e²)
- **Parallel fifth/octave detection** — violations are flagged

## Project Structure

```
thoroughbass/
├── key_module.py       # Key signatures, diatonic scales, interval calculation
└── thorough_bass.py    # Note, Figure, BassNote, Chord, RuleEngine, Realizer
```

Both files must be in the same directory. `thorough_bass.py` imports from `key_module.py`.

## Requirements

- Python 3.8 or later
- No external dependencies

## Usage

```python
from key_module import Key
from thorough_bass import Note, Figure, BassNote, ThoroughBassRealizer

# Define the key
key = Key('C')           # C major
# key = Key('G')         # G major
# key = Key('a')         # A minor (uses C major scale)

# Build a bass line with figures
bass_line = [
    BassNote(Note('C', 3), Figure.from_string('')),     # unfigured = root triad
    BassNote(Note('D', 3), Figure.from_string('6')),    # sixth chord
    BassNote(Note('E', 3), Figure.from_string('')),
    BassNote(Note('F', 3), Figure.from_string('')),
    BassNote(Note('G', 3), Figure.from_string('7')),    # seventh chord
    BassNote(Note('C', 3), Figure.from_string('')),
]

# Realize
realizer = ThoroughBassRealizer(key=key)
chords = realizer.realize(bass_line)

for chord in chords:
    print(chord)
# Example output:
# Chord(S:C5 A:G4 T:E4 B:C3)
# Chord(S:B4 A:F4 T:B3 B:D3)
# ...
```

### Figure notation

Figures are written as slash-separated integers:

| Figure string | Meaning |
|---|---|
| `''` | Unfigured (root-position triad) |
| `'6'` | Sixth chord (first inversion) |
| `'6/4'` | Six-four chord (second inversion) |
| `'7'` | Seventh chord |
| `'6/5'` | Six-five chord |

### Key notation

| Key string | Meaning |
|---|---|
| `'C'` | C major |
| `'G'` | G major |
| `'Bb'` | B-flat major |
| `'a'` | A minor (relative: C major) |
| `'e'` | E minor (relative: G major) |
| `'g'` | G minor (relative: B-flat major) |

Uppercase = major, lowercase = minor.

## Theoretical basis

The rules implemented in this engine are drawn directly from Niedt's *Musicalische Handleitung* (translated by Poulin & Taylor, Clarendon Press, 1989):

- **Part I, Chapter VI** — General rules for thoroughbass playing (voice ranges, contrary motion, parallel fifths/octaves)
- **Part I, Chapter VII** — Unfigured bass
- **Part I, Chapter VIII** — Figured bass (12 rules covering sixth chords, chromatic alterations, suspensions, passing notes)
- **Part I, Chapter IX** — Seventh, ninth, and eleventh chords (preparation rules)

Bach himself edited and expanded Niedt's rules in his own thoroughbass precepts (*Vorschriften und Grundsätze*, c. 1738). The footnotes in the Poulin/Taylor translation document these differences; future versions of this project may offer a "Bach mode" alongside the Niedt defaults.

## Roadmap

- [ ] Chromatic alterations in figures (#3, b6, etc.)
- [ ] Suspension chains (7–6, 4–3, 9–8)
- [ ] Tierce de Picardie (Rule 6, Ch. VIII) — major third on final chord
- [ ] Additional treatise modes: St. Lambert, Handel, Bach
- [ ] MIDI output
- [ ] MusicXML / ABC notation export
- [ ] Web interface

## License

MIT

## Authors

Developed in collaboration by **Attila Roeckl** and **Claude** (Anthropic).
Development in progress. Contributions welcome.
