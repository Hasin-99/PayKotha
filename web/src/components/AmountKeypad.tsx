type Props = {
  value: string
  onChange: (v: string) => void
  onDone?: () => void
}

/** Numeric amount pad — industry MFS pattern */
export function AmountKeypad({ value, onChange, onDone }: Props) {
  function press(key: string) {
    if (key === '⌫') {
      onChange(value.slice(0, -1) || '0')
      return
    }
    if (key === '.') {
      if (value.includes('.')) return
      onChange(value === '0' ? '0.' : `${value}.`)
      return
    }
    if (value === '0') {
      onChange(key)
      return
    }
    const next = `${value}${key}`
    const [a, b] = next.split('.')
    if (b && b.length > 2) return
    if (a.length > 7) return
    onChange(next)
  }

  const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '⌫']

  return (
    <div className="keypad">
      {keys.map((k) => (
        <button key={k} type="button" className="key" onClick={() => press(k)}>
          {k}
        </button>
      ))}
      {onDone && (
        <button type="button" className="key key-done" onClick={onDone}>
          Next
        </button>
      )}
    </div>
  )
}
