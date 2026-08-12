import React, { useCallback, useRef, useState } from 'react'

const ACCEPTED_HINT = 'PDF, PNG, or JPG — blood reports, X-rays, MRI/CT reports, prescriptions'

function fileIcon(name) {
  const ext = name.split('.').pop().toLowerCase()
  if (['png', 'jpg', 'jpeg', 'webp'].includes(ext)) return '🩻'
  return '📄'
}

export default function UploadPanel({ onAnalyze, isUploading, error }) {
  const [files, setFiles] = useState([])
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef(null)

  const addFiles = useCallback((incoming) => {
    const list = Array.from(incoming)
    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name + f.size))
      const merged = [...prev]
      for (const f of list) {
        if (!existingNames.has(f.name + f.size)) merged.push(f)
      }
      return merged.slice(0, 6)
    })
  }, [])

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    addFiles(e.dataTransfer.files)
  }

  const removeFile = (idx) => setFiles((prev) => prev.filter((_, i) => i !== idx))

  return (
    <section className="max-w-3xl mx-auto px-6 sm:px-8 py-16 sm:py-20">
      <p className="font-mono text-[12px] tracking-[0.2em] text-clinical uppercase mb-3">Step 1 of 2</p>
      <h2 className="font-display text-3xl sm:text-4xl text-ink mb-3">Upload your documents</h2>
      <p className="font-body text-ink/60 mb-10 max-w-xl">
        Drop in whatever you have — you don't need all four. The Planner Agent
        figures out what each file is automatically.
      </p>

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-sheet border-2 border-dashed px-8 py-14 text-center transition-colors ${
          isDragging ? 'border-clinical bg-clinical-soft' : 'border-ink/25 bg-paper-card hover:border-ink/40'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
        <div className="font-display text-2xl text-ink mb-2">Drop files here</div>
        <p className="font-body text-sm text-muted">{ACCEPTED_HINT}</p>
        <p className="font-mono text-[12px] text-clinical mt-3 underline">or click to browse</p>
      </div>

      {files.length > 0 && (
        <ul className="mt-6 space-y-2">
          {files.map((f, i) => (
            <li
              key={f.name + f.size}
              className="flex items-center justify-between bg-paper-card border border-ink/10 rounded-sheet px-4 py-3"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-lg">{fileIcon(f.name)}</span>
                <div className="min-w-0">
                  <p className="font-body text-sm text-ink truncate max-w-xs">{f.name}</p>
                  <p className="font-mono text-[11px] text-muted">{(f.size / 1024).toFixed(0)} KB</p>
                </div>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="font-mono text-[12px] text-flag hover:underline shrink-0 ml-3"
                aria-label={`Remove ${f.name}`}
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p className="mt-4 font-body text-sm text-flag bg-flag-soft border border-flag/30 rounded-sheet px-4 py-3">
          {error}
        </p>
      )}

      <button
        disabled={files.length === 0 || isUploading}
        onClick={() => onAnalyze(files)}
        className="mt-8 font-body font-medium text-[15px] bg-ink text-paper rounded-sheet px-6 py-3.5 hover:bg-ink-soft transition-colors shadow-sheet disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-ink"
      >
        {isUploading ? 'Uploading…' : `Analyze ${files.length || ''} document${files.length === 1 ? '' : 's'}`.trim()}
      </button>

      <p className="font-mono text-[11px] text-muted mt-4">
        Files are processed for this session only and used solely to generate your explanation.
      </p>
    </section>
  )
}
