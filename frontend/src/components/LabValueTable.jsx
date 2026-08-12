import React from 'react'

const FLAG_STYLES = {
  low: 'bg-clinical-soft text-clinical',
  high: 'bg-flag-soft text-flag',
  normal: 'bg-ink/5 text-ink/50',
  unknown: 'bg-ink/5 text-ink/40',
}

export default function LabValueTable({ results }) {
  const allValues = results.flatMap((r) =>
    r.lab_values.map((lv) => ({ ...lv, docType: r.document_type }))
  )

  if (allValues.length === 0) return null

  return (
    <div className="overflow-x-auto scrollbar-thin border border-ink/10 rounded-sheet">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-ink/10 bg-paper-card">
            <th className="font-mono text-[11px] uppercase tracking-wide text-muted px-4 py-3">Test</th>
            <th className="font-mono text-[11px] uppercase tracking-wide text-muted px-4 py-3">Value</th>
            <th className="font-mono text-[11px] uppercase tracking-wide text-muted px-4 py-3">Reference range</th>
            <th className="font-mono text-[11px] uppercase tracking-wide text-muted px-4 py-3">Flag</th>
          </tr>
        </thead>
        <tbody>
          {allValues.map((lv, i) => (
            <tr key={`${lv.name}-${i}`} className="border-b border-ink/5 last:border-0">
              <td className="font-body text-sm text-ink px-4 py-3">{lv.name}</td>
              <td className="font-mono text-sm text-ink px-4 py-3">
                {lv.value} {lv.unit || ''}
              </td>
              <td className="font-mono text-[13px] text-muted px-4 py-3">{lv.reference_range || '—'}</td>
              <td className="px-4 py-3">
                <span className={`text-[10px] font-mono uppercase tracking-wide px-2 py-1 rounded-sm ${FLAG_STYLES[lv.flag] || FLAG_STYLES.unknown}`}>
                  {lv.flag}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
