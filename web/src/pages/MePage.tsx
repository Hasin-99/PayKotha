import { useMemo, useState } from 'react'
import { api } from '../api'
import type { Favorite, Txn, User } from '../api'
import { BRAND } from '../brand'
import {
  initials,
  kycLabel,
  kycRank,
  limitPct,
  memberSince,
  monthStats,
  spentToday,
} from '../lib/walletStats'

const money = (n: number) =>
  `৳${Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

type Props = {
  token: string
  user: User
  txns: Txn[]
  favs: Favorite[]
  liveConnected: boolean
  unread: number
  pendingRequests: number
  onRefresh: () => Promise<void>
  onFlash: (type: 'ok' | 'err', text: string) => void
  onOpenFlow: (id: 'more' | 'ops' | 'savings' | 'request' | 'addmoney' | 'bank') => void
  onNav: (nav: 'history' | 'inbox' | 'home') => void
  onLogout: () => void
  oldPin: string
  newPin: string
  setOldPin: (v: string) => void
  setNewPin: (v: string) => void
  setSessionPin: (v: string) => void
  favLabel: string
  favPhone: string
  setFavLabel: (v: string) => void
  setFavPhone: (v: string) => void
}

type Panel = null | 'security' | 'kyc' | 'favorites' | 'limits' | 'about'

export function MePage(props: Props) {
  const {
    token, user, txns, favs, liveConnected, unread, pendingRequests,
    onRefresh, onFlash, onOpenFlow, onNav, onLogout,
    oldPin, newPin, setOldPin, setNewPin, setSessionPin,
    favLabel, favPhone, setFavLabel, setFavPhone,
  } = props

  const [panel, setPanel] = useState<Panel>(null)
  const [busy, setBusy] = useState(false)
  const [nid, setNid] = useState('1990123456789')

  const spent = useMemo(() => spentToday(txns, user.id), [txns, user.id])
  const month = useMemo(() => monthStats(txns, user.id), [txns, user.id])
  const pct = limitPct(spent, user.daily_limit)
  const rank = kycRank(user.kyc_level)

  async function upgrade(level: string) {
    setBusy(true)
    try {
      await api.upgradeKyc(token, level, nid)
      await onRefresh()
      onFlash('ok', `KYC upgraded to ${level}`)
    } catch (e) {
      onFlash('err', e instanceof Error ? e.message : 'KYC failed')
    } finally {
      setBusy(false)
    }
  }

  async function updatePin() {
    setBusy(true)
    try {
      await api.changePin(token, oldPin, newPin)
      localStorage.setItem('paykotha_pin', newPin)
      setSessionPin(newPin)
      setOldPin('')
      setNewPin('')
      onFlash('ok', 'PIN updated')
    } catch (e) {
      onFlash('err', e instanceof Error ? e.message : 'PIN update failed')
    } finally {
      setBusy(false)
    }
  }

  async function addFav() {
    if (!favLabel.trim() || !favPhone.trim()) return onFlash('err', 'Enter label and mobile')
    setBusy(true)
    try {
      await api.addFavorite(token, favLabel, favPhone)
      setFavLabel('')
      setFavPhone('')
      await onRefresh()
      onFlash('ok', 'Favorite saved')
    } catch (e) {
      onFlash('err', e instanceof Error ? e.message : 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  function toggle(p: Panel) {
    setPanel((cur) => (cur === p ? null : p))
  }

  return (
    <section className="block me-page" style={{ paddingTop: '0.85rem' }}>
      <div className="me-hero">
        <div className="me-hero-top">
          <div className="me-avatar" aria-hidden>{initials(user.name)}</div>
          <div className="me-hero-text">
            <h3>{user.name}</h3>
            <p>{user.phone}</p>
            <div className="me-badges">
              <span className={`pill kyc k${rank}`}>{kycLabel(user.kyc_level)}</span>
              <span className={`pill live ${liveConnected ? '' : 'off'}`}>{liveConnected ? 'LIVE' : 'Offline'}</span>
              {user.is_admin ? <span className="pill admin">Ops</span> : null}
            </div>
          </div>
        </div>
        <div className="me-meta-row">
          <span>Member since {memberSince(user)}</span>
          <span>ID {user.id}</span>
        </div>
      </div>

      <div className="insight-grid">
        <button type="button" className="insight" onClick={() => onNav('history')}>
          <em>Wallet</em>
          <strong>{money(user.balance)}</strong>
        </button>
        <button type="button" className="insight" onClick={() => onOpenFlow('savings')}>
          <em>Savings</em>
          <strong>{money(user.savings_balance)}</strong>
        </button>
        <button type="button" className="insight" onClick={() => onNav('history')}>
          <em>Spent today</em>
          <strong>{money(spent)}</strong>
        </button>
        <button type="button" className="insight" onClick={() => onNav('inbox')}>
          <em>Inbox</em>
          <strong>{unread + pendingRequests}</strong>
        </button>
      </div>

      <div className="limit-card">
        <div className="limit-head">
          <span>Daily limit</span>
          <b>{money(spent)} / {money(user.daily_limit)}</b>
        </div>
        <div className="limit-track" aria-hidden>
          <i style={{ width: `${pct}%` }} />
        </div>
        <p className="muted tiny">This month · in {money(month.inflow)} · out {money(month.outflow)} · fees {money(month.fees)}</p>
      </div>

      <div className="menu-list">
        <button type="button" className="menu-row" onClick={() => toggle('kyc')}>
          <span>
            <b>Identity & KYC</b>
            <small>{kycLabel(user.kyc_level)} · raise limits</small>
          </span>
          <em>{panel === 'kyc' ? '−' : '+'}</em>
        </button>
        {panel === 'kyc' && (
          <div className="panel-card">
            <div className="kyc-steps">
              <div className={`kyc-step ${rank >= 0 ? 'on' : ''}`}><b>L0</b><span>Basic</span></div>
              <div className={`kyc-step ${rank >= 1 ? 'on' : ''}`}><b>L1</b><span>NID</span></div>
              <div className={`kyc-step ${rank >= 2 ? 'on' : ''}`}><b>L2</b><span>Full</span></div>
            </div>
            <label className="lbl">NID number
              <input value={nid} onChange={(e) => setNid(e.target.value)} inputMode="numeric" />
            </label>
            <div className="btn-row">
              <button type="button" className="btn soft" disabled={busy || rank >= 1} onClick={() => upgrade('L1_NID')}>Upgrade L1</button>
              <button type="button" className="btn" disabled={busy || rank >= 2} onClick={() => upgrade('L2_FULL')}>Upgrade L2</button>
            </div>
            <p className="muted tiny">L1 · ৳25k/txn · L2 · ৳200k/txn & higher wallet cap</p>
          </div>
        )}

        <button type="button" className="menu-row" onClick={() => toggle('security')}>
          <span>
            <b>Security · PIN</b>
            <small>Change wallet PIN · OTP on large sends</small>
          </span>
          <em>{panel === 'security' ? '−' : '+'}</em>
        </button>
        {panel === 'security' && (
          <div className="panel-card">
            <label className="lbl">Current PIN<input type="password" value={oldPin} onChange={(e) => setOldPin(e.target.value)} inputMode="numeric" maxLength={6} /></label>
            <label className="lbl">New PIN<input type="password" value={newPin} onChange={(e) => setNewPin(e.target.value)} inputMode="numeric" maxLength={6} /></label>
            <button type="button" className="btn" disabled={busy || newPin.length < 4} onClick={updatePin}>Update PIN</button>
          </div>
        )}

        <button type="button" className="menu-row" onClick={() => toggle('favorites')}>
          <span>
            <b>Favorites</b>
            <small>{favs.length} saved contacts for Send Money</small>
          </span>
          <em>{panel === 'favorites' ? '−' : '+'}</em>
        </button>
        {panel === 'favorites' && (
          <div className="panel-card">
            {favs.map((f) => (
              <div className="fav-row" key={f.id}>
                <div>
                  <b>{f.label}</b>
                  <small>{f.phone}</small>
                </div>
                <button
                  type="button"
                  className="chip"
                  onClick={() => api.deleteFavorite(token, f.id).then(onRefresh).then(() => onFlash('ok', 'Removed'))}
                >
                  Remove
                </button>
              </div>
            ))}
            {!favs.length && <p className="muted tiny">No favorites yet</p>}
            <label className="lbl">Label<input value={favLabel} onChange={(e) => setFavLabel(e.target.value)} placeholder="Bob" /></label>
            <label className="lbl">Mobile<input value={favPhone} onChange={(e) => setFavPhone(e.target.value)} inputMode="tel" placeholder="01XXXXXXXXX" /></label>
            <button type="button" className="btn soft" disabled={busy} onClick={addFav}>Add favorite</button>
          </div>
        )}

        <button type="button" className="menu-row" onClick={() => toggle('limits')}>
          <span>
            <b>Limits & fees</b>
            <small>Cash out 1.8% · Bank ৳10 · Merchant 1%</small>
          </span>
          <em>{panel === 'limits' ? '−' : '+'}</em>
        </button>
        {panel === 'limits' && (
          <div className="panel-card">
            <div className="fee-line"><span>Daily limit</span><b>{money(user.daily_limit)}</b></div>
            <div className="fee-line"><span>Cash out fee</span><b>1.8%</b></div>
            <div className="fee-line"><span>Bank transfer</span><b>৳10</b></div>
            <div className="fee-line"><span>Merchant / QR</span><b>1%</b></div>
            <div className="fee-line"><span>Bill (≥৳100)</span><b>৳5</b></div>
            <div className="fee-line"><span>OTP step-up</span><b>≥ ৳5,000</b></div>
            <div className="fee-line"><span>Linked bank</span><b>{user.bank_account || 'Not linked yet'}</b></div>
          </div>
        )}

        <button type="button" className="menu-row" onClick={() => onOpenFlow('addmoney')}>
          <span><b>Add money</b><small>Bank → wallet</small></span><em>›</em>
        </button>
        <button type="button" className="menu-row" onClick={() => onOpenFlow('bank')}>
          <span><b>Bank transfer</b><small>Wallet → bank account</small></span><em>›</em>
        </button>
        <button type="button" className="menu-row" onClick={() => onOpenFlow('savings')}>
          <span><b>Savings pot</b><small>{money(user.savings_balance)} saved</small></span><em>›</em>
        </button>
        <button type="button" className="menu-row" onClick={() => onOpenFlow('request')}>
          <span><b>Request money</b><small>{pendingRequests} pending</small></span><em>›</em>
        </button>
        <button type="button" className="menu-row" onClick={() => onNav('history')}>
          <span><b>Full statement</b><small>{month.count} txns this month</small></span><em>›</em>
        </button>
        <button
          type="button"
          className="menu-row"
          onClick={() => api.exportExcel(token).then((r) => onFlash('ok', r.message)).catch((e) => onFlash('err', e.message))}
        >
          <span><b>Download Excel</b><small>Course / portfolio export</small></span><em>›</em>
        </button>
        {user.is_admin && (
          <button type="button" className="menu-row" onClick={() => onOpenFlow('ops')}>
            <span><b>Ops Desk</b><small>Settlement · reversals · audit</small></span><em>›</em>
          </button>
        )}
        <button type="button" className="menu-row" onClick={() => toggle('about')}>
          <span><b>About PayKotha</b><small>{BRAND.motto}</small></span>
          <em>{panel === 'about' ? '−' : '+'}</em>
        </button>
        {panel === 'about' && (
          <div className="panel-card">
            <p className="dict-bn" style={{ margin: 0 }}>{BRAND.mottoBn}</p>
            <p className="muted tiny" style={{ marginTop: '0.45rem' }}>{BRAND.example}</p>
            <p className="muted tiny">Sandbox core-banking wallet · not a licensed MFS.</p>
          </div>
        )}
      </div>

      <button type="button" className="btn soft" style={{ marginTop: '0.85rem' }} onClick={onLogout}>Log out</button>
    </section>
  )
}
