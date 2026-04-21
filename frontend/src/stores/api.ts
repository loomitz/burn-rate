export class ApiError extends Error {
  status: number
  details: unknown

  constructor(status: number, details: unknown) {
    super(`API error ${status}`)
    this.status = status
    this.details = details
  }
}

function csrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1]
}

function parseResponseBody(rawBody: string, contentType: string) {
  if (!rawBody) return null
  const normalizedContentType = contentType.toLowerCase()
  const looksJson =
    normalizedContentType.includes('application/json') || rawBody.startsWith('{') || rawBody.startsWith('[')

  if (!looksJson) return rawBody

  try {
    return JSON.parse(rawBody)
  } catch {
    return rawBody
  }
}

export function apiErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    const details = error.details
    if (typeof details === 'string' && details.trim()) return details
    if (details && typeof details === 'object') {
      const record = details as Record<string, unknown>
      const fields = ['detail', 'message', 'non_field_errors', 'error']
      for (const field of fields) {
        const value = record[field]
        if (typeof value === 'string' && value.trim()) return value
        if (Array.isArray(value)) {
          const first = value.find((item) => typeof item === 'string' && item.trim())
          if (typeof first === 'string') return first
        }
      }
      for (const value of Object.values(record)) {
        if (typeof value === 'string' && value.trim()) return value
        if (Array.isArray(value)) {
          const first = value.find((item) => typeof item === 'string' && item.trim())
          if (typeof first === 'string') return first
        }
      }
    }
    if (error.status === 401) return 'Email o password incorrecto.'
    if (error.status === 403) return 'No tienes permiso para hacer ese cambio.'
    if (error.status === 404) return 'No encontramos ese dato.'
    if (error.status === 429) return 'Hay demasiados intentos. Espera un momento e intenta otra vez.'
    return `Error ${error.status}`
  }

  if (error instanceof Error && error.message) {
    const networkHints = ['Failed to fetch', 'NetworkError', 'Load failed']
    if (networkHints.some((hint) => error.message.includes(hint))) {
      return 'No pudimos conectar con la casa. Revisa la red e intenta de nuevo.'
    }
    return error.message
  }

  return fallback
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  const token = csrfToken()
  if (token) {
    headers.set('X-CSRFToken', token)
  }

  const response = await fetch(path, {
    credentials: 'include',
    ...options,
    headers,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const rawBody = await response.text()
  const data = parseResponseBody(rawBody, response.headers.get('content-type') ?? '')
  if (!response.ok) {
    throw new ApiError(response.status, data)
  }
  return data as T
}

export function centsFromInput(value: string) {
  const normalized = Number(value.replace(',', '.'))
  if (!Number.isFinite(normalized)) return 0
  return Math.round(normalized * 100)
}

export function money(cents: number, currency = 'MXN') {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency,
  }).format(cents / 100)
}
