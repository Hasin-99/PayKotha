const API = import.meta.env.VITE_API_URL ?? '/api/v1'

export type User = {
  id: string
  name: string
  phone: string
  balance: number
  savings_balance: number
  daily_limit: number
  bank_account: string
  is_active: boolean
  is_admin?: boolean
  kyc_level?: string
  created_at: string
}

export type Txn = {
  id: string
  sender_id: string
  receiver_id: string
  amount: number
  fee: number
  txn_type: string
  status: string
  note: string
  meta?: string
  rail_ref?: string
  created_at: string
}

export type MoneyReq = {
  id: string
  requester_id: string
  payer_phone: string
  amount: number
  note: string
  status: string
  created_at: string
}

export type Notif = {
  id: number
  title: string
  body: string
  is_read: boolean
  created_at: string
}

export type Favorite = { id: number; label: string; phone: string; kind: string }

export type OtpChallenge = {
  challenge_id: string
  expires_in: number
  purpose: string
  delivery: string
  sandbox_code?: string
}

export type Reversal = {
  id: string
  transaction_id: string
  maker_id: string
  checker_id?: string | null
  reason: string
  status: string
  created_at: string
}

export type Settlement = {
  id: string
  status: string
  txn_count: number
  gross_amount: number
  fee_amount: number
  net_amount: number
  rail_ref: string
  created_at: string
}

function authHeaders(token?: string | null): HeadersInit {
  const h: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) h.Authorization = `Bearer ${token}`
  return h
}

function detailMessage(data: { detail?: unknown; message?: string }): string {
  const detail = data.detail
  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(', ')
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && 'message' in (detail as object)) {
    return String((detail as { message: string }).message)
  }
  return data.message || 'Request failed'
}

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { ...authHeaders(token), ...(options.headers || {}) },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(detailMessage(data)) as Error & { status?: number; detail?: unknown }
    err.status = res.status
    err.detail = data.detail
    throw err
  }
  return data as T
}

const idemp = () => crypto.randomUUID()

type OtpFields = { otp_challenge_id?: string; otp_code?: string }

