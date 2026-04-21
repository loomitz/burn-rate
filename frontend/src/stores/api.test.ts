import { describe, expect, it } from 'vitest'
import { ApiError, apiErrorMessage, centsFromInput, money } from './api'

describe('money helpers', () => {
  it('converts decimal user input to cents', () => {
    expect(centsFromInput('123.45')).toBe(12345)
    expect(centsFromInput('99,90')).toBe(9990)
  })

  it('formats cents in MXN', () => {
    expect(money(12345)).toContain('$123.45')
  })

  it('extracts a useful message from api errors', () => {
    expect(apiErrorMessage(new ApiError(400, { detail: 'Monto invalido' }), 'Fallback')).toBe('Monto invalido')
    expect(apiErrorMessage(new Error('Failed to fetch'), 'Fallback')).toContain('No pudimos conectar')
  })
})
