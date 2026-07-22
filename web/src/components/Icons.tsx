/** Compact SVG icons — MFS-style circular service glyphs */
type IconProps = { size?: number; className?: string }

export function IconSend({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 12h12M12 6l6 6-6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
export function IconCashIn({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 4v12M7 11l5 5 5-5M5 20h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
export function IconCashOut({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 20V8M7 13l5-5 5 5M5 4h14" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
export function IconQr({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 4h7v7H4V4zm9 0h7v7h-7V4zM4 13h7v7H4v-7zm11 2h2v2h-2v-2zm-2-2h2v2h-2v-2zm4 4h2v2h-2v-2zm-2 2h2v2h-2v-2z" fill="currentColor" />
    </svg>
  )
}
export function IconPhone({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="7" y="2" width="10" height="20" rx="2.5" stroke="currentColor" strokeWidth="2" />
      <path d="M11 18h2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
export function IconBill({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 3h10v18l-2-1.5L13 21l-2-1.5L9 21l-2-1.5V3z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M10 8h4M10 12h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
export function IconBank({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 10h16M6 10v8M10 10v8M14 10v8M18 10v8M3 18h18M12 4l9 6H3l9-6z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
export function IconAdd({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8v8M8 12h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
export function IconRequest({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M7 10V6a2 2 0 012-2h9a2 2 0 012 2v8a2 2 0 01-2 2h-3" stroke="currentColor" strokeWidth="2" />
      <path d="M4 10h10a1 1 0 011 1v7H5a1 1 0 01-1-1v-7z" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}
export function IconSavings({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 3c4 0 7 2.5 7 6.5S16 17 12 21C8 17 5 13.5 5 9.5S8 3 12 3z" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="10" r="2.2" fill="currentColor" />
    </svg>
  )
}
export function IconHeart({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M12 20s-7-4.4-7-10a4 4 0 017-2.6A4 4 0 0119 10c0 5.6-7 10-7 10z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
export function IconUser({ size = 22 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="2" />
      <path d="M5 19c1.5-3 4-4.5 7-4.5S17.5 16 19 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
export function IconHome({ size = 20 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 11l8-7 8 7v9a1 1 0 01-1 1h-5v-6H10v6H5a1 1 0 01-1-1v-9z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
export function IconHistory({ size = 20 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8v5l3 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
export function IconInbox({ size = 20 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 7l8 6 8-6M5 19h14a1 1 0 001-1V6a1 1 0 00-1-1H5a1 1 0 00-1 1v12a1 1 0 001 1z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
export function IconBell({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M6 16h12l-1.2-2V10a4.8 4.8 0 00-9.6 0v4L6 16zM10 18a2 2 0 004 0" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}
export function IconEye({ size = 14 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" stroke="currentColor" strokeWidth="2" />
      <circle cx="12" cy="12" r="2.5" fill="currentColor" />
    </svg>
  )
}
export function IconCheck({ size = 40 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.15" />
      <path d="M7 12.5l3.2 3.2L17 8.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
export function IconBack({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M15 6l-6 6 6 6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
