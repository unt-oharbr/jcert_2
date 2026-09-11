import type { AvatarId, ColourTheme } from '../api/profile'

export const AVATAR_GLYPH: Record<AvatarId, string> = {
  fox: '🦊',
  owl: '🦉',
  otter: '🦦',
  comet: '☄️',
  cactus: '🌵',
  wave: '🌊',
}

export const COLOUR_SWATCH: Record<ColourTheme, string> = {
  indigo: '#3454d1',
  coral: '#e8735a',
  teal: '#1f9e9e',
  amber: '#d98e2b',
  violet: '#7c4fd9',
}
