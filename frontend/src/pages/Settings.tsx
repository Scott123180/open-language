import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { IconArrowLeft } from '../components/shared/icons'
import ConversationLevelSection from '../components/settings/ConversationLevelSection'
import CorrectionModeFieldset from '../components/settings/CorrectionModeFieldset'
import LlmProviderFields from '../components/settings/LlmProviderFields'
import PracticeLanguageFieldset from '../components/settings/PracticeLanguageFieldset'
import SettingsSaveBar from '../components/settings/SettingsSaveBar'
import SuggestionCountField from '../components/settings/SuggestionCountField'
import ThemeField from '../components/settings/ThemeField'
import TtsVoiceField from '../components/settings/TtsVoiceField'
import WhisperModelField from '../components/settings/WhisperModelField'
import { useLlmProviders } from '../components/settings/useLlmProviders'
import { useSettingsForm } from '../components/settings/useSettingsForm'

const pageStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '40px 16px',
  gap: '24px',
  minHeight: '100vh',
  background: 'var(--color-bg)',
}
const formStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '20px',
  width: '100%',
  maxWidth: '480px',
}

/** Layout only: the form's state lives in useSettingsForm, each section in its own component. */
export default function Settings() {
  const form = useSettingsForm()
  const llmProviders = useLlmProviders()
  return (
    <main style={pageStyle}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Settings</h1>
      <Link to="/" className="back-link" style={{ alignSelf: 'flex-start' }}>
        <IconArrowLeft size={14} /> Back to Home
      </Link>
      {form.isLoading && <p aria-live="polite">Loading settings…</p>}
      {!form.isLoading && (
        <form onSubmit={(e) => e.preventDefault()} style={formStyle}>
          <LlmProviderFields providers={llmProviders} value={form.llm} onChange={form.setLlm} />
          <WhisperModelField value={form.whisperModel} onChange={form.setWhisperModel} />
          {form.practiceLanguages.length > 0 && (
            <PracticeLanguageFieldset
              languages={form.practiceLanguages}
              value={form.practiceLanguage}
              onChange={form.setPracticeLanguage}
            />
          )}
          <TtsVoiceField
            value={form.ttsVoice}
            voices={form.voicesForLanguage}
            onChange={form.setTtsVoice}
          />
          <ConversationLevelSection
            value={form.conversationLevel}
            onChange={form.setConversationLevel}
          />
          <CorrectionModeFieldset value={form.correctionMode} onChange={form.setCorrectionMode} />
          <ThemeField />
          <SuggestionCountField value={form.suggestionCount} onChange={form.setSuggestionCount} />
          <SettingsSaveBar
            isSaving={form.isSaving}
            successMessage={form.successMessage}
            errorMessage={form.errorMessage}
            onSave={form.save}
          />
        </form>
      )}
    </main>
  )
}
