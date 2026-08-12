import React from 'react'
import Section from '../components/Section.jsx'
import LabValueTable from '../components/LabValueTable.jsx'

export default function Results({ report }) {
  const { summary, pdf_results = [], image_results = [] } = report

  return (
    <div className="max-w-3xl mx-auto px-6 sm:px-8 py-14">
      <p className="font-mono text-[12px] tracking-[0.2em] text-clinical uppercase mb-3">Your case, explained</p>
      <h1 className="font-display text-4xl text-ink mb-6 leading-tight">Here's what your documents show</h1>

      <div className="bg-paper-card border border-ink/10 rounded-sheet p-6 mb-2 shadow-sheet">
        <p className="font-body text-[17px] leading-relaxed text-ink">
          {summary.plain_language_summary}
        </p>
      </div>

      <Section eyebrow="Possibilities to discuss" title="Possible conditions">
        {summary.possible_conditions.length === 0 ? (
          <p className="font-body text-sm text-muted">No specific condition pattern was flagged from what was provided.</p>
        ) : (
          <ul className="space-y-3">
            {summary.possible_conditions.map((c, i) => (
              <li key={i} className="flex gap-3 items-start">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-highlighter shrink-0" />
                <span className="font-body text-[15px] text-ink">{c}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {summary.evidence.length > 0 && (
        <Section eyebrow="Why we think so" title="Supporting evidence">
          <ul className="space-y-3">
            {summary.evidence.map((e, i) => (
              <li key={i} className="font-body text-[15px] text-ink/80 pl-4 border-l-2 border-clinical-soft">
                {e}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {(pdf_results.some((r) => r.lab_values.length > 0)) && (
        <Section eyebrow="Extracted data" title="Lab values">
          <LabValueTable results={pdf_results} />
        </Section>
      )}

      {image_results.length > 0 && (
        <Section eyebrow="Scan analysis" title="Imaging observations">
          <div className="space-y-6">
            {image_results.map((img, i) => (
              <div key={i} className="bg-paper-card border border-ink/10 rounded-sheet p-5">
                <p className="font-mono text-[11px] uppercase tracking-wide text-clinical mb-3">{img.modality}</p>
                {img.observations.length > 0 && (
                  <>
                    <p className="font-body text-[13px] text-muted mb-1">Observations</p>
                    <ul className="mb-3 space-y-1">
                      {img.observations.map((o, j) => (
                        <li key={j} className="font-body text-sm text-ink">• {o}</li>
                      ))}
                    </ul>
                  </>
                )}
                {img.possible_findings.length > 0 && (
                  <>
                    <p className="font-body text-[13px] text-muted mb-1">Possible findings</p>
                    <ul className="mb-3 space-y-1">
                      {img.possible_findings.map((f, j) => (
                        <li key={j} className="font-body text-sm text-ink">
                          <span className="mark px-0.5">{f}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="font-body text-[12px] text-muted italic">{img.confidence_note}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {summary.medicine_explanations.length > 0 && (
        <Section eyebrow="What you were prescribed" title="Medicine explanations">
          <ul className="space-y-3">
            {summary.medicine_explanations.map((m, i) => (
              <li key={i} className="font-body text-[15px] text-ink bg-paper-card border border-ink/10 rounded-sheet p-4">
                {m}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section eyebrow="Take this with you" title="Questions to ask your doctor">
        <ol className="space-y-3">
          {summary.follow_up_questions.map((q, i) => (
            <li key={i} className="flex gap-3 items-start">
              <span className="font-mono text-xs text-clinical mt-1 shrink-0 w-5">{String(i + 1).padStart(2, '0')}</span>
              <span className="font-body text-[15px] text-ink">{q}</span>
            </li>
          ))}
        </ol>
      </Section>

      {summary.references.length > 0 && (
        <Section eyebrow="Grounded in" title="References" className="border-b-0">
          <div className="flex flex-wrap gap-2">
            {summary.references.map((r, i) => (
              <span key={i} className="font-mono text-[12px] text-clinical bg-clinical-soft px-3 py-1.5 rounded-sheet">
                {r}
              </span>
            ))}
          </div>
        </Section>
      )}

      <div className="mt-4 bg-flag-soft border border-flag/25 rounded-sheet px-5 py-4">
        <p className="font-body text-[13px] text-flag leading-relaxed">
          {summary.disclaimer}
        </p>
      </div>

      {summary.safety_notes && summary.safety_notes.length > 0 && (
        <div className="mt-4 bg-clinical-soft border border-clinical/20 rounded-sheet px-5 py-4">
          <p className="font-mono text-[11px] uppercase tracking-wide text-clinical mb-2">
            Safety / Verification Agent — what it checked
          </p>
          <ul className="space-y-1">
            {summary.safety_notes.map((n, i) => (
              <li key={i} className="font-body text-[13px] text-ink/70">• {n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
