import { useMemo, useState } from 'react'
import type { Txn, User } from '../api'
import { initials } from '../lib/walletStats'

const money = (n: number) =>
  `৳${Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const MERCHANTS = [
  { code: 'SHOP-9A2F', name: 'Corner Mart' },
  { code: 'CAFE-42', name: 'Cafe Lexicon' },
  { code: 'MART-77', name: 'City Mart' },
  { code: 'FUEL-12', name: 'Padma Fuel' },
]

type Mode = 'receive' | 'pay'

type Props = {
  user: User
  merchant: string
  setMerchant: (v: string) => void
  setAmountStr: (v: string) => void
  txns: Txn[]
  onPay: () => void
  onFlash: (type: 'ok' | 'err', text: string) => void
}

export function ScanPage({ user, merchant, setMerchant, setAmountStr, txns, onPay, onFlash }: Props) {
  const [mode, setMode] = useState<Mode>('receive')

  const recentMerchants = useMemo(() => {
    const codes = new Set<string>()
    for (const t of txns) {
      if (t.txn_type !== 'MERCHANT') continue
      try {
        const meta = t.meta ? JSON.parse(t.meta) : null
        if (meta?.merchant_code) codes.add(String(meta.merchant_code))
      } catch {
        /* ignore */
      }
      if (codes.size >= 4) break
    }
    return Array.from(codes)
  }, [txns])

  function copyReceive() {
    const text = `PayKotha · ${user.name}\n${user.phone}\nSend money on PayKotha`
    void navigator.clipboard?.writeText(text)
    onFlash('ok', 'Receive details copied')
  }

  return (
    <section className="block scan-page" style={{ paddingTop: '0.85rem' }}>
      <div className="seg">
        <button type="button" className={mode === 'receive' ? 'on' : ''} onClick={() => setMode('receive')}>Receive</button>
        <button type="button" className={mode === 'pay' ? 'on' : ''} onClick={() => setMode('pay')}>Pay QR</button>
      </div>

      {mode === 'receive' ? (
        <div className="receive-panel">
          <div className="qr big">
            <span className="qr-brand">PK</span>
            <strong>{initials(user.name)}</strong>
            <em>{user.phone.slice(-4)}</em>
          </div>
          <h3 style={{ margin: '0.85rem 0 0.2rem' }}>{user.name}</h3>
          <p className="muted tiny" style={{ margin: 0 }}>{user.phone}</p>
          <p className="muted tiny">Show this code to receive PayKotha transfers</p>
          <div className="btn-row">
            <button type="button" className="btn soft" onClick={copyReceive}>Copy details</button>
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                void navigator.clipboard?.writeText(user.phone)
                onFlash('ok', 'Mobile copied')
              }}
            >
              Copy mobile
            </button>
          </div>
        </div>
      ) : (
        <div className="pay-panel">
          <h3 style={{ marginTop: 0 }}>Pay merchant</h3>
          <p className="muted tiny">Enter or pick a merchant / QR code</p>
          <label className="lbl">
            Merchant / QR code
            <input value={merchant} onChange={(e) => setMerchant(e.target.value.toUpperCase())} placeholder="SHOP-9A2F" />
          </label>

          <p className="section-label">Quick codes</p>
          <div className="merchant-grid">
            {MERCHANTS.map((m) => (
              <button
                key={m.code}
                type="button"
                className={`merchant-tile ${merchant === m.code ? 'on' : ''}`}
                onClick={() => setMerchant(m.code)}
              >
                <b>{m.name}</b>
                <small>{m.code}</small>
              </button>
            ))}
          </div>

          {recentMerchants.length > 0 && (
            <>
              <p className="section-label">Recent</p>
              <div className="chips">
                {recentMerchants.map((code) => (
                  <button key={code} type="button" className={`chip ${merchant === code ? 'on' : ''}`} onClick={() => setMerchant(code)}>
                    {code}
                  </button>
                ))}
              </div>
            </>
          )}

          <p className="section-label">Amount shortcuts</p>
          <div className="chips">
            {[50, 100, 200, 500].map((a) => (
              <button key={a} type="button" className="chip" onClick={() => setAmountStr(String(a))}>
                {money(a)}
              </button>
            ))}
          </div>

          <button type="button" className="btn" style={{ marginTop: '0.65rem' }} onClick={onPay}>
            Continue to Pay
          </button>
        </div>
      )}
    </section>
  )
}
