# Contract: language pack format

**Feature**: [../spec.md](../spec.md) | **Research**: R4, R5 | **Data model**: [../data-model.md](../data-model.md)

A pack is a UTF-8 TOML file. `scaffold` writes a full pack. `backfill` writes a partial pack holding
only the missing items. The agent edits only the values. Comments are guidance and are ignored when
the pack is read.

## Keys

| Key | Type | Producer | In a scaffolded pack |
|---|---|---|---|
| `code` | string | derived | filled |
| `name` | string | agent | filled from `--name` |
| `default_voice` | string | chosen | `"TODO"` |
| `[[voices]]` `key` | string | chosen | none: candidates listed in a comment |
| `[[voices]]` `gender` | `"female"` \| `"male"` | agent | |
| `[[voices]]` `speaking_rate` | `"natural"` \| `"fast"` \| `"slow"` | agent | `"natural"` when omitted |
| `[[voices]]` `display_name` | string, 1–40 characters | agent, optional | absent: derived as `"<Name> (<country_english>)"` |
| `[podcast.host_names]` `<gender>` | array of strings | agent | `[]` per gender |
| `[podcast]` `guest_labels` | array of strings | agent | `[]` |
| `[podcast]` `sample_line` | string | agent | `"TODO"` |
| `[evaluation]` `special_letters` | string | agent | `"TODO"` |
| `[evaluation]` `loanwords` | array of strings | agent | `[]` |
| `[evaluation]` `dictation` | array of strings | agent | `[]` |
| `[evaluation.turns]` `<scenario-id>` | array of strings | agent | `[]` for **every current scenario** |

`order`, and each voice's `locale` and `quality`, are **never** in a pack. They are derived at
`apply` (research R5). A pack that sets them gets an error: "derived by the kit; remove it". A
voice's `display_name` is derived too, from the catalogue's voice name and country ("Paola (Italy)"),
but a pack may set it to override a name that reads badly: the catalogue calls Spanish's
`es_ES-davefx-medium` voice `davefx`, and the app shows "David (Spain)". Any key not in the registry is an error naming it, which catches typos such as `guest_label`.
`"TODO"` and empty arrays fail their rules, so an unfilled pack never validates.

## Guidance comments

Before each key, `scaffold` writes:

```toml
# ── podcast.sample_line ─────────────────────────────── agent · needed by 007
# What a podcast host says when the learner previews their voice.
# Rules: contains {name} exactly once; no other braces.
# Example (German): "Hallo, ich bin {name}. Willkommen zur Sendung!"
sample_line = "TODO"
```

The example comes from the first catalogued language whose data passes that item. German is
preferred, being the most recent.

## Example: a filled Italian pack (abridged)

```toml
code = "it"
name = "Italian"
default_voice = "it_IT-paola-medium"

[[voices]]
key = "it_IT-paola-medium"
gender = "female"

[[voices]]
key = "it_IT-riccardo-x_low"
gender = "male"

[podcast]
guest_labels = ["Ospite", "Ascoltatore", "Ascoltatrice", "Conduttore", "Conduttrice"]
sample_line = "Ciao, sono {name}. Benvenuti al programma!"

[podcast.host_names]
female = ["Giulia", "Chiara", "Francesca", "Sara", "Martina", "Elena", "Alessia", "Valentina", "Federica", "Silvia"]
male = ["Marco", "Luca", "Matteo", "Andrea", "Davide", "Simone", "Lorenzo", "Paolo", "Stefano", "Giorgio"]

[evaluation]
special_letters = "àèéìòù"
loanwords = ["hotel", "taxi", "ok", "bar", "sport"]
dictation = [
  "Perché il treno è in ritardo oggi?",
  # … 19 more, each with at least one of àèéìòù
]

[evaluation.turns]
buy-train-ticket = [
  "Buongiorno, vorrei un biglietto per Roma.",
  # … 4 more
]
# … one key for every scenario
```

## Partial (backfill) packs

They have the same keys, but only those that are missing or failing are present. `code` is always
present. A partial pack for Spanish written when the kit ships holds only `[evaluation]` and
`[evaluation.turns]`. Applying merges by key: an item present in the pack replaces that item, and
every other item is kept byte-for-byte in the rendered files.
