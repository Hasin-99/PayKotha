import { useMemo, useState } from 'react'
import type { Txn } from '../api'
import { isOutflow, labelTxn, monthStats, relativeTime } from '../lib/walletStats'

const money = (n: number) =>
  `৳${Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

type Filter = 'ALL' | 'IN' | 'OUT' | 'SEND' | 'BILL' | 'BANK' | 'SAVINGS'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'ALL', label: 'All' },
  { id: 'IN', label: 'In' },
  { id: 'OUT', label: 'Out' },
  { id: 'SEND', label: 'Send' },
  { id: 'BILL', label: 'Bills' },
  { id: 'BANK', label: 'Bank' },
  { id: 'SAVINGS', label: 'Savings' },
]

type Props = {
  userId: string
  txns: Txn[]
  onExport: () => void
}

export function HistoryPage({ userId, txns, onExport }: Props) {
  const [filter, setFilter] = useState<Filter>('ALL')
  const [q, setQ] = useState('')
  const [openId, setOpenId] = useState<string | null>(null)

  const month = useMemo(() => monthStats(txns, userId), [txns, userId])

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return txns.filter((t) => {
      const out = isOutflow(t, userId)
      if (filter === 'IN' && out) return false
      if (filter === 'OUT' && !out) return false
      if (filter === 'SEND' && t.txn_type !== 'TRANSFER') return false
      if (filter === 'BILL' && !['BILL_PAY', 'RECHARGE', 'MERCHANT'].includes(t.txn_type)) return false
      if (filter === 'BANK' && !['BANK_IN', 'BANK_OUT'].includes(t.txn_type)) return false
      if (filter === 'SAVINGS' && !['SAVINGS_IN', 'SAVINGS_OUT'].includes(t.txn_type)) return false
      if (!needle) return true
      return (
        t.id.toLowerCase().includes(needle) ||
        t.txn_type.toLowerCase().includes(needle) ||
        (t.note || '').toLowerCase().includes(needle) ||
        (t.rail_ref || '').toLowerCase().includes(needle)
      )
    })
  }, [txns, userId, filter, q])

  return (
    <section className="block hist-page" style={{ paddingTop: '0.85rem' }}>
      <div className="page-head">
        <div>
          <h3 style={{ margin: 0 }}>Statement</h3>
          <p className="muted tiny" style={{ margin: '0.2rem 0 0' }}>{month.count} this month</p>
        </div>
        <button type="button" className="chip" onClick={onExport}>Excel</button>
      </div>

      <div className="insight-grid tight">
        <div className="insight"><em>In</em><strong className="in">{money(month.inflow)}</strong></div>
        <div className="insight"><em>Out</em><strong className="out">{money(month.outflow)}</strong></div>
        <div className="insight"><em>Fees</em><strong>{money(month.fees)}</strong></div>
      </div>

      <label className="lbl">
        Search
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="TrxID, note, type…" />
      </label>

      <div className="chips">
        {FILTERS.map((f) => (
          <button key={f.id} type="button" className={`chip ${filter === f.id ? 'on' : ''}`} onClick={() => setFilter(f.id)}>
            {f.label}
          </button>
        ))}
      </div>

      <div className="list">
        {rows.map((t) => {
          const out = isOutflow(t, userId)
          const open = openId === t.id
          return (
            <div className={`row-item tap ${open ? 'open' : ''}`} key={t.id}>
              <button type="button" className="row-main" onClick={() => setOpenId(open ? null : t.id)}>
                <div className="left">
                  <div className={`av ${out ? 'out' : 'in'}`}>{t.txn_type.slice(0, 2)}</div>
                  <div>
                    <strong>{labelTxn(t.txn_type)}</strong>
                    <small>{relativeTime(t.created_at)} · {t.status}</small>
                  </div>
                </div>
                <div className={`money ${out ? 'out' : 'in'}`}>
                  {out ? '−' : '+'}{money(t.amount)}
                </div>
              </button>
              {open && (
                <div className="txn-detail">
                  <div className="fee-line"><span>TrxID</span><b>{t.id}</b></div>
                  <div className="fee-line"><span>Amount</span><b>{money(t.amount)}</b></div>
                  <div className="fee-line"><span>Fee</span><b>{money(t.fee)}</b></div>
                  <div className="fee-line"><span>Note</span><b>{t.note || '—'}</b></div>
                  <div className="fee-line"><span>Rail</span><b>{t.rail_ref || '—'}</b></div>
                  <div className="fee-line"><span>When</span><b>{new Date(t.created_at).toLocaleString()}</b></div>
                  <button
                    type="button"
                    className="chip on"
                    onClick={() => { void navigator.clipboard?.writeText(t.id) }}
                  >
                    Copy TrxID
                  </button>
                </div>
              )}
            </div>
          )
        })}
        {!rows.length && <div className="empty">No matching transactions</div>}
      </div>
    </section>
  )
}
