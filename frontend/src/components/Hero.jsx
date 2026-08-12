import React from 'react'
import AnnotatedReport from './AnnotatedReport.jsx'

export default function Hero({ onStart }) {
  return (
    <section className="max-w-6xl mx-auto px-6 sm:px-8 pt-16 sm:pt-24 pb-20 grid lg:grid-cols-2 gap-16 items-center">
      <div>
        <p className="font-mono text-[12px] tracking-[0.2em] text-clinical uppercase mb-5">
          Blood reports · X-rays · MRI/CT · Prescriptions
        </p>
        <h1 className="font-display text-[2.75rem] sm:text-[3.4rem] leading-[1.05] text-ink mb-6">
          Your medical reports,<br />
          <span className="italic">explained like a friend</span><br />
          who happens to be a doctor.
        </h1>
        <p className="font-body text-lg text-ink/70 max-w-lg mb-9 leading-relaxed">
          Upload what you were handed at the clinic. Domain-specific agents read
          it, merge it into one patient snapshot, cross-check it against a
          medical knowledge graph of trusted references, and a safety layer
          verifies the language before it ever reaches you.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <button
            onClick={onStart}
            className="font-body font-medium text-[15px] bg-ink text-paper rounded-sheet px-6 py-3.5 hover:bg-ink-soft transition-colors shadow-sheet"
          >
            Analyze my reports
          </button>
          <span className="font-mono text-[12px] text-muted">4 files max · PDF, PNG, JPG</span>
        </div>

        <dl className="grid grid-cols-3 gap-6 mt-14 max-w-md border-t border-ink/10 pt-6">
          {[
            ['8', 'agentic reasoning steps'],
            ['<60s', 'to a plain summary'],
            ['1', 'built-in safety layer'],
          ].map(([n, l]) => (
            <div key={l}>
              <dt className="font-display text-2xl text-ink">{n}</dt>
              <dd className="font-body text-[12px] text-muted mt-1">{l}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="hidden lg:block">
        <AnnotatedReport />
      </div>
    </section>
  )
}
