import { apiFetch } from './client'

export type AvatarId = 'fox' | 'owl' | 'otter' | 'comet' | 'cactus' | 'wave'
export type ColourTheme = 'indigo' | 'coral' | 'teal' | 'amber' | 'violet'

export interface Profile {
  userId: string
  nickname: string
  avatar: AvatarId
  colourTheme: ColourTheme
}

interface ProfileResponse extends Partial<Profile> {
  userId: string
  isNew: boolean
}

export async function getProfile(idToken: string): Promise<ProfileResponse> {
  return apiFetch<ProfileResponse>('/profile', idToken)
}

export async function putProfile(
  idToken: string,
  update: { nickname: string; avatar: AvatarId; colourTheme: ColourTheme },
): Promise<Profile> {
  return apiFetch<Profile>('/profile', idToken, {
    method: 'PUT',
    body: JSON.stringify({ nickname: update.nickname, avatar: update.avatar, colourTheme: update.colourTheme }),
  })
}
