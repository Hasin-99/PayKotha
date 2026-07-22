import { useEffect, useRef, useState } from 'react'
import type { Dispatch, RefObject, SetStateAction } from 'react'
import { api } from '../api'
import type { MoneyReq, Notif, Txn, User } from '../api'
import { animateBalance, pulseSuccess } from '../motion'

export type LiveState = {
  connected: boolean
  lastEventAt: string | null
  unread: number
  latestToast: string | null
}

function mergeRecent(prev: Txn[], recent: Txn[]): Txn[] {
  if (!recent.length) return prev
  const map = new Map<string, Txn>()
  for (const t of recent) if (t.id) map.set(t.id, t)
  for (const t of prev) if (t.id && !map.has(t.id)) map.set(t.id, t)
  return Array.from(map.values()).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
}

export function useLiveWallet(
  token: string | null,
  user: User | null,
  setUser: (u: User | null) => void,
  setTxns: Dispatch<SetStateAction<Txn[]>>,
  setNotifs: (n: Notif[]) => void,
  balanceRef: RefObject<HTMLElement | null>,
  setRequests?: Dispatch<SetStateAction<MoneyReq[]>>,
) {
  const [live, setLive] = useState<LiveState>({
    connected: false,
    lastEventAt: null,
    unread: 0,
    latestToast: null,
  })
  const prevBal = useRef(user?.balance ?? 0)
  const userRef = useRef(user)
  userRef.current = user

  useEffect(() => {
    if (!token) return
    let es: EventSource | null = null
    let pollTimer: ReturnType<typeof setInterval> | null = null
    let closed = false

    const applyBalance = (balance: number, savings: number) => {
      const current = userRef.current
      if (!current) return
      const el = balanceRef.current
      if (el && balance !== prevBal.current) {
        animateBalance(el, prevBal.current, balance)
        pulseSuccess(el)
      }
      prevBal.current = balance
      setUser({ ...current, balance, savings_balance: savings })
    }

    const refreshSide = () => {
      api.notifications(token).then(setNotifs).catch(() => undefined)
      api.me(token).then((me) => applyBalance(me.balance, me.savings_balance)).catch(() => undefined)
      api.history(token).then((h) => setTxns(h)).catch(() => undefined)
      if (setRequests) api.listRequests(token).then(setRequests).catch(() => undefined)
    }

    const onWallet = (raw: string) => {
      try {
        const data = JSON.parse(raw)
        setLive((s) => ({
          ...s,
          connected: true,
          lastEventAt: data.server_time,
          unread: data.unread_notifications ?? 0,
        }))
        applyBalance(data.balance, data.savings_balance)
        if (Array.isArray(data.recent)) {
          const mapped: Txn[] = data.recent.map((t: Partial<Txn>) => ({
            id: t.id || '',
            sender_id: t.sender_id || '',
            receiver_id: t.receiver_id || '',
            amount: t.amount || 0,
            fee: t.fee || 0,
            txn_type: t.txn_type || '',
            status: t.status || 'SUCCESS',
            note: t.note || '',
            meta: t.meta || '',
            created_at: t.created_at || new Date().toISOString(),
          }))
          setTxns((prev) => mergeRecent(prev, mapped))
        }
      } catch {
        /* ignore */
      }
    }

    const startPollFallback = () => {
      if (pollTimer || closed) return
      pollTimer = setInterval(() => {
        api.liveSnapshot(token)
          .then((snap) => {
            setLive((s) => ({
              ...s,
              connected: true,
              lastEventAt: snap.server_time,
              unread: snap.unread_notifications ?? 0,
            }))
            applyBalance(snap.user.balance, snap.user.savings_balance)
            if (Array.isArray(snap.recent)) setTxns((prev) => mergeRecent(prev, snap.recent))
            if (setRequests) api.listRequests(token).then(setRequests).catch(() => undefined)
          })
          .catch(() => setLive((s) => ({ ...s, connected: false })))
      }, 4000)
    }

    const connect = () => {
      if (closed) return
      es = api.openLiveStream(token)
      setLive((s) => ({ ...s, connected: true }))

      es.addEventListener('wallet', (ev) => onWallet((ev as MessageEvent).data))

      es.addEventListener('ping', (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data)
          setLive((s) => ({
            ...s,
            connected: true,
            latestToast: data.type ? `${data.type}${data.amount ? ` · ৳${data.amount}` : ''}` : s.latestToast,
          }))
          refreshSide()
        } catch {
          /* ignore */
        }
      })

      es.onerror = () => {
        setLive((s) => ({ ...s, connected: false }))
        es?.close()
        es = null
        startPollFallback()
      }
    }

    connect()

    return () => {
      closed = true
      es?.close()
      if (pollTimer) clearInterval(pollTimer)
      setLive((s) => ({ ...s, connected: false }))
    }
  }, [token, balanceRef, setUser, setTxns, setNotifs, setRequests])

  useEffect(() => {
    if (user) prevBal.current = user.balance
  }, [user?.id])

  return live
}