export const api = {
  catalog: () =>
    request<{
      operators: string[]
      billers: Record<string, string>
      features: string[]
      require_otp_above?: number
      rail_mode?: string
    }>('/catalog'),
  register: (body: { name: string; phone: string; pin: string; opening_balance: number; nid_number?: string }) =>
    request<User>('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
  login: (body: { phone: string; pin: string }) =>
    request<{ access_token: string; refresh_token?: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  refresh: (refresh_token: string) =>
    request<{ access_token: string; refresh_token?: string }>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
    }),
  issueOtp: (token: string, purpose: string) =>
    request<OtpChallenge>('/auth/otp/issue', { method: 'POST', body: JSON.stringify({ purpose }) }, token),
  changePin: (token: string, old_pin: string, new_pin: string) =>
    request<User>('/auth/change-pin', { method: 'POST', body: JSON.stringify({ old_pin, new_pin }) }, token),
  upgradeKyc: (token: string, level: string, nid_number = '') =>
    request<User>('/kyc/upgrade', { method: 'POST', body: JSON.stringify({ level, nid_number }) }, token),
  me: (token: string) => request<User>('/me', {}, token),
  cashIn: (token: string, amount: number, note = '') =>
    request<Txn>('/wallet/cash-in', { method: 'POST', body: JSON.stringify({ amount, note, idempotency_key: idemp() }) }, token),
  cashOut: (token: string, amount: number, note = '', otp?: OtpFields) =>
    request<Txn>(
      '/wallet/cash-out',
      { method: 'POST', body: JSON.stringify({ amount, note, idempotency_key: idemp(), ...otp }) },
      token,
    ),
  send: (token: string, receiver_phone: string, amount: number, note = '', otp?: OtpFields) =>
    request<Txn>(
      '/wallet/send',
      {
        method: 'POST',
        body: JSON.stringify({ receiver_phone, amount, note, idempotency_key: idemp(), ...otp }),
      },
      token,
    ),
  recharge: (token: string, operator: string, mobile: string, amount: number) =>
    request<Txn>('/wallet/recharge', { method: 'POST', body: JSON.stringify({ operator, mobile, amount, idempotency_key: idemp() }) }, token),
  billPay: (token: string, biller_code: string, account_no: string, amount: number) =>
    request<Txn>('/wallet/bill-pay', { method: 'POST', body: JSON.stringify({ biller_code, account_no, amount, idempotency_key: idemp() }) }, token),
  merchantPay: (token: string, merchant_code: string, amount: number, note = '') =>
    request<Txn>('/wallet/merchant-pay', { method: 'POST', body: JSON.stringify({ merchant_code, amount, note, idempotency_key: idemp() }) }, token),
  bankTransfer: (token: string, bank_account: string, amount: number, otp?: OtpFields) =>
    request<Txn>(
      '/wallet/bank-transfer',
      { method: 'POST', body: JSON.stringify({ bank_account, amount, idempotency_key: idemp(), ...otp }) },
      token,
    ),
  addMoney: (token: string, amount: number, bank_account = '') =>
    request<Txn>('/wallet/add-money', { method: 'POST', body: JSON.stringify({ amount, bank_account, idempotency_key: idemp() }) }, token),
  donate: (token: string, cause: string, amount: number) =>
    request<Txn>('/wallet/donate', { method: 'POST', body: JSON.stringify({ cause, amount, idempotency_key: idemp() }) }, token),
  savingsIn: (token: string, amount: number) =>
    request<Txn>('/wallet/savings/deposit', { method: 'POST', body: JSON.stringify({ amount, idempotency_key: idemp() }) }, token),
  savingsOut: (token: string, amount: number) =>
    request<Txn>('/wallet/savings/withdraw', { method: 'POST', body: JSON.stringify({ amount, idempotency_key: idemp() }) }, token),
  history: (token: string) => request<Txn[]>('/wallet/transactions', {}, token),
  createRequest: (token: string, payer_phone: string, amount: number, note = '') =>
    request<MoneyReq>('/requests', { method: 'POST', body: JSON.stringify({ payer_phone, amount, note }) }, token),
  listRequests: (token: string) => request<MoneyReq[]>('/requests', {}, token),
  payRequest: (token: string, id: string) => request<Txn>(`/requests/${id}/pay`, { method: 'POST' }, token),
  cancelRequest: (token: string, id: string) => request<MoneyReq>(`/requests/${id}/cancel`, { method: 'POST' }, token),
  favorites: (token: string) => request<Favorite[]>('/favorites', {}, token),
  addFavorite: (token: string, label: string, phone: string, kind = 'CONTACT') =>
    request<Favorite>('/favorites', { method: 'POST', body: JSON.stringify({ label, phone, kind }) }, token),
  deleteFavorite: (token: string, id: number) =>
    request<{ ok: boolean }>(`/favorites/${id}`, { method: 'DELETE' }, token),
  notifications: (token: string) => request<Notif[]>('/notifications', {}, token),
  readNotifications: (token: string) => request<{ marked: number }>('/notifications/read', { method: 'POST' }, token),
  liveSnapshot: (token: string) =>
    request<{
      server_time: string
      live: boolean
      user: User
      unread_notifications: number
      pending_requests: number
      recent: Txn[]
    }>('/live/snapshot', {}, token),
  exportExcel: (token: string) => request<{ message: string; paths: Record<string, string> }>('/admin/export-excel', { method: 'POST' }, token),
  adminStats: (token: string) => request<{ users: number; transactions: number; total_volume: number }>('/admin/stats', {}, token),
  adminReconcile: (token: string) => request<Record<string, unknown>>('/admin/reconcile', {}, token),
  adminSettlement: (token: string) => request<Settlement>('/admin/settlement/eod', { method: 'POST' }, token),
  adminListSettlements: (token: string) => request<Settlement[]>('/admin/settlement', {}, token),
  adminReversals: (token: string) => request<Reversal[]>('/admin/reversals', {}, token),
  adminCreateReversal: (token: string, transaction_id: string, reason: string) =>
    request<Reversal>('/admin/reversals', { method: 'POST', body: JSON.stringify({ transaction_id, reason }) }, token),
  adminDecideReversal: (token: string, id: string, approve: boolean) =>
    request<Reversal>(`/admin/reversals/${id}/decide`, { method: 'POST', body: JSON.stringify({ approve }) }, token),
  adminAudit: (token: string) =>
    request<{ id: number; actor_id: string; action: string; entity_id: string; detail: string; created_at: string }[]>(
      '/admin/audit',
      {},
      token,
    ),
  openLiveStream: (token: string) => {
    const base = API.startsWith('http') ? API : `${window.location.origin}${API}`
    return new EventSource(`${base}/live/stream?token=${encodeURIComponent(token)}`)
  },
}
