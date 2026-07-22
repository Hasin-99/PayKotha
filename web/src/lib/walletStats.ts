import type { Txn, User } from '../api'

export function isOutflow(t: Txn, userId: string) {
  if (['CASH_IN', 'BANK_IN', 'SAVINGS_OUT'].includes(t.txn_type)) return false
  if (t.txn_type === 'REQUEST_PAY' && t.receiver_id === userId) return false
  return t.sender_id === userId
}

export function labelTxn(type: string) {
  return type.replaceAll('_', ' ')
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return 'PK'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function kycRank(level?: string) {
  if (level === 'L2_FULL') return 2
  if (level === 'L1_NID') return 1
  return 0
}

export function kycLabel(level?: string) {
  if (level === 'L2_FULL') return 'Full verified'
  if (level === 'L1_NID') return 'NID verified'
  return 'Basic'
}

export function todayKey(d = new Date()) {
  return d.toISOString().slice(0, 10)
}

export function spentToday(txns: Txn[], userId: string) {
  const key = todayKey()
  return txns.reduce((sum, t) => {
    if (!isOutflow(t, userId)) return sum
    if (!t.created_at?.startsWith(key)) return sum
    return sum + Number(t.amount || 0) + Number(t.fee || 0)
  }, 0)
}

export function monthStats(txns: Txn[], userId: string) {
  const prefix = todayKey().slice(0, 7)
  let inflow = 0
  let outflow = 0
  let fees = 0
  let count = 0
  for (const t of txns) {
    if (!t.created_at?.startsWith(prefix)) continue
    count += 1
    fees += Number(t.fee || 0)
    if (isOutflow(t, userId)) outflow += Number(t.amount || 0)
    else inflow += Number(t.amount || 0)
  }
  return { inflow, outflow, fees, count }
}

export function limitPct(spent: number, limit: number) {
  if (!limit) return 0
  return Math.min(100, Math.round((spent / limit) * 100))
}

export function relativeTime(iso: string) {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const sec = Math.round((Date.now() - t) / 1000)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  if (sec < 604800) return `${Math.floor(sec / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

export function memberSince(user: User) {
  try {
    return new Date(user.created_at).toLocaleDateString('en-GB', {
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}
