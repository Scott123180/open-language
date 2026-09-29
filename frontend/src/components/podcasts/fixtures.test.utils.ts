import type { EpisodeHost, EpisodeLine, PersonalityOption, ShowDraft } from '../../services/podcastsApi'

export const personalities: PersonalityOption[] = [
  { personality_id: 'enthusiast', label: 'Enthusiast', description: 'Excited about everything.' },
  { personality_id: 'dry_sceptic', label: 'Dry sceptic', description: 'Unimpressed until convinced.' },
]

export const show: ShowDraft = {
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
}

export const lucia: EpisodeHost = {
  host_id: 11,
  slot: 'lead',
  name: 'Lucía',
  personality_id: 'enthusiast',
  personality_label: 'Enthusiast',
  voice_key: 'es_AR-daniela-high',
  show_role: 'host',
  is_voice_available: true,
  voice_unavailable_message: null,
}

export const hostLine: EpisodeLine = {
  message_id: 901,
  speaker: 'host',
  host_id: 11,
  content: '¡Bienvenidos a Weekend Food Talk!',
  intent: 'open',
  invites_learner: true,
  is_revealed: false,
  created_at: '2026-09-28T10:00:00Z',
}

export const generatedShow: ShowDraft = {
  ...show,
  source: 'generated',
  show_id: null,
  title: 'Night Shift Abroad',
  premise: 'Two nurses swap stories about working far from home.',
  topic: 'living abroad as a nurse',
}
