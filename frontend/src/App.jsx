import React, { useState } from 'react'
import Header from './components/Header.jsx'
import Hero from './components/Hero.jsx'
import UploadPanel from './components/UploadPanel.jsx'
import PipelineTracker from './components/PipelineTracker.jsx'
import Results from './pages/Results.jsx'
import { uploadFiles, analyzeSession } from './api/client.js'

// 'landing' -> 'upload' -> 'analyzing' -> 'results' -> 'error'
export default function App() {
  const [stage, setStage] = useState('landing')
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)

  const handleAnalyze = async (files) => {
    setError(null)
    setIsUploading(true)
    try {
      const { session_id } = await uploadFiles(files)
      setIsUploading(false)
      setStage('analyzing')
      const result = await analyzeSession(session_id)
      setReport(result)
      setStage('results')
    } catch (err) {
      setIsUploading(false)
      setError(err.message || 'Something went wrong. Please try again.')
      setStage('upload')
    }
  }

  const reset = () => {
    setStage('landing')
    setReport(null)
    setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header onReset={reset} showReset={stage !== 'landing'} />
      <main className="flex-1">
        {stage === 'landing' && <Hero onStart={() => setStage('upload')} />}
        {stage === 'upload' && (
          <UploadPanel onAnalyze={handleAnalyze} isUploading={isUploading} error={error} />
        )}
        {stage === 'analyzing' && <PipelineTracker trace={[]} />}
        {stage === 'results' && report && <Results report={report} />}
      </main>
      <footer className="border-t border-ink/10 py-8">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 flex flex-col sm:flex-row justify-between items-center gap-3">
          <p className="font-mono text-[11px] text-muted">MediAssist AI — educational tool, not a medical device.</p>
          <p className="font-mono text-[11px] text-muted">Planner · PDF · Image · Summary agents</p>
        </div>
      </footer>
    </div>
  )
}
