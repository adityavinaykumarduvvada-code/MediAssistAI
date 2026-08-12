import React from 'react'

export default function Header({ onReset, showReset }) {
  return (
    <header className="border-b border-ink/10 bg-paper/90 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-sheet bg-ink flex items-center justify-center">
            <span className="font-mono text-highlighter text-[13px] font-semibold">M</span>
          </div>
          <span className="font-display text-[17px] tracking-tight">MediAssist AI</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="hidden sm:inline font-mono text-[11px] text-muted tracking-wide">
            EDUCATIONAL TOOL · NOT A DIAGNOSIS
          </span>
          {showReset && (
            <button
              onClick={onReset}
              className="font-body text-sm text-ink border border-ink/20 rounded-sheet px-3.5 py-1.5 hover:bg-ink hover:text-paper transition-colors"
            >
              Start new case
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
