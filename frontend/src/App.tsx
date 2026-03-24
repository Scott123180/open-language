import { Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Chat from './pages/Chat'
import History from './pages/History'
import Settings from './pages/Settings'
import Flashcards from './pages/Flashcards'
import FlashcardDecks from './pages/FlashcardDecks'
import FlashcardPractice from './pages/FlashcardPractice'
import FlashcardSummary from './pages/FlashcardSummary'
import FlashcardAnalytics from './pages/FlashcardAnalytics'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/chat/:conversationId" element={<Chat />} />
      <Route path="/history" element={<History />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/flashcards" element={<Flashcards />} />
      <Route path="/flashcards/decks" element={<FlashcardDecks />} />
      <Route path="/flashcards/practice/:sessionId" element={<FlashcardPractice />} />
      <Route path="/flashcards/summary/:sessionId" element={<FlashcardSummary />} />
      <Route path="/flashcards/analytics" element={<FlashcardAnalytics />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
