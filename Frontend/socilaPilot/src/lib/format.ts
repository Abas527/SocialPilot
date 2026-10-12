const WEI_PER_ETH = 10n ** 18n

export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 45) return 'just now'
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto', style: 'narrow' })
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(seconds / 3600), 'hour')
  if (abs < 86400 * 7) return rtf.format(Math.round(seconds / 86400), 'day')
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: abs > 86400 * 300 ? 'numeric' : undefined })
}

export function fullDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

/** Wei (decimal string or bigint) to a short ETH string, e.g. "0.0125". */
export function formatEth(wei: string | bigint, maxFraction = 5): string {
  const value = typeof wei === 'bigint' ? wei : BigInt(wei || '0')
  const whole = value / WEI_PER_ETH
  const fraction = (value % WEI_PER_ETH).toString().padStart(18, '0').slice(0, maxFraction).replace(/0+$/, '')
  return fraction ? `${whole}.${fraction}` : `${whole}`
}

export function shortAddress(address: string): string {
  return `${address.slice(0, 6)}…${address.slice(-4)}`
}

export function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || '?'
}

export function compactNumber(n: number): string {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n)
}

/** Local time in an IANA zone or "UTC+5:45" style label; null if the zone is unknown. */
export function localTimeIn(zone: string, now = new Date()): string | null {
  if (!zone) return null
  const match = /^UTC([+-])(\d{1,2})(?::(\d{2}))?$/.exec(zone)
  try {
    if (match) {
      const sign = match[1] === '-' ? -1 : 1
      const minutes = sign * (Number(match[2]) * 60 + Number(match[3] ?? 0))
      const shifted = new Date(now.getTime() + minutes * 60_000)
      return shifted.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })
    }
    return now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', timeZone: zone })
  } catch {
    return null
  }
}

export function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function errorMessage(cause: unknown, fallback = 'Something went wrong. Please try again.'): string {
  return cause instanceof Error && cause.message ? cause.message : fallback
}
