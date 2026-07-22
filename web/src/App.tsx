import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { animate, createTimeline, stagger } from 'animejs'
import { api } from './api'
import type { Favorite, MoneyReq, Notif, Reversal, Txn, User } from './api'
import { BRAND } from './brand'
import { AmountKeypad } from './components/AmountKeypad'
import {
  IconAdd, IconBack, IconBank, IconBell, IconBill, IconCashIn, IconCashOut,
  IconCheck, IconEye, IconHeart, IconHistory, IconHome, IconInbox, IconPhone,
  IconQr, IconRequest, IconSavings, IconSend, IconUser,
} from './components/Icons'
import { useLiveWallet } from './hooks/useLiveWallet'
import { pulseSuccess, shakeError } from './motion'
import { isOutflow, limitPct, spentToday } from './lib/walletStats'
import { HistoryPage } from './pages/HistoryPage'
import { InboxPage } from './pages/InboxPage'
import { MePage } from './pages/MePage'
import { ScanPage } from './pages/ScanPage'

type Mode = 'login' | 'register'
type Nav = 'home' | 'history' | 'scan' | 'inbox' | 'me'
type Flow =
  | null
  | 'send' | 'cashin' | 'cashout' | 'addmoney' | 'recharge' | 'bills'
  | 'merchant' | 'bank' | 'request' | 'savings' | 'donate' | 'more' | 'ops'
type Step = 'details' | 'amount' | 'confirm' | 'success'

