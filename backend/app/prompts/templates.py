def build_roleplay_system_prompt(
    scenario_title: str,
    scenario_description: str,
    character_description: str,
    target_language: str,
    native_language: str,
) -> str:
    # character_description already contains the full role ("You are a ..."),
    # so use it directly without adding another "You are".
    return (
        f"CRITICAL LANGUAGE RULE: You must write EXCLUSIVELY in {target_language}. "
        f"This means zero {native_language} words, zero parenthetical translations like '(word)', "
        f"zero {native_language} explanations, zero {native_language} anywhere — not even a single word. "
        f"If you include ANY {native_language} in your response, you have failed.\n\n"
        f"{character_description}\n"
        f"Scenario: {scenario_title} — {scenario_description}\n\n"
        f"Additional rules:\n"
        f"- If the user writes entirely in {native_language}, respond only with a short prompt "
        f"asking them to use {target_language}, written in {target_language}.\n"
        f"- Stay in character and keep the conversation focused on the scenario."
    )


def build_open_chat_user_prompt(target_language: str) -> str:
    return f"Begin the conversation in {target_language}."


def build_grammar_prompt(message_content: str, native_language: str) -> str:
    return (
        f"You are a language tutor. Analyse the grammar of the following sentence "
        f"and explain any errors or improvements in {native_language}.\n\n"
        f'Sentence: """{message_content}"""'
    )


def build_translation_prompt(message_content: str, native_language: str) -> str:
    return (
        f"Translate the following text into {native_language}. "
        f"Provide only the translation, no explanation.\n\n"
        f'Text: """{message_content}"""'
    )


def build_phrasing_prompt(message_content: str, target_language: str) -> str:
    return (
        f"Provide two or three natural alternative ways to express the following "
        f"in {target_language}. List each alternative on a new line.\n\n"
        f'Original: """{message_content}"""'
    )


def build_word_lookup_prompt(word: str, target_language: str, native_language: str) -> str:
    return (
        f'Look up the {target_language} word "{word}".\n'
        f"Provide: definition, part of speech, and an example sentence. "
        f"Respond in {native_language}."
    )


def build_suggestion_prompt(history_text: str, target_language: str, n: int) -> str:
    return (
        f"Given the following conversation history, suggest {n} natural "
        f"response(s) the learner could say next in {target_language}.\n"
        f"List each suggestion on a new line, numbered.\n\n"
        f"Conversation:\n{history_text}"
    )


def build_helper_system_prompt(target_language: str, native_language: str) -> str:
    return (
        f"You are a helpful language learning assistant specialising in {target_language}.\n"
        f"When explaining concepts, use {native_language} for clarity.\n"
        f"Be concise, accurate, and encouraging."
    )
