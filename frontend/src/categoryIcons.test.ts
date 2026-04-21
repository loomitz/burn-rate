import { describe, expect, it } from 'vitest'

import { categoryIcons, getCategoryIcon, normalizeCategoryIconId } from './categoryIcons'

describe('category icon catalog', () => {
  it('keeps a curated searchable set with stable short ids', () => {
    const ids = categoryIcons.map((icon) => icon.id)

    expect(categoryIcons.length).toBeGreaterThanOrEqual(50)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toEqual(expect.arrayContaining(['tag', 'utensils', 'calendar', 'flame', 'wifi', 'paw', 'bolt', 'box']))
    expect(categoryIcons.every((icon) => icon.id.length <= 40)).toBe(true)
    expect(categoryIcons.every((icon) => icon.label && icon.group && icon.search)).toBe(true)
  })

  it('normalizes stored ids and falls back to tag', () => {
    expect(normalizeCategoryIconId('lucide:shopping-cart')).toBe('shopping-cart')
    expect(getCategoryIcon('paw').label).toBe('Mascotas')
    expect(getCategoryIcon('unknown-icon').id).toBe('tag')
    expect(getCategoryIcon(null).id).toBe('tag')
  })
})
