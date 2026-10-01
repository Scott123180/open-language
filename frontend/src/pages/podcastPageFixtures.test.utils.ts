import type { Episode, EpisodeLine, PodcastCatalog, PodcastPreferences } from '../services/podcastsApi'

export const catalog: PodcastCatalog = {
  language: 'es',
  language_name: 'Spanish',
  formats: [
    { format_id: 'one_host', label: 'One host', host_count: 1, is_learner_speaking: true, description: 'You and one host.' },
    { format_id: 'panel', label: 'Panel', host_count: 2, is_learner_speaking: true, description: 'You and two hosts.' },
    { format_id: 'listen', label: 'Listen', host_count: 2, is_learner_speaking: false, description: 'Two hosts talk; you listen.' },
  ],
  lengths: [
    { length_id: 'short', label: 'Short', target_host_lines: 10, is_default: false },
    { length_id: 'medium', label: 'Medium', target_host_lines: 20, is_default: true },
    { length_id: 'long', label: 'Long', target_host_lines: 40, is_default: false },
  ],
  personalities: [
    { personality_id: 'enthusiast', label: 'Enthusiast', description: 'Excited.' },
    { personality_id: 'dry_sceptic', label: 'Dry sceptic', description: 'Unimpressed.' },
  ],
  shows: [
    {
      source: 'ready_made',
      show_id: 'weekend-food-talk',
      title: 'Weekend Food Talk',
      premise: 'Two food lovers swap weekend cooking wins and disasters.',
      topic: 'food',
      learner_role: 'guest',
      language: 'es',
      hosts: [
        { slot: 'lead', name: 'Lucía', personality_id: 'enthusiast', voice_key: 'es_AR-daniela-high', show_role: 'host', angle: null },
        { slot: 'second', name: 'Marco', personality_id: 'dry_sceptic', voice_key: 'es_ES-davefx-medium', show_role: 'co_host', angle: null },
      ],
    },
  ],
  voices: { installed_count: 2, shared_voice_notice: null, unavailable_message: null },
}

export const preferences: PodcastPreferences = {
  last_format: 'panel',
  is_show_text_on: false,
  interests: [],
  learner_name: 'Sam',
}

export const openingLine: EpisodeLine = {
  message_id: 901,
  speaker: 'host',
  host_id: 11,
  content: '¡Bienvenidos! ¿Qué cocinaste?',
  intent: 'open',
  invites_learner: true,
  is_revealed: false,
  created_at: '2026-09-28T10:00:00Z',
}

export const episode = (overrides: Partial<Episode> = {}): Episode => ({
  conversation_id: 57,
  status: 'active',
  language: 'de',
  language_name: 'German',
  native_language_name: 'English',
  show: { title: 'Weekend Food Talk', premise: 'p', topic: 'food', learner_role: 'guest', source: 'ready_made', show_id: 'weekend-food-talk' },
  format: 'one_host',
  format_label: 'One host',
  length: 'short',
  target_host_lines: 10,
  learner_name: null,
  hosts: [
    { host_id: 11, slot: 'lead', name: 'Lucía', personality_id: 'enthusiast', personality_label: 'Enthusiast', voice_key: 'de_DE-kerstin-low', show_role: 'host', is_voice_available: true, voice_unavailable_message: null },
  ],
  shared_voice_notice: null,
  turn: 'learner',
  awaiting: null,
  can_jump_in: false,
  can_pass: false,
  lines: [openingLine],
  ...overrides,
})
