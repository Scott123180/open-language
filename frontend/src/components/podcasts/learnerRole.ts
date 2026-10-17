import type { ComponentType } from 'react'
import { IconHeadphones, IconMic, IconPhone } from '../shared/icons'

/** Each learner role's words and the icon that tells it apart at a glance. */
export const LEARNER_ROLES: Record<string, { text: string; Icon: ComponentType<{ size?: number }> }> = {
  guest: { text: "You're the guest", Icon: IconMic },
  co_host: { text: "You're a co-host", Icon: IconHeadphones },
  caller: { text: "You're a caller", Icon: IconPhone },
}

/** The learner's part in a show, as words; a role it does not know is shown as given. */
export function roleText(role: string): string {
  return LEARNER_ROLES[role]?.text ?? role
}
