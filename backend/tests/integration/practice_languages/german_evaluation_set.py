"""The fixed German evaluation set for the SC-002 and SC-003 benchmarks (research R8, R14).

`GERMAN_TURNS` holds 5 correct, simple learner turns for each of the 10 scenarios. `DICTATION_SENTENCES`
holds 20 sentences, each with at least one of ä, ö, ü or ß, for the transcription benchmark.
"""

GERMAN_TURNS: dict[str, tuple[str, ...]] = {
    "buy-train-ticket": (
        "Guten Tag, ich brauche eine Fahrkarte nach Berlin.",
        "Ich möchte morgen früh fahren.",
        "Hin und zurück, bitte.",
        "Gibt es einen Rabatt für Studenten?",
        "Von welchem Gleis fährt der Zug?",
    ),
    "check-into-hotel": (
        "Guten Abend, ich habe ein Zimmer reserviert.",
        "Mein Name ist Anna Schmidt.",
        "Ich bleibe drei Nächte.",
        "Ist das Frühstück im Preis enthalten?",
        "Wann muss ich das Zimmer verlassen?",
    ),
    "order-at-restaurant": (
        "Guten Tag, einen Tisch für zwei Personen, bitte.",
        "Können wir bitte die Speisekarte haben?",
        "Ich nehme die Suppe und danach den Fisch.",
        "Zu trinken hätte ich gern ein Wasser.",
        "Die Rechnung, bitte.",
    ),
    "call-doctors-office": (
        "Guten Morgen, ich möchte einen Termin machen.",
        "Ich habe seit zwei Tagen Kopfschmerzen.",
        "Ich habe auch ein bisschen Fieber.",
        "Geht es heute Nachmittag?",
        "Vielen Dank, bis später.",
    ),
    "ask-for-directions": (
        "Entschuldigung, wo ist der Bahnhof?",
        "Ist das weit von hier?",
        "Muss ich an der Ampel links gehen?",
        "Kann ich auch mit dem Bus fahren?",
        "Danke schön, das ist sehr nett.",
    ),
    "job-interview": (
        "Guten Tag, ich freue mich auf das Gespräch.",
        "Ich habe drei Jahre in einem Büro gearbeitet.",
        "Ich arbeite gern im Team.",
        "Ich spreche Englisch und ein wenig Deutsch.",
        "Wann kann ich mit einer Antwort rechnen?",
    ),
    "rent-a-car": (
        "Guten Tag, ich möchte ein Auto mieten.",
        "Ich brauche es für eine Woche.",
        "Ein kleines Auto reicht mir.",
        "Ist die Versicherung inklusive?",
        "Wo kann ich das Auto zurückgeben?",
    ),
    "visit-pharmacy": (
        "Guten Tag, ich habe Halsschmerzen.",
        "Haben Sie etwas gegen Husten?",
        "Wie oft soll ich die Tabletten nehmen?",
        "Brauche ich dafür ein Rezept?",
        "Was kostet das zusammen?",
    ),
    "report-lost-item": (
        "Guten Tag, ich habe meine Tasche verloren.",
        "Sie ist schwarz und ziemlich groß.",
        "Ich war heute Morgen im Park.",
        "In der Tasche sind mein Handy und mein Schlüssel.",
        "Bitte rufen Sie mich an, wenn Sie sie finden.",
    ),
    "board-airplane": (
        "Guten Tag, hier ist meine Bordkarte.",
        "Wo ist mein Platz?",
        "Kann ich meine Tasche hier oben lassen?",
        "Darf ich bitte ein Glas Wasser haben?",
        "Wann landen wir in München?",
    ),
}

DICTATION_SENTENCES: tuple[str, ...] = (
    "Ich hätte gern einen Kaffee und ein Stück Kuchen, bitte.",
    "Die Straße ist heute sehr ruhig.",
    "Können Sie mir bitte helfen?",
    "Mein Zug fährt um neun Uhr.",
    "Wir müssen noch Brot und Käse kaufen.",
    "Das Hotel liegt direkt am Fluss, gegenüber dem Park.",
    "Ich möchte ein Zimmer für zwei Nächte.",
    "Der Schlüssel liegt auf dem Tisch.",
    "Meine Schwester wohnt in München.",
    "Es ist schön, Sie kennenzulernen.",
    "Wie groß ist die Wohnung?",
    "Morgens trinke ich gern Tee, später ein großes Glas Saft.",
    "Die Tür ist leider geschlossen.",
    "Mein Bruder spielt jeden Samstag Fußball.",
    "Wir fahren im Sommer an die Küste.",
    "Ich habe meine Brille in der Küche vergessen.",
    "Das Frühstück ist im Preis enthalten.",
    "Kannst du bitte das Fenster öffnen?",
    "Die Äpfel sind heute besonders süß.",
    "Um wie viel Uhr öffnet die Bäckerei?",
)

LOANWORD_ALLOWLIST: frozenset[str] = frozenset({"hotel", "taxi", "ticket", "ok"})
"""Standard German words that are also common in English; never counted as foreign (R8)."""
