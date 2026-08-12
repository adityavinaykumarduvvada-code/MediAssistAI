import React from 'react'

export default function Section({ eyebrow, title, children, className = '' }) {
  return (
    <section className={`py-10 border-b border-ink/10 ${className}`}>
      {eyebrow && (
        <p className="font-mono text-[11px] tracking-[0.2em] text-clinical uppercase mb-2">{eyebrow}</p>
      )}
      {title && <h2 className="font-display text-2xl text-ink mb-5">{title}</h2>}
      {children}
    </section>
  )
}
