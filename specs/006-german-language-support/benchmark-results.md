# Benchmark results (006)

Hand-run on 2026-09-27: RTX 3070 Ti, `llama3.1:8b` through Ollama, faster-whisper 1.2.1, Piper.

## SC-002: German replies (target: ≥ 95% of 50)

`llama3.1:8b`, Natural level, 10 scenarios × 5 scripted German turns: **50/50 replies with no
English or Spanish word — met.** Empty replies count as failures. Nothing was flagged, so the review
sheet (`german-review-sheet.md`) has no rows to judge. First three replies, for the record:

- "Guten Tag, ich brauche eine Fahrkarte nach Berlin." → "Guten Tag! Eine Fahrt nach Berlin? Wohin genau möchten Sie fahren? …"
- "Ich möchte morgen früh fahren." → "Morgen früh also? Das ist kein Problem. Unsere Züge verkehren regelmäßig. …"
- "Hin und zurück, bitte." → "Ein Hin- und Rückfahrschein also! Dafür benötige ich Ihre Ausweispapiere, bitte. …"

The purity check uses a refined rule (see `text_purity.py` and research R8): R8's first sketch,
"rare in German", missed English words because wordfreq's German list carries them ("the" is 5.6).

## SC-003: German transcription (target: ≥ 18/20)

Audio source: each dictation sentence synthesised by Piper, resampled to 16 kHz mono.

| Whisper model | Kerstin (low), as specified | Thorsten (medium), diagnostic |
|---|---|---|
| base (the default) | 13/20 | 14/20 |
| small | 16/20 | 17/20 |
| medium | 17/20 | not run |

**Not met** on any model. Misses are almost all a single umlaut word. Kerstin's ü is misheard on every model ("Stück" → "Steck", "Schlüssel" → "Schlasse"/"Schlosser", "München" → "Männchen"), so the low-quality synthetic voice is part of the gap; a real speaker has not been measured.

### base, Kerstin (the specified run)

| # | Sentence | Transcript | WER | Pass |
|---|---|---|---|---|
| 1 | Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte. | Ich hätte gern eine Kaffe und ein Stück Kuchen bitte. | 20% | True |
| 2 | Die Straße ist heute sehr ruhig. | Die Straße ist heute sehr ruhig. | 0% | True |
| 3 | Können Sie mir bitte helfen? | Können Sie mir bitte helfen. | 0% | True |
| 4 | Mein Zug fährt um neun Uhr. | Ein Zug fährt um 9 Uhr. | 33% | False |
| 5 | Wir müssen noch Brot und Käse kaufen. | Wir müssen noch beruht um Käse kaufen. | 29% | False |
| 6 | Das Hotel liegt direkt am Fluss, gegenüber dem Park. | Das Hote liegt direkt am Fluss gegenüber dem Park. | 11% | True |
| 7 | Ich möchte ein Zimmer für zwei Nächte. | Ich möchte ein Zimmer für zwei Nächte. | 0% | True |
| 8 | Der Schlüssel liegt auf dem Tisch. | Der Schlaste liegt auf dem Tisch. | 17% | False |
| 9 | Meine Schwester wohnt in München. | Eine Schwester wohnt in Männchen. | 40% | False |
| 10 | Es ist schön, Sie kennenzulernen. | Es ist schön, sie kennen Zulernen. | 40% | False |
| 11 | Wie groß ist die Wohnung? | Wie groß ist die Wohnungen? | 20% | True |
| 12 | Morgens trinke ich gern Tee, später ein großes Glas Saft. | Mums trinke ich gern tief, später ein großes Glas saft. | 20% | True |
| 13 | Die Tür ist leider geschlossen. | Die Tür ist leider geschlossen. | 0% | True |
| 14 | Mein Bruder spielt jeden Samstag Fußball. | Mein Bruder spielt jeden Samstag Fußball. | 0% | True |
| 15 | Wir fahren im Sommer an die Küste. | Wir fahren im Sommer an die Koster. | 14% | False |
| 16 | Ich habe meine Brille in der Küche vergessen. | Ich habe meine Brülle in der Küche vergessen. | 12% | True |
| 17 | Das Frühstück ist im Preis enthalten. | Das Frühstück ist im Preis enthalten. | 0% | True |
| 18 | Kannst du bitte das Fenster öffnen? | kannst du bitte das Fenster öffnen. | 0% | True |
| 19 | Die Äpfel sind heute besonders süß. | Die Apfils sind heute besonders süß. | 17% | False |
| 20 | Um wie viel Uhr öffnet die Bäckerei? | Um wie viel Uhr öffnet die Bäckerei. | 0% | True |

### small, Kerstin

