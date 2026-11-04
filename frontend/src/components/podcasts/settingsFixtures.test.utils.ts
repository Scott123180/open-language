import type { EpisodeOptions } from '../../services/podcastsApi'

/** 011 contracts §1's episode_options, as the catalogue serves them. */
export const episodeOptions: EpisodeOptions = {
  styles: [
    { style_id: 'conversation', label: 'Conversation', description: 'Lots of back-and-forth.', is_default: false },
    { style_id: 'balanced', label: 'Balanced', description: 'Some talk, some explaining.', is_default: true },
    { style_id: 'presented', label: 'Presented', description: 'The hosts mostly explain and tell stories, like a radio show.', is_default: false },
  ],
  line_lengths: [
    { line_length_id: 'short', label: 'Short', is_default: false },
    { line_length_id: 'medium', label: 'Medium', is_default: true },
    { line_length_id: 'long', label: 'Long', is_default: false },
  ],
  invite_frequencies: [
    { invite_frequency_id: 'often', label: 'Often', is_default: false },
    { invite_frequency_id: 'sometimes', label: 'Sometimes', is_default: true },
    { invite_frequency_id: 'rarely', label: 'Rarely', is_default: false },
  ],
  learner_roles: [
    { learner_role: 'guest', label: 'Guest' },
    { learner_role: 'co_host', label: 'Co-host' },
    { learner_role: 'caller', label: 'Caller' },
  ],
  today_subject_max_length: 120,
}
