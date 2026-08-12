import React, { useEffect, useState } from 'react'

const AGENTS = [
  { key: 'Agentic Orchestrator', label: 'Agentic Orchestrator', desc: 'Sorting your files by type' },
  { key: 'Blood Agent', label: 'Blood Agent', desc: 'Reading blood & lab reports' },
  { key: 'Drug Agent', label: 'Drug Agent', desc: 'Reading prescriptions' },
  { key: 'Imaging Agent', label: 'Imaging Agent', desc: 'Reading X-ray / MRI / CT images' },
  { key: 'Patient Digital Twin', label: 'Patient Digital Twin', desc: 'Merging everything into one patient snapshot' },
  { key: 'Medical Knowledge Graph', label: 'Medical Knowledge Graph', desc: 'Linking findings to trusted references' },
  { key: 'Clinical Reasoning Agent', label: 'Clinical Reasoning Agent', desc: 'Reasoning through possible explanations' },
  { key: 'Safety / Verification Agent', label: 'Safety / Verification Agent', desc: 'Double-checking language & citations' },
]

export default function PipelineTracker({ trace }) {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 900)
    return () => clearInterval(id)
  }, [])

  const statusFor = (key) => {
    const events = (trace || []).filter((t) => t.agent === key)
    if (events.some((e) => e.status === 'completed')) return 'completed'
    if (events.some((e) => e.status === 'started')) return 'running'
    return 'pending'
  }

  // While we're waiting for the backend response, simulate forward motion
  // through the pipeline so the wait doesn't feel static.
  const simulatedActive = Math.min(AGENTS.length - 1, Math.floor(tick / 2))

  return (
    <section className="max-w-2xl mx-auto px-6 sm:px-8 py-24 text-center">
      <p className="font-mono text-[12px] tracking-[0.2em] text-clinical uppercase mb-3">Step 2 of 2</p>
      <h2 className="font-display text-3xl text-ink mb-2">Reading your case</h2>
      <p className="font-body text-ink/60 mb-14">Four agents are working through your documents in order.</p>

      <ol className="space-y-5 text-left max-w-md mx-auto">
        {AGENTS.map((agent, i) => {
          const status = trace?.length ? statusFor(agent.key) : (i <= simulatedActive ? (i < simulatedActive ? 'completed' : 'running') : 'pending')
          return (
            <li key={agent.key} className="flex items-start gap-4">
              <div className="mt-1 shrink-0">
                {status === 'completed' && (
                  <div className="w-6 h-6 rounded-full bg-clinical flex items-center justify-center">
                    <span className="text-paper text-xs">✓</span>
                  </div>
                )}
                {status === 'running' && (
                  <div className="w-6 h-6 rounded-full border-2 border-highlighter flex items-center justify-center">
                    <span className="w-2 h-2 rounded-full bg-highlighter animate-pulseDot" />
                  </div>
                )}
                {status === 'pending' && (
                  <div className="w-6 h-6 rounded-full border-2 border-ink/15" />
                )}
              </div>
              <div>
                <p className={`font-body text-sm font-medium ${status === 'pending' ? 'text-ink/35' : 'text-ink'}`}>
                  {agent.label}
                </p>
                <p className={`font-body text-[13px] ${status === 'pending' ? 'text-ink/25' : 'text-muted'}`}>
                  {agent.desc}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
