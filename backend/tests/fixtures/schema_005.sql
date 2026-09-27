-- Frozen pre-006 schema: the output of init_db() at commit 329cf72
-- ("feat(levels): add conversation difficulty levels"), the 005 release.
-- Used by the SC-005 upgrade tests to build a "before" database without the
-- live ORM metadata, which already holds the 006 tables and columns.
-- Do not edit: regenerate from that commit if it is ever needed again.
CREATE TABLE decks (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	practice_mode VARCHAR(30) NOT NULL, 
	algorithm VARCHAR(30) NOT NULL, 
	requested_size INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_practiced_at DATETIME, 
	PRIMARY KEY (id)
);
CREATE TABLE app_settings (
	id INTEGER NOT NULL, 
	llm_provider VARCHAR(20) NOT NULL, 
	llm_model VARCHAR(100) NOT NULL, 
	llm_effort VARCHAR(10) NOT NULL, 
	target_language VARCHAR(20) NOT NULL, 
	native_language VARCHAR(20) NOT NULL, 
	tts_voice VARCHAR(200) NOT NULL, 
	suggestion_count INTEGER NOT NULL, 
	whisper_model VARCHAR(50) NOT NULL, 
	correction_mode VARCHAR(10) NOT NULL, 
	conversation_level VARCHAR(12) NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE conversations (
	id INTEGER NOT NULL, 
	scenario_id VARCHAR(100) NOT NULL, 
	scenario_title VARCHAR(200) NOT NULL, 
	target_language VARCHAR(20) NOT NULL, 
	native_language VARCHAR(20) NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	started_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	llm_model VARCHAR(100) NOT NULL, 
	custom_prompt TEXT, 
	PRIMARY KEY (id)
);
CREATE TABLE conversation_correction_state (
	conversation_id INTEGER NOT NULL, 
	consecutive_corrected_attempts INTEGER NOT NULL, 
	awaiting_clarification BOOLEAN NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (conversation_id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);
CREATE TABLE practice_sessions (
	id INTEGER NOT NULL, 
	deck_id INTEGER, 
	practice_mode VARCHAR(30) NOT NULL, 
	algorithm VARCHAR(30) NOT NULL, 
	started_at DATETIME NOT NULL, 
	ended_at DATETIME, 
	total_cards INTEGER NOT NULL, 
	cards_reviewed INTEGER NOT NULL, 
	knew_it_count INTEGER NOT NULL, 
	guessed_count INTEGER NOT NULL, 
	didnt_know_count INTEGER NOT NULL, 
	completed BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(deck_id) REFERENCES decks (id) ON DELETE SET NULL
);
CREATE INDEX idx_sessions_deck ON practice_sessions (deck_id);
CREATE INDEX idx_sessions_started ON practice_sessions (started_at);
CREATE TABLE messages (
	id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	role VARCHAR(9) NOT NULL, 
	content TEXT NOT NULL, 
	input_source VARCHAR(8), 
	created_at DATETIME NOT NULL, 
	tts_audio_path VARCHAR(500), 
	transcription_confidence FLOAT, 
	is_low_confidence BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);
CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);
CREATE TABLE vocabulary_items (
	id INTEGER NOT NULL, 
	word VARCHAR(500) NOT NULL, 
	translation VARCHAR(500) NOT NULL, 
	target_language VARCHAR(20) NOT NULL, 
	native_language VARCHAR(20) NOT NULL, 
	source_conversation_id INTEGER, 
	saved_at DATETIME NOT NULL, 
	classification VARCHAR(20) NOT NULL, 
	manual_override BOOLEAN NOT NULL, 
	tts_cache_path VARCHAR(500), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_vocabulary_word_lang UNIQUE (word, target_language), 
	FOREIGN KEY(source_conversation_id) REFERENCES conversations (id) ON DELETE SET NULL
);
CREATE TABLE message_feedback (
	id INTEGER NOT NULL, 
	message_id INTEGER NOT NULL, 
	kind VARCHAR(14) NOT NULL, 
	category VARCHAR(11), 
	error_fragment TEXT, 
	corrected_text TEXT, 
	explanation TEXT NOT NULL, 
	mode VARCHAR(6) NOT NULL, 
	rank INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE CASCADE
);
CREATE INDEX ix_message_feedback_message_id ON message_feedback (message_id);
CREATE TABLE deck_cards (
	id INTEGER NOT NULL, 
	deck_id INTEGER NOT NULL, 
	vocabulary_item_id INTEGER, 
	position INTEGER NOT NULL, 
	fill_blank_sentence VARCHAR(1000), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_deck_card_position UNIQUE (deck_id, position), 
	FOREIGN KEY(deck_id) REFERENCES decks (id) ON DELETE CASCADE, 
	FOREIGN KEY(vocabulary_item_id) REFERENCES vocabulary_items (id) ON DELETE SET NULL
);
CREATE INDEX idx_deck_cards_deck ON deck_cards (deck_id);
CREATE TABLE card_results (
	id INTEGER NOT NULL, 
	session_id INTEGER NOT NULL, 
	vocabulary_item_id INTEGER, 
	rating VARCHAR(20) NOT NULL, 
	response_type VARCHAR(10), 
	user_response TEXT, 
	rated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES practice_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(vocabulary_item_id) REFERENCES vocabulary_items (id) ON DELETE SET NULL
);
CREATE INDEX idx_card_results_session ON card_results (session_id);
CREATE INDEX idx_card_results_vocab ON card_results (vocabulary_item_id);
CREATE TABLE flashcard_rating_history (
	id INTEGER NOT NULL, 
	vocabulary_item_id INTEGER NOT NULL, 
	rating VARCHAR(20) NOT NULL, 
	rated_at DATETIME NOT NULL, 
	session_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(vocabulary_item_id) REFERENCES vocabulary_items (id) ON DELETE CASCADE, 
	FOREIGN KEY(session_id) REFERENCES practice_sessions (id) ON DELETE CASCADE
);
CREATE INDEX idx_rating_history_vocab ON flashcard_rating_history (vocabulary_item_id, rated_at);
CREATE TABLE word_llm_cache (
	id INTEGER NOT NULL, 
	vocabulary_item_id INTEGER NOT NULL, 
	cache_type VARCHAR(20) NOT NULL, 
	language VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	generated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_llm_cache_word_type_lang UNIQUE (vocabulary_item_id, cache_type, language), 
	FOREIGN KEY(vocabulary_item_id) REFERENCES vocabulary_items (id) ON DELETE CASCADE
);
CREATE TABLE spaced_repetition_schedule (
	id INTEGER NOT NULL, 
	vocabulary_item_id INTEGER NOT NULL, 
	interval_stage INTEGER NOT NULL, 
	last_practiced_at DATETIME, 
	next_due_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_srs_vocab_item UNIQUE (vocabulary_item_id), 
	FOREIGN KEY(vocabulary_item_id) REFERENCES vocabulary_items (id) ON DELETE CASCADE
);
CREATE TABLE session_classification_snapshots (
	id INTEGER NOT NULL, 
	session_id INTEGER NOT NULL, 
	snapshotted_at DATETIME NOT NULL, 
	not_practiced_count INTEGER NOT NULL, 
	difficult_count INTEGER NOT NULL, 
	almost_learned_count INTEGER NOT NULL, 
	learned_count INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES practice_sessions (id) ON DELETE CASCADE
);
CREATE TABLE learning_tool_results (
	id INTEGER NOT NULL, 
	message_id INTEGER NOT NULL, 
	tool_type VARCHAR(20) NOT NULL, 
	input_selection VARCHAR(500), 
	result TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_tool_result UNIQUE (message_id, tool_type, input_selection), 
	FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE CASCADE
);
CREATE INDEX ix_learning_tool_results_message_id ON learning_tool_results (message_id);