const money = (n: number) =>
  `৳${Number(n || 0).toLocaleString('en-BD', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

const TITLES: Record<Exclude<Flow, null>, string> = {
  send: 'Send Money', cashin: 'Cash In', cashout: 'Cash Out', addmoney: 'Add Money',
  recharge: 'Mobile Recharge', bills: 'Pay Bill', merchant: 'Payment', bank: 'Bank Transfer',
  request: 'Request Money', savings: 'Savings', donate: 'Donation',   more: 'My Account', ops: 'Ops Desk',
}

const QUICK: { id: Flow; label: string; color: string; soft: string; icon: ReactNode }[] = [
  { id: 'send', label: 'Send', color: '#e2136e', soft: '#fce4ef', icon: <IconSend /> },
  { id: 'cashin', label: 'Cash In', color: '#00897b', soft: '#e0f2f1', icon: <IconCashIn /> },
  { id: 'cashout', label: 'Cash Out', color: '#ef6c00', soft: '#fff3e0', icon: <IconCashOut /> },
  { id: 'merchant', label: 'Pay', color: '#6a1b9a', soft: '#f3e5f5', icon: <IconQr /> },
]

const SERVICES: { id: Flow; label: string; color: string; soft: string; icon: ReactNode }[] = [
  { id: 'recharge', label: 'Mobile\nRecharge', color: '#e2136e', soft: '#fce4ef', icon: <IconPhone /> },
  { id: 'bills', label: 'Pay\nBill', color: '#00897b', soft: '#e0f2f1', icon: <IconBill /> },
  { id: 'addmoney', label: 'Add\nMoney', color: '#1565c0', soft: '#e3f2fd', icon: <IconAdd /> },
  { id: 'bank', label: 'Bank\nTransfer', color: '#ef6c00', soft: '#fff3e0', icon: <IconBank /> },
  { id: 'request', label: 'Request\nMoney', color: '#c2185b', soft: '#fce4ef', icon: <IconRequest /> },
  { id: 'savings', label: 'Savings', color: '#2e7d32', soft: '#e8f5e9', icon: <IconSavings /> },
  { id: 'donate', label: 'Donation', color: '#ad1457', soft: '#fce4ef', icon: <IconHeart /> },
  { id: 'more', label: 'My\nAccount', color: '#546e7a', soft: '#eceff1', icon: <IconUser /> },
]

function feeFor(flow: Flow, amount: number) {
  if (flow === 'cashout') return +(amount * 0.018).toFixed(2)
  if (flow === 'bank') return 10
  if (flow === 'merchant') return +(amount * 0.01).toFixed(2)
  if (flow === 'bills' && amount >= 100) return 5
  return 0
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('paykotha_token'))
  const [user, setUser] = useState<User | null>(null)
  const [mode, setMode] = useState<Mode>('login')
  const [nav, setNav] = useState<Nav>('home')
  const [flow, setFlow] = useState<Flow>(null)
  const [step, setStep] = useState<Step>('details')
  const [txns, setTxns] = useState<Txn[]>([])
  const [requests, setRequests] = useState<MoneyReq[]>([])
  const [notifs, setNotifs] = useState<Notif[]>([])
  const [favs, setFavs] = useState<Favorite[]>([])
  const [operators, setOperators] = useState<string[]>([])
  const [billers, setBillers] = useState<Record<string, string>>({})
  const [flash, setFlash] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [hiddenBal, setHiddenBal] = useState(false)
  const [amountStr, setAmountStr] = useState('100')
  const [sessionPin, setSessionPin] = useState(() => localStorage.getItem('paykotha_pin') || '')
  const [confirmPin, setConfirmPin] = useState('')
  const [lastTxn, setLastTxn] = useState<Txn | null>(null)

  const [phone, setPhone] = useState('01711111111')
  const [pin, setPin] = useState('1234')
  const [name, setName] = useState('Alice Rahman')
  const [opening, setOpening] = useState(2000)
  const [toPhone, setToPhone] = useState('01722222222')
  const [note, setNote] = useState('')
  const [operator, setOperator] = useState('Grameenphone')
  const [rechargeMobile, setRechargeMobile] = useState('01711111111')
  const [biller, setBiller] = useState('DESCO')
  const [accountNo, setAccountNo] = useState('1234567890')
  const [merchant, setMerchant] = useState('SHOP-9A2F')
  const [bankAcc, setBankAcc] = useState('1209123456789')
  const [cause, setCause] = useState('Flood relief')
  const [oldPin, setOldPin] = useState('')
  const [newPin, setNewPin] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpHint, setOtpHint] = useState('')
  const [otpChallengeId, setOtpChallengeId] = useState('')
  const [otpAbove, setOtpAbove] = useState(5000)
  const [revTxnId, setRevTxnId] = useState('')
  const [revReason, setRevReason] = useState('Customer dispute')
  const [opsMsg, setOpsMsg] = useState('')
  const [opsReversals, setOpsReversals] = useState<Reversal[]>([])
  const [savingsMode, setSavingsMode] = useState<'in' | 'out'>('in')
  const [favLabel, setFavLabel] = useState('')
  const [favPhone, setFavPhone] = useState('')

  const authRef = useRef<HTMLDivElement>(null)
  const balanceRef = useRef<HTMLParagraphElement>(null)
  const toastRef = useRef<HTMLDivElement>(null)
  const successRef = useRef<HTMLDivElement>(null)
  const homeAnim = useRef<HTMLDivElement>(null)
  const lastToastRef = useRef('')

  const live = useLiveWallet(token, user, setUser, setTxns, setNotifs, balanceRef, setRequests)
  const amount = Number(amountStr) || 0
  const fee = feeFor(flow, amount)
  const clock = useMemo(() => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), [user?.id, nav])

  async function refresh(t = token) {
    if (!t) return
    const [me, history, reqs, ns, fs] = await Promise.all([
      api.me(t), api.history(t), api.listRequests(t), api.notifications(t), api.favorites(t),
    ])
    setUser(me); setTxns(history); setRequests(reqs); setNotifs(ns); setFavs(fs)
  }

  useEffect(() => {
    api.catalog().then((c) => {
      setOperators(c.operators)
      setBillers(c.billers)
      if (c.require_otp_above) setOtpAbove(c.require_otp_above)
      if (c.operators[0]) setOperator(c.operators[0])
      const first = Object.keys(c.billers)[0]
      if (first) setBiller(first)
    }).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!token) return
    refresh(token).catch(async () => {
      const rt = localStorage.getItem('paykotha_refresh')
      if (rt) {
        try {
          const tokens = await api.refresh(rt)
          localStorage.setItem('paykotha_token', tokens.access_token)
          if (tokens.refresh_token) localStorage.setItem('paykotha_refresh', tokens.refresh_token)
          setToken(tokens.access_token)
          return
        } catch {
          /* fall through */
        }
      }
      localStorage.removeItem('paykotha_token')
      localStorage.removeItem('paykotha_refresh')
      localStorage.removeItem('paykotha_pin')
      setToken(null)
      setUser(null)
    })
  }, [token])

  useEffect(() => {
    if (user || !authRef.current) return
    const root = authRef.current
    const sheet = root.querySelector('.auth-sheet')
    const tl = createTimeline({ defaults: { ease: 'outExpo' } })
    tl.add(root.querySelectorAll('.dict-word, .dict-meta, .dict-def, .dict-bn, .dict-ex'), {
      opacity: [0, 1],
      translateY: [28, 0],
      delay: stagger(90),
      duration: 720,
    })
    if (sheet) {
      tl.add(sheet, { opacity: [0, 1], translateY: [40, 0], duration: 650 }, '-=400')
    }
  }, [user])

  useEffect(() => {
    if (!user || flow || nav !== 'home' || !homeAnim.current) return
    createTimeline({ defaults: { ease: 'outBack(1.5)' } }).add(
      homeAnim.current.querySelectorAll('.quick button, .svc'),
      { scale: [0.82, 1], opacity: [0, 1], delay: stagger(22), duration: 380 },
    )
  }, [user?.id, nav, flow])

  function show(type: 'ok' | 'err', text: string) {
    setFlash({ type, text })
  }

  useEffect(() => {
    if (!flash || !toastRef.current) return
    if (flash.type === 'ok') pulseSuccess(toastRef.current)
    else shakeError(toastRef.current)
    const t = setTimeout(() => setFlash(null), 2800)
    return () => clearTimeout(t)
  }, [flash])

  useEffect(() => {
    if (!live.latestToast || live.latestToast === lastToastRef.current) return
    lastToastRef.current = live.latestToast
    show('ok', `Live · ${live.latestToast}`)
  }, [live.latestToast])

  useEffect(() => {
    if (step === 'success' && successRef.current) {
      const check = successRef.current.querySelector('.check')
      if (check) {
        animate(check, {
          scale: [0.4, 1],
          opacity: [0, 1],
          duration: 550,
          ease: 'outBack(1.8)',
        })
      }
    }
  }, [step])

  function openFlow(id: Flow) {
    if (id === 'more') {
      setNav('me')
      setFlow(null)
      return
    }
    setFlow(id)
    setStep('details')
    setConfirmPin('')
    setLastTxn(null)
    setOtpCode('')
    setOtpChallengeId('')
    setAmountStr('100')
    setSavingsMode('in')
    setNav('home')
  }

  function closeFlow() {
    if (step === 'amount') setStep('details')
    else if (step === 'confirm') setStep('amount')
    else if (step === 'success') {
      setFlow(null)
      setStep('details')
    } else {
      setFlow(null)
      setStep('details')
    }
  }

  async function onAuth(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setFlash(null)
    try {
      if (mode === 'register') await api.register({ name, phone, pin, opening_balance: opening })
      const { access_token, refresh_token } = await api.login({ phone, pin })
      localStorage.setItem('paykotha_token', access_token)
      if (refresh_token) localStorage.setItem('paykotha_refresh', refresh_token)
      localStorage.setItem('paykotha_pin', pin)
      setSessionPin(pin)
      setToken(access_token)
    } catch (err) {
      show('err', err instanceof Error ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  async function ensureOtp(purpose: 'TRANSFER' | 'CASH_OUT') {
    if (!token || amount < otpAbove) return undefined
    if (otpChallengeId && otpCode) return { otp_challenge_id: otpChallengeId, otp_code: otpCode }
    const ch = await api.issueOtp(token, purpose)
    setOtpChallengeId(ch.challenge_id)
    setOtpHint(ch.sandbox_code || '')
    throw new Error(`OTP required (≥ ${money(otpAbove)}). Code: ${ch.sandbox_code}`)
  }

  function validateDetails(): string | null {
    if (flow === 'send' || flow === 'request') {
      if (!/^01[3-9]\d{8}$/.test(toPhone)) return 'Enter a valid BD mobile number'
    }
    if (flow === 'recharge' && !/^01[3-9]\d{8}$/.test(rechargeMobile)) return 'Enter valid mobile'
    if (flow === 'bills' && !accountNo.trim()) return 'Enter consumer number'
    if (flow === 'merchant' && merchant.trim().length < 4) return 'Enter merchant / QR code'
    if ((flow === 'bank' || flow === 'addmoney') && bankAcc.trim().length < 8) return 'Enter valid bank account'
    return null
  }

  function goAmount() {
    const err = validateDetails()
    if (err) return show('err', err)
    setStep('amount')
  }

  function goConfirm() {
    if (amount <= 0) return show('err', 'Enter an amount')
    if (flow === 'recharge' && (amount < 20 || amount > 1000)) return show('err', 'Recharge ৳20–৳1000')
    setStep('confirm')
    setConfirmPin('')
  }

  async function submitPayment() {
    if (!token || !flow) return
    if (confirmPin.length < 4) return show('err', 'Enter your PIN')
    if (sessionPin && confirmPin !== sessionPin) return show('err', 'Incorrect PIN')
    setBusy(true)
    setFlash(null)
    try {
      let t: Txn | null = null
      if (flow === 'send') {
        const otp = await ensureOtp('TRANSFER')
        t = await api.send(token, toPhone, amount, note || 'Send money', otp)
      } else if (flow === 'cashin') t = await api.cashIn(token, amount, note)
      else if (flow === 'cashout') {
        const otp = await ensureOtp('CASH_OUT')
        t = await api.cashOut(token, amount, note, otp)
      } else if (flow === 'addmoney') t = await api.addMoney(token, amount, bankAcc)
      else if (flow === 'recharge') t = await api.recharge(token, operator, rechargeMobile, amount)
      else if (flow === 'bills') t = await api.billPay(token, biller, accountNo, amount)
      else if (flow === 'merchant') t = await api.merchantPay(token, merchant, amount, note)
      else if (flow === 'bank') {
        const otp = await ensureOtp('TRANSFER')
        t = await api.bankTransfer(token, bankAcc, amount, otp)
      } else if (flow === 'request') {
        const r = await api.createRequest(token, toPhone, amount, note)
        show('ok', `Request ${r.id} created`)
        await refresh()
        setFlow(null)
        return
      } else if (flow === 'savings') {
        t = savingsMode === 'out' ? await api.savingsOut(token, amount) : await api.savingsIn(token, amount)
      } else if (flow === 'donate') t = await api.donate(token, cause, amount)

      if (t) {
        setLastTxn(t)
        setStep('success')
        setOtpCode('')
        setOtpChallengeId('')
        await refresh()
      }
    } catch (err) {
      show('err', err instanceof Error ? err.message : 'Transaction failed')
    } finally {
      setBusy(false)
    }
  }

  function logout() {
    localStorage.removeItem('paykotha_token')
    localStorage.removeItem('paykotha_refresh')
    localStorage.removeItem('paykotha_pin')
    setToken(null)
    setUser(null)
  }

  const unread = live.unread || notifs.filter((n) => !n.is_read).length
  const pendingReqs = requests.filter((r) => r.status === 'PENDING')
  const todaySpend = user ? spentToday(txns, user.id) : 0
  const dailyPct = user ? limitPct(todaySpend, user.daily_limit) : 0

  function pinPress(k: string) {
    if (k === '⌫') {
      setConfirmPin((p) => p.slice(0, -1))
      return
    }
    if (confirmPin.length >= 6) return
    setConfirmPin((p) => p + k)
  }

  if (!user || !token) {
    return (
      <div className="stage">
        <div className="phone">
          <div className="auth" ref={authRef}>
            <div className="auth-top">
              <div className="dict-card">
                <div className="dict-eyebrow">Word of the wallet</div>
                <h1 className="dict-word logo">{BRAND.name}</h1>
                <p className="dict-meta">
                  <em>{BRAND.phonetic}</em>
                  <span>·</span>
                  <span>{BRAND.partOfSpeech}</span>
                </p>
                <p className="dict-def">{BRAND.motto}</p>
                <p className="dict-bn">{BRAND.mottoBn}</p>
                <p className="dict-ex">{BRAND.example}</p>
              </div>
            </div>
            <form className="auth-sheet" onSubmit={onAuth}>
              <div className="seg">
                <button type="button" className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>Log in</button>
                <button type="button" className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>Register</button>
              </div>
              {mode === 'register' && (
                <>
                  <label className="lbl">Name<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
                  <label className="lbl">Opening balance<input type="number" value={opening} onChange={(e) => setOpening(Number(e.target.value))} /></label>
                </>
              )}
              <label className="lbl">Mobile number<input value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" required /></label>
              <label className="lbl">PIN<input type="password" value={pin} onChange={(e) => setPin(e.target.value)} inputMode="numeric" required minLength={4} maxLength={6} /></label>
              <button className="btn" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}</button>
              {flash && <div className="errbox">{flash.text}</div>}
              <p className="hint">Demo · Alice 01711111111 / 1234 · Bob 01722222222 / 5678</p>
            </form>
          </div>
        </div>
      </div>
    )
  }

  const confirmLines: { k: string; v: string }[] = []
  if (flow === 'send' || flow === 'request') confirmLines.push({ k: 'To', v: toPhone })
  if (flow === 'recharge') {
    confirmLines.push({ k: 'Operator', v: operator })
    confirmLines.push({ k: 'Mobile', v: rechargeMobile })
  }
  if (flow === 'bills') {
    confirmLines.push({ k: 'Biller', v: billers[biller] || biller })
    confirmLines.push({ k: 'Account', v: accountNo })
  }
  if (flow === 'merchant') confirmLines.push({ k: 'Merchant', v: merchant })
  if (flow === 'bank' || flow === 'addmoney') confirmLines.push({ k: 'Bank A/C', v: bankAcc })
  if (flow === 'donate') confirmLines.push({ k: 'Cause', v: cause })
  if (flow === 'savings') confirmLines.push({ k: 'Action', v: savingsMode === 'out' ? 'Withdraw from savings' : 'Deposit to savings' })
  confirmLines.push({ k: 'Amount', v: money(amount) })
  if (fee > 0) confirmLines.push({ k: 'Charge', v: money(fee) })
  confirmLines.push({ k: 'Total', v: money(amount + fee) })

  return (
    <div className="stage">
      <div className="phone">
        <div className="status-bar">
          <span>{clock}</span>
          <span className={`live-chip ${live.connected ? '' : 'off'}`}>
            <span className="d" />
            {live.connected ? 'LIVE' : '…'}
          </span>
        </div>

        <div className="scroll">
          {flow ? (
            <>
              <div className="head">
                <button type="button" className="back" onClick={closeFlow} aria-label="Back"><IconBack /></button>
                <h2>{step === 'success' ? 'Successful' : TITLES[flow]}</h2>
              </div>
              <div className="body">
                {flow !== 'more' && flow !== 'ops' && step === 'details' && (
                  <>
                    {flow === 'send' && (
                      <>
                        <label className="lbl">Receiver mobile<input value={toPhone} onChange={(e) => setToPhone(e.target.value)} inputMode="tel" placeholder="01XXXXXXXXX" /></label>
                        {favs.length > 0 && (
                          <div className="chips">
                            {favs.slice(0, 5).map((f) => (
                              <button key={f.id} type="button" className={`chip ${toPhone === f.phone ? 'on' : ''}`} onClick={() => setToPhone(f.phone)}>{f.label}</button>
                            ))}
                          </div>
                        )}
                        <label className="lbl">Reference (optional)<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Lunch" /></label>
                      </>
                    )}
                    {flow === 'cashin' && <label className="lbl">Note<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Agent cash in" /></label>}
                    {flow === 'cashout' && <label className="lbl">Note<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Agent cash out" /></label>}
                    {flow === 'recharge' && (
                      <>
                        <label className="lbl">Operator
                          <select value={operator} onChange={(e) => setOperator(e.target.value)}>{operators.map((o) => <option key={o}>{o}</option>)}</select>
                        </label>
                        <label className="lbl">Mobile<input value={rechargeMobile} onChange={(e) => setRechargeMobile(e.target.value)} inputMode="tel" /></label>
                      </>
                    )}
                    {flow === 'bills' && (
                      <>
                        <label className="lbl">Biller
                          <select value={biller} onChange={(e) => setBiller(e.target.value)}>
                            {Object.entries(billers).map(([c, l]) => <option key={c} value={c}>{l}</option>)}
                          </select>
                        </label>
                        <label className="lbl">Consumer / account no.<input value={accountNo} onChange={(e) => setAccountNo(e.target.value)} /></label>
                      </>
                    )}
                    {flow === 'merchant' && <label className="lbl">Merchant / QR code<input value={merchant} onChange={(e) => setMerchant(e.target.value)} /></label>}
                    {(flow === 'bank' || flow === 'addmoney') && <label className="lbl">Bank account<input value={bankAcc} onChange={(e) => setBankAcc(e.target.value)} /></label>}
                    {flow === 'request' && <label className="lbl">Request from<input value={toPhone} onChange={(e) => setToPhone(e.target.value)} inputMode="tel" /></label>}
                    {flow === 'donate' && <label className="lbl">Cause<input value={cause} onChange={(e) => setCause(e.target.value)} /></label>}
                    {flow === 'savings' && (
                      <>
                        <div className="seg" style={{ marginBottom: '0.75rem' }}>
                          <button type="button" className={savingsMode === 'in' ? 'on' : ''} onClick={() => setSavingsMode('in')}>Deposit</button>
                          <button type="button" className={savingsMode === 'out' ? 'on' : ''} onClick={() => setSavingsMode('out')}>Withdraw</button>
                        </div>
                        <p className="muted" style={{ fontSize: '0.82rem', margin: '0 0 0.65rem' }}>
                          Savings pot {money(user.savings_balance)} · Wallet {money(user.balance)}
                        </p>
                      </>
                    )}
                    <button className="btn" type="button" onClick={goAmount}>Next</button>
                  </>
                )}

                {flow !== 'more' && flow !== 'ops' && step === 'amount' && (
                  <>
                    <div className="amount-hero">
                      <div className="sym">Enter Amount</div>
                      <div className="big">{money(amount)}</div>
                      {fee > 0 && <div className="fee">Est. charge {money(fee)}</div>}
                    </div>
                    <AmountKeypad value={amountStr} onChange={setAmountStr} onDone={goConfirm} />
                  </>
                )}

                {flow !== 'more' && flow !== 'ops' && step === 'confirm' && (
                  <>
                    <div className="confirm-card">
                      {confirmLines.map((l) => (
                        <div className="line" key={l.k}><span>{l.k}</span><b>{l.v}</b></div>
                      ))}
                    </div>
                    {amount >= otpAbove && ['send', 'cashout', 'bank'].includes(flow || '') && (
                      <label className="lbl">
                        OTP {otpHint && `(${otpHint})`}
                        <input value={otpCode} onChange={(e) => setOtpCode(e.target.value)} inputMode="numeric" placeholder="6-digit OTP" />
                      </label>
                    )}
                    <p className="muted" style={{ textAlign: 'center', fontSize: '0.82rem', margin: '0.35rem 0' }}>Enter PIN to confirm</p>
                    <div className="pin-dots">
                      {[0, 1, 2, 3].map((i) => <i key={i} className={confirmPin.length > i ? 'on' : ''} />)}
                    </div>
                    <div className="keypad">
                      {['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫'].map((k, idx) =>
                        k === '' ? <span key={idx} /> : (
                          <button key={k} type="button" className="key" onClick={() => pinPress(k)}>{k}</button>
                        ),
                      )}
                    </div>
                    <button className="btn" style={{ marginTop: '0.75rem' }} disabled={busy || confirmPin.length < 4} onClick={submitPayment}>
                      {busy ? 'Processing…' : 'Confirm'}
                    </button>
                  </>
                )}

                {step === 'success' && lastTxn && (
                  <div className="success" ref={successRef}>
                    <div className="check"><IconCheck size={44} /></div>
                    <h3>Transaction Successful</h3>
                    <div className="amt">{money(lastTxn.amount)}</div>
                    <div className="trx">TrxID {lastTxn.id}</div>
                    <p className="muted" style={{ marginTop: '0.75rem', fontSize: '0.84rem' }}>{lastTxn.note || TITLES[flow!]}</p>
                    <button className="btn teal" style={{ marginTop: '1.25rem' }} onClick={() => { setFlow(null); setStep('details') }}>Done</button>
                  </div>
                )}

                {flow === 'more' && (
                  <>
                    <div className="card">
                      <h4>{user.name}</h4>
                      <div className="muted">{user.phone} · KYC {user.kyc_level}</div>
                    </div>
                    <button className="btn soft" onClick={() => api.upgradeKyc(token, 'L1_NID', '1990123456789').then(() => refresh()).then(() => show('ok', 'KYC upgraded'))}>Upgrade KYC</button>
                    <label className="lbl" style={{ marginTop: '0.85rem' }}>Current PIN<input type="password" value={oldPin} onChange={(e) => setOldPin(e.target.value)} /></label>
                    <label className="lbl">New PIN<input type="password" value={newPin} onChange={(e) => setNewPin(e.target.value)} /></label>
                    <button className="btn" onClick={() => api.changePin(token, oldPin, newPin).then(() => { localStorage.setItem('paykotha_pin', newPin); setSessionPin(newPin); show('ok', 'PIN updated') }).catch((e) => show('err', e.message))}>Update PIN</button>

                    <h3 style={{ margin: '1.1rem 0 0.45rem', fontSize: '0.95rem' }}>Favorites</h3>
                    {favs.map((f) => (
                      <div className="card" key={f.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                        <div>
                          <h4 style={{ margin: 0 }}>{f.label}</h4>
                          <div className="muted" style={{ fontSize: '0.82rem' }}>{f.phone}</div>
                        </div>
                        <button type="button" className="chip" onClick={() => api.deleteFavorite(token, f.id).then(() => refresh()).then(() => show('ok', 'Removed'))}>Remove</button>
                      </div>
                    ))}
                    <label className="lbl">Label<input value={favLabel} onChange={(e) => setFavLabel(e.target.value)} placeholder="Bob" /></label>
                    <label className="lbl">Mobile<input value={favPhone} onChange={(e) => setFavPhone(e.target.value)} inputMode="tel" placeholder="01XXXXXXXXX" /></label>
                    <button className="btn soft" onClick={() => {
                      if (!favLabel.trim() || !favPhone.trim()) return show('err', 'Enter label and mobile')
                      api.addFavorite(token, favLabel, favPhone).then(() => refresh()).then(() => { setFavLabel(''); setFavPhone(''); show('ok', 'Favorite saved') }).catch((e) => show('err', e.message))
                    }}>Add favorite</button>

                    <button className="btn ghost" style={{ marginTop: '0.55rem' }} onClick={() => openFlow('ops')}>Ops Desk</button>
                  </>
                )}

                {flow === 'ops' && (
                  user.is_admin ? (
                    <>
                      <button className="btn ghost" onClick={() => api.adminStats(token).then((s) => setOpsMsg(`Users ${s.users} · Txns ${s.transactions}`))}>Platform stats</button>
                      <button className="btn ghost" style={{ marginTop: '0.45rem' }} onClick={() => api.adminReconcile(token).then((r) => setOpsMsg(JSON.stringify(r)))}>Reconcile</button>
                      <button className="btn teal" style={{ marginTop: '0.45rem' }} onClick={() => api.adminSettlement(token).then((s) => setOpsMsg(`${s.id} · ${money(s.net_amount)}`))}>Run EOD settlement</button>
                      <button className="btn ghost" style={{ marginTop: '0.45rem' }} onClick={() => api.adminListSettlements(token).then((rows) => setOpsMsg(rows.slice(0, 3).map((s) => `${s.id} ${s.status}`).join(' · ') || 'No settlements'))}>List settlements</button>
                      <button className="btn ghost" style={{ marginTop: '0.45rem' }} onClick={() => api.adminAudit(token).then((rows) => setOpsMsg(rows.slice(0, 5).map((a) => a.action).join(' · ') || 'No audit'))}>Audit trail</button>
                      <button className="btn ghost" style={{ marginTop: '0.45rem' }} onClick={() => api.adminReversals(token).then(setOpsReversals).then(() => show('ok', 'Reversals loaded'))}>Load reversals</button>
                      <label className="lbl" style={{ marginTop: '0.85rem' }}>Txn ID<input value={revTxnId} onChange={(e) => setRevTxnId(e.target.value)} /></label>
                      <label className="lbl">Reason<input value={revReason} onChange={(e) => setRevReason(e.target.value)} /></label>
                      <button className="btn" onClick={() => api.adminCreateReversal(token, revTxnId, revReason).then((r) => { setOpsMsg(r.id); return api.adminReversals(token).then(setOpsReversals) }).catch((e) => show('err', e.message))}>Request reversal</button>
                      {opsReversals.map((r) => (
                        <div className="card" key={r.id} style={{ marginTop: '0.55rem' }}>
                          <h4>{r.id}</h4>
                          <div className="muted" style={{ fontSize: '0.82rem' }}>{r.transaction_id} · {r.status} · {r.reason}</div>
                          {r.status === 'PENDING' && (
                            <div className="chips" style={{ marginTop: '0.45rem' }}>
                              <button type="button" className="chip on" onClick={() => api.adminDecideReversal(token, r.id, true).then(() => api.adminReversals(token).then(setOpsReversals)).then(() => show('ok', 'Approved')).catch((e) => show('err', e.message))}>Approve</button>
                              <button type="button" className="chip" onClick={() => api.adminDecideReversal(token, r.id, false).then(() => api.adminReversals(token).then(setOpsReversals)).then(() => show('ok', 'Rejected')).catch((e) => show('err', e.message))}>Reject</button>
                            </div>
                          )}
                        </div>
                      ))}
                      {opsMsg && <p className="hint">{opsMsg}</p>}
                    </>
                  ) : <p className="empty">Admin only<br />01999999991 / 111111</p>
                )}

                {flow === 'request' && step === 'details' && requests.slice(0, 4).map((r) => (
                  <div className="card" key={r.id} style={{ marginTop: '0.55rem' }}>
                    <h4>{r.id}</h4>
                    <div className="muted">{r.payer_phone} · {money(r.amount)} · {r.status}</div>
                    {r.status === 'PENDING' && r.payer_phone === user.phone && (
                      <button className="btn soft" style={{ marginTop: '0.45rem' }} onClick={() => api.payRequest(token, r.id).then(() => refresh()).then(() => show('ok', 'Paid'))}>Pay now</button>
                    )}
                    {r.status === 'PENDING' && r.requester_id === user.id && (
                      <button className="btn ghost" style={{ marginTop: '0.45rem' }} onClick={() => api.cancelRequest(token, r.id).then(() => refresh()).then(() => show('ok', 'Cancelled'))}>Cancel</button>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : nav === 'home' ? (
            <div ref={homeAnim}>
              <header className="banner">
                <div className="banner-row">
                  <div>
                    <div className="brand">PayKotha</div>
                    <div className="sub">{user.name}</div>
                  </div>
                  <button type="button" className="icon-round" onClick={() => setNav('inbox')} aria-label="Notifications">
                    <IconBell />
                    {unread > 0 && <span className="badge">{unread}</span>}
                  </button>
                </div>
                <div className="bal">
                  <div className="cap">
                    Available Balance
                    <button type="button" className="eye" onClick={() => setHiddenBal((v) => !v)}>
                      <IconEye /> {hiddenBal ? 'Show' : 'Hide'}
                    </button>
                  </div>
                  <p className="amt" ref={balanceRef}>{hiddenBal ? '৳••••••' : money(user.balance)}</p>
                  <div className="meta">Savings {money(user.savings_balance)} · KYC {user.kyc_level}</div>
                  <div className="limit-mini">
                    <div className="limit-head">
                      <span>Today</span>
                      <b>{money(todaySpend)} / {money(user.daily_limit)}</b>
                    </div>
                    <div className="limit-track light" aria-hidden><i style={{ width: `${dailyPct}%` }} /></div>
                  </div>
                </div>
              </header>

              {pendingReqs.some((r) => r.payer_phone === user.phone) && (
                <button type="button" className="action-banner" onClick={() => setNav('inbox')}>
                  <b>Money request waiting</b>
                  <span>Tap to pay or review in Inbox</span>
                </button>
              )}

              <div className="quick">
                {QUICK.map((q) => (
                  <button key={q.id!} type="button" onClick={() => openFlow(q.id)}>
                    <span className="ic" style={{ background: q.color }}>{q.icon}</span>
                    <span>{q.label}</span>
                  </button>
                ))}
              </div>

              <div className="promo">
                <b>{BRAND.promoTitle}</b>
                <span>{BRAND.promoBody}</span>
              </div>

              <section className="block">
                <h3>Services</h3>
                <div className="services">
                  {SERVICES.map((s) => (
                    <button key={s.id!} type="button" className="svc" onClick={() => openFlow(s.id)}>
                      <span className="ic" style={{ background: s.soft, color: s.color }}>{s.icon}</span>
                      <em>{s.label}</em>
                    </button>
                  ))}
                </div>
              </section>

              <section className="block">
                <div className="page-head" style={{ marginBottom: '0.45rem' }}>
                  <h3 style={{ margin: 0 }}>Recent</h3>
                  <button type="button" className="chip" onClick={() => setNav('history')}>See all</button>
                </div>
                <div className="list">
                  {txns.slice(0, 5).map((t) => {
                    const isOut = isOutflow(t, user.id)
                    return (
                      <div className="row-item" key={t.id}>
                        <div className="left">
                          <div className={`av ${isOut ? 'out' : 'in'}`}>{t.txn_type.slice(0, 2)}</div>
                          <div>
                            <strong>{t.txn_type.replaceAll('_', ' ')}</strong>
                            <small>{t.note || t.id}</small>
                          </div>
                        </div>
                        <div className={`money ${isOut ? 'out' : 'in'}`}>
                          {isOut ? '−' : '+'}{money(t.amount)}
                        </div>
                      </div>
                    )
                  })}
                  {!txns.length && <div className="empty">No transactions yet</div>}
                </div>
              </section>
            </div>
          ) : nav === 'history' ? (
            <HistoryPage
              userId={user.id}
              txns={txns}
              onExport={() => api.exportExcel(token).then((r) => show('ok', r.message)).catch((e) => show('err', e.message))}
            />
          ) : nav === 'scan' ? (
            <ScanPage
              user={user}
              merchant={merchant}
              setMerchant={setMerchant}
              setAmountStr={setAmountStr}
              txns={txns}
              onPay={() => openFlow('merchant')}
              onFlash={show}
            />
          ) : nav === 'inbox' ? (
            <InboxPage
              token={token}
              userPhone={user.phone}
              userId={user.id}
              requests={requests}
              notifs={notifs}
              onRefresh={refresh}
              onFlash={show}
              onRequestMoney={() => openFlow('request')}
            />
          ) : (
            <MePage
              token={token}
              user={user}
              txns={txns}
              favs={favs}
              liveConnected={live.connected}
              unread={unread}
              pendingRequests={pendingReqs.length}
              onRefresh={refresh}
              onFlash={show}
              onOpenFlow={(id) => openFlow(id)}
              onNav={setNav}
              onLogout={logout}
              oldPin={oldPin}
              newPin={newPin}
              setOldPin={setOldPin}
              setNewPin={setNewPin}
              setSessionPin={setSessionPin}
              favLabel={favLabel}
              favPhone={favPhone}
              setFavLabel={setFavLabel}
              setFavPhone={setFavPhone}
            />
          )}
        </div>

        {!flow && (
          <nav className="tabbar">
            <button type="button" className={nav === 'home' ? 'on' : ''} onClick={() => setNav('home')}><IconHome /><span>Home</span></button>
            <button type="button" className={nav === 'history' ? 'on' : ''} onClick={() => setNav('history')}><IconHistory /><span>History</span></button>
            <button type="button" className={nav === 'scan' ? 'on' : ''} onClick={() => setNav('scan')}><span className="scan-fab"><IconQr size={22} /></span></button>
            <button type="button" className={nav === 'inbox' ? 'on' : ''} onClick={() => setNav('inbox')}><IconInbox /><span>Inbox</span></button>
            <button type="button" className={nav === 'me' ? 'on' : ''} onClick={() => setNav('me')}><IconUser size={20} /><span>Me</span></button>
          </nav>
        )}

        {flash && <div ref={toastRef} className={`toast ${flash.type === 'ok' ? 'ok' : 'err'}`}>{flash.text}</div>}
      </div>
    </div>
  )
}
