const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export async function uploadFiles(files) {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))

  const res = await fetch(`${BASE_URL}/sessions/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload failed (${res.status})`)
  return res.json()
}

export async function analyzeSession(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/analyze`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error(`Analysis failed (${res.status})`)
  return res.json()
}

export async function fetchReport(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/report`)
  if (!res.ok) throw new Error(`No report found (${res.status})`)
  return res.json()
}
