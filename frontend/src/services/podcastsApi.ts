// ---------------------------------------------------------------------------
// Podcast API types (mirror specs/007-podcast-mode/contracts/api.md §1, §2, §6)
// ---------------------------------------------------------------------------

export type PodcastFormatId = 'one_host' | 'panel' | 'listen'
export type EpisodeLengthId = 'short' | 'medium' | 'long'
export type HostSlot = 'lead' | 'second'
export type LearnerRole = 'guest' | 'co_host' | 'caller'
export type ShowSource = 'ready_made' | 'generated' | 'surprise'
export type LineIntent = 'open' | 'greet' | 'discuss' | 'wrap_up' | 'sign_off'

/** Whose turn it is: the hosts', the learner's, or nobody's once the episode has finished. */
export type Turn = 'hosts' | 'learner' | 'finished'
/** At the hosts' turn: the opening, a reply to the learner, or the next line on Continue. */
export type Awaiting = 'opening' | 'reply' | 'continue' | null

export interface PodcastFormatOption {
  format_id: PodcastFormatId
  label: string
  host_count: number
  is_learner_speaking: boolean
  description: string
}

export interface EpisodeLengthOption {
  length_id: EpisodeLengthId
  label: string
  target_host_lines: number
  is_default: boolean
}

export interface PersonalityOption {
  personality_id: string
  label: string
  description: string
}

export interface HostDraft {
  slot: HostSlot
  name: string
  personality_id: string
  voice_key: string
  show_role: string
  angle: string | null
}

export interface ShowDraft {
  source: ShowSource
  show_id: string | null
  title: string
  premise: string
  topic: string
  learner_role: LearnerRole
  language: string
  hosts: HostDraft[]
}

export interface CatalogVoices {
  installed_count: number
  shared_voice_notice: string | null
  unavailable_message: string | null
}

export interface PodcastCatalog {
  language: string
  language_name: string
  formats: PodcastFormatOption[]
  lengths: EpisodeLengthOption[]
  personalities: PersonalityOption[]
  shows: ShowDraft[]
  voices: CatalogVoices
}

export interface PodcastPreferences {
  last_format: PodcastFormatId
  is_show_text_on: boolean
  interests: string[]
  learner_name: string | null
}

export interface EpisodeHost {
  host_id: number
  slot: HostSlot
  name: string
  personality_id: string
  personality_label: string
  voice_key: string
  show_role: string
  is_voice_available: boolean
  voice_unavailable_message: string | null
}

export interface EpisodeLine {
  message_id: number
  speaker: 'host' | 'learner'
  host_id: number | null
  content: string
  intent: LineIntent | null
  invites_learner: boolean
  is_revealed: boolean
  created_at: string
}

export interface EpisodeShow {
  title: string
  premise: string
  topic: string
  learner_role: LearnerRole
  source: ShowSource
  show_id: string | null
}

export interface Episode {
  conversation_id: number
  status: 'active' | 'completed'
  language: string
  language_name: string
  native_language_name: string
  show: EpisodeShow
  format: PodcastFormatId
  format_label: string
  length: EpisodeLengthId
  target_host_lines: number
  learner_name: string | null
  hosts: EpisodeHost[]
  shared_voice_notice: string | null
  turn: Turn
  awaiting: Awaiting
  can_jump_in: boolean
  can_pass: boolean
  lines: EpisodeLine[]
}

/** One row of `GET /api/podcasts/episodes`, for labelling Past Chats. */
export interface EpisodeSummaryRow {
  conversation_id: number
  show_title: string
  format: PodcastFormatId
  format_label: string
  host_names: string[]
  language: string
  language_name: string
  status: 'active' | 'completed'
}
