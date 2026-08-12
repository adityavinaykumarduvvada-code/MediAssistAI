import React from 'react'

/**
 * The signature element of the product: a stylized snippet of a real
 * blood report with highlighter marks and margin "translation" notes
 * fading in in sequence — visualizing exactly what the product does
 * before the user uploads anything.
 */
export default function AnnotatedReport() {
  const rows = [
    { label: 'Hemoglobin', value: '10.2 g/dL', flag: 'low', note: 'Lower than typical — can explain tiredness', delay: 0.1 },
    { label: 'WBC Count', value: '11,400 /µL', flag: 'high', note: 'Slightly elevated — often means the body is fighting something', delay: 0.35 },
    { label: 'Platelets', value: '260,000 /µL', flag: 'normal', note: 'Within the expected range', delay: 0.6 },
  ]

  return (
    <div className="relative">
      <div className="absolute -inset-4 sm:-inset-6 border border-ink/10 rounded-sheet -rotate-1" aria-hidden="true" />
      <div className="relative bg-paper-card border border-ink/15 rounded-sheet shadow-sheet px-6 py-6 sm:px-8 sm:py-8 rotate-[0.4deg]">
        <div className="flex items-center justify-between border-b border-ink/10 pb-4 mb-5">
          <div>
            <p className="font-mono text-[11px] tracking-widest text-muted uppercase">Complete Blood Count</p>
            <p className="font-display text-lg text-ink">Patient Report — Excerpt</p>
          </div>
          <span className="font-mono text-[11px] text-muted">Ref# 88213</span>
        </div>

        <div className="space-y-4">
          {rows.map((r, i) => (
            <div key={r.label} className="grid grid-cols-[1fr,auto] gap-x-4 items-start">
              <div>
                <div className="flex items-baseline gap-3">
                  <span className="font-body text-sm text-ink/70">{r.label}</span>
                  <span
                    className="mark-animate font-mono text-sm font-medium text-ink px-0.5"
                    style={{ '--mark-delay': `${r.delay + 0.4}s` }}
                  >
                    {r.value}
                  </span>
                  {r.flag !== 'normal' && (
                    <span
                      className={`text-[10px] font-mono uppercase tracking-wide px-1.5 py-0.5 rounded-sm ${
                        r.flag === 'low' ? 'bg-clinical-soft text-clinical' : 'bg-flag-soft text-flag'
                      }`}
                    >
                      {r.flag}
                    </span>
                  )}
                </div>
                <p
                  className="font-body text-[13px] text-muted mt-1 opacity-0 animate-fadeUp"
                  style={{ animationDelay: `${r.delay + 0.9}s`, animationFillMode: 'forwards' }}
                >
                  <span className="text-highlighter">›</span> {r.note}
                </p>
              </div>
              <div className="w-1 self-stretch bg-ink/5 rounded-full" aria-hidden="true" />
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-dashed border-ink/15 flex items-center gap-2 text-[11px] font-mono text-muted">
          <span className="w-1.5 h-1.5 rounded-full bg-clinical animate-pulseDot" />
          translated in plain language by MediAssist AI
        </div>
      </div>
    </div>
  )
}
