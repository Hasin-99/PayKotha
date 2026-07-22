import { useMemo, useState } from 'react'
import { api } from '../api'
import type { MoneyReq, Notif } from '../api'
import { relativeTime } from '../lib/walletStats'

const money = (n: number) =>
  `৳${Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

type Tab = 'action' | 'alerts'

type Props = {
  token: string
  userPhone: string
  userId: string
  requests: MoneyReq[]
  notifs: Notif[]
  onRefresh: () => Promise<void>
  onFlash: (type: 'ok' | 'err', text: string) => void
  onRequestMoney: () => void
}

export function InboxPage({
  token, userPhone, userId, requests, notifs, onRefresh, onFlash, onRequestMoney,
}: Props) {
  const [tab, setTab] = useState<Tab>('action')

  const pending = useMemo(
    () => requests.filter((r) => r.status === 'PENDING'),
    [requests],
  )
  const unread = useMemo(() => notifs.filter((n) => !n.is_read).length, [notifs])

  return (
    <section className="block inbox-page" style={{ paddingTop: '0.85rem' }}>
      <div className="page-head">
        <div>
          <h3 style={{ margin: 0 }}>Inbox</h3>
          <p className="muted tiny" style={{ margin: '0.2rem 0 0' }}>
            {pending.length} requests · {unread} unread
          </p>
        </div>
        <button
          type="button"
          className="chip"
          onClick={() => api.readNotifications(token).then(onRefresh).then(() => onFlash('ok', 'Marked read'))}
        >
          Mark read
        </button>
      </div>

      <div className="seg">
        <button type="button" className={tab === 'action' ? 'on' : ''} onClick={() => setTab('action')}>
          Action ({pending.length})
        </button>
        <button type="button" className={tab === 'alerts' ? 'on' : ''} onClick={() => setTab('alerts')}>
          Alerts ({notifs.length})
        </button>
      </div>

      {tab === 'action' ? (
        <div className="list" style={{ marginTop: '0.75rem' }}>
          {pending.map((r) => {
            const mine = r.requester_id === userId
            const toPay = r.payer_phone === userPhone
            return (
              <div className="action-card" key={r.id}>
                <div className="action-top">
                  <span className={`pill ${toPay ? 'pay' : 'ask'}`}>{toPay ? 'Pay' : 'Your ask'}</span>
                  <small>{relativeTime(r.created_at)}</small>
                </div>
                <h4>{money(r.amount)}</h4>
                <p className="muted tiny">
                  {mine ? `Asking ${r.payer_phone}` : `Pay to requester`} · {r.note || 'Money request'}
                </p>
                <p className="muted tiny">ID {r.id}</p>
                <div className="btn-row">
                  {toPay && (
                    <button
                      type="button"
                      className="btn soft"
                      onClick={() => api.payRequest(token, r.id).then(onRefresh).then(() => onFlash('ok', 'Paid'))
                        .catch((e) => onFlash('err', e.message))}
                    >
                      Pay now
                    </button>
                  )}
                  {mine && (
                    <button
                      type="button"
                      className="btn ghost"
                      onClick={() => api.cancelRequest(token, r.id).then(onRefresh).then(() => onFlash('ok', 'Cancelled'))
                        .catch((e) => onFlash('err', e.message))}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            )
          })}
          {!pending.length && (
            <div className="empty-card">
              <p>No pending requests</p>
              <button type="button" className="btn" onClick={onRequestMoney}>Request money</button>
            </div>
          )}
        </div>
      ) : (
        <div className="list" style={{ marginTop: '0.75rem' }}>
          {notifs.map((n) => (
            <div className={`notif-card ${n.is_read ? '' : 'new'}`} key={n.id}>
              <div className="action-top">
                <h4 style={{ margin: 0 }}>{n.title}</h4>
                <small>{relativeTime(n.created_at)}</small>
              </div>
              <p className="muted tiny">{n.body}</p>
              {!n.is_read && <span className="dot-new">New</span>}
            </div>
          ))}
          {!notifs.length && <div className="empty">No alerts yet</div>}
        </div>
      )}
    </section>
  )
}