| # | Sentence | Transcript | WER | Pass |
|---|---|---|---|---|
| 1 | Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte. | Ich hätte gerne einen Kaffee und einen Steck Kuchen, bitte. | 30% | False |
| 2 | Die Straße ist heute sehr ruhig. | Die Straße ist heute sehr ruhig. | 0% | True |
| 3 | Können Sie mir bitte helfen? | Können Sie mir bitte helfen. | 0% | True |
| 4 | Mein Zug fährt um neun Uhr. | Mein Zug fährt um 9 Uhr. | 17% | True |
| 5 | Wir müssen noch Brot und Käse kaufen. | Wir müssen noch Brot und Käse kaufen. | 0% | True |
| 6 | Das Hotel liegt direkt am Fluss, gegenüber dem Park. | Das Hotel liegt direkt am Fluss gegenüber dem Park. | 0% | True |
| 7 | Ich möchte ein Zimmer für zwei Nächte. | Ich möchte ein Zimmer für zwei Nächte. | 0% | True |
| 8 | Der Schlüssel liegt auf dem Tisch. | Der Schlasse liegt auf dem Tisch. | 17% | False |
| 9 | Meine Schwester wohnt in München. | Meine Schwester wohnt in Männchen. | 20% | False |
| 10 | Es ist schön, Sie kennenzulernen. | Er ist schön, Sie können zu lernen. | 80% | False |
| 11 | Wie groß ist die Wohnung? | Wie groß ist die Wohnung? | 0% | True |
| 12 | Morgens trinke ich gern Tee, später ein großes Glas Saft. | Morgens trinke ich Gentti, später ein großes Glas Saft. | 20% | True |
| 13 | Die Tür ist leider geschlossen. | Die Tür ist leider geschlossen. | 0% | True |
| 14 | Mein Bruder spielt jeden Samstag Fußball. | Mein Bruder spielt jeden Samstag Fußball. | 0% | True |
| 15 | Wir fahren im Sommer an die Küste. | Wir fahren im Sommer an die Küste. | 0% | True |
| 16 | Ich habe meine Brille in der Küche vergessen. | Ich habe meine Brille in der Küche vergessen. | 0% | True |
| 17 | Das Frühstück ist im Preis enthalten. | Das Frühstück ist dem Preis enthalten. | 17% | True |
| 18 | Kannst du bitte das Fenster öffnen? | Kannst du bitte das Fenster öffnen? | 0% | True |
| 19 | Die Äpfel sind heute besonders süß. | Die Äpfel sind heute besonders süß. | 0% | True |
| 20 | Um wie viel Uhr öffnet die Bäckerei? | um wie viel Uhr öffnet die Bäckerei. | 0% | True |

### medium, Kerstin

| # | Sentence | Transcript | WER | Pass |
|---|---|---|---|---|
| 1 | Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte. | Ich hätte gerne einen Kaffee und einen Steck Kuchen, bitte. | 30% | False |
| 2 | Die Straße ist heute sehr ruhig. | Die Straße ist heute sehr ruhig. | 0% | True |
| 3 | Können Sie mir bitte helfen? | Können Sie mir bitte helfen? | 0% | True |
| 4 | Mein Zug fährt um neun Uhr. | Mein Zug fährt um 9 Uhr. | 17% | True |
| 5 | Wir müssen noch Brot und Käse kaufen. | Wir müssen noch Brot und Käse kaufen. | 0% | True |
| 6 | Das Hotel liegt direkt am Fluss, gegenüber dem Park. | Das Hotel liegt direkt am Fluss gegenüber dem Park. | 0% | True |
| 7 | Ich möchte ein Zimmer für zwei Nächte. | Ich möchte ein Zimmer für zwei Nächte. | 0% | True |
| 8 | Der Schlüssel liegt auf dem Tisch. | Der Schlosser liegt auf dem Tisch. | 17% | False |
| 9 | Meine Schwester wohnt in München. | Meine Schwester wohnt in Männchen. | 20% | False |
| 10 | Es ist schön, Sie kennenzulernen. | Es ist schön, Sie kennenzulernen. | 0% | True |
| 11 | Wie groß ist die Wohnung? | Wie groß ist die Wohnung? | 0% | True |
| 12 | Morgens trinke ich gern Tee, später ein großes Glas Saft. | Morgens trinke ich gern Tee, später ein großes Glas Saft. | 0% | True |
| 13 | Die Tür ist leider geschlossen. | Die Tür ist leider geschlossen. | 0% | True |
| 14 | Mein Bruder spielt jeden Samstag Fußball. | Mein Bruder spielt jeden Samstag Fußball. | 0% | True |
| 15 | Wir fahren im Sommer an die Küste. | Wir fahren im Sommer an die Küste. | 0% | True |
| 16 | Ich habe meine Brille in der Küche vergessen. | Ich habe meine Brille in der Küche vergessen. | 0% | True |
| 17 | Das Frühstück ist im Preis enthalten. | Das Frühstück ist im Preis enthalten. | 0% | True |
| 18 | Kannst du bitte das Fenster öffnen? | Kannst du bitte das Fenster öffnen? | 0% | True |
| 19 | Die Äpfel sind heute besonders süß. | Die Äpfel sind heute besonders süß. | 0% | True |
| 20 | Um wie viel Uhr öffnet die Bäckerei? | Um wie viel Uhr öffnet die Bäckerei? | 0% | True |

## FR-026: German on Claude (T069)

`pytest -m claude_live tests/live -k german` (Claude Code 2.1.283, Sonnet, low effort): **passed**.
The reply to "Guten Abend, einen Tisch für zwei Personen, bitte." was non-empty and had no flagged
English or Spanish word.

## US4: the chosen German voice speaks the next reply (T099)

Real backend on an isolated database, real Ollama and Piper. After
`PUT /api/settings {"target_language": "de", "tts_voice": "de_DE-kerstin-low"}`, a new
Order-at-a-Restaurant conversation opened in German ("Willkommen im Restaurant! …"), and
`GET /api/audio/tts/1` returned a 5.5 s WAV at **16,000 Hz**, which is Kerstin (Thorsten is
22,050 Hz). Listening by ear was not possible in this session.
