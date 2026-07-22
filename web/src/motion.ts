import { animate, createTimeline, stagger, utils } from 'animejs'

export function playAuthEntrance(root: HTMLElement) {
  const brand = root.querySelectorAll('.auth-brand, .auth-copy, .auth-panel')
  createTimeline({ defaults: { ease: 'outExpo' } })
    .add(brand, {
      opacity: [0, 1],
      translateY: [36, 0],
      rotateX: [18, 0],
      duration: 900,
      delay: stagger(120),
    })
    .add(
      root.querySelectorAll('.orb'),
      {
        scale: [0.6, 1],
        opacity: [0, 1],
        duration: 1200,
        delay: stagger(80),
      },
      '-=700',
    )
}

export function playWalletEntrance(root: HTMLElement) {
  const wallet = root.querySelector('.wallet-3d')
  const tiles = root.querySelectorAll('.nav-tile')
  const workbench = root.querySelector('.workbench')
  const tl = createTimeline({ defaults: { ease: 'outCubic' } })
  if (wallet) {
    tl.add(wallet, {
      opacity: [0, 1],
      translateY: [48, 0],
      rotateX: [24, 12],
      duration: 1000,
    })
  }
  if (tiles.length) {
    tl.add(
      tiles,
      {
        opacity: [0, 1],
        translateY: [28, 0],
        rotateX: [12, 0],
        duration: 650,
        delay: stagger(35),
      },
      '-=550',
    )
  }
  if (workbench) {
    tl.add(
      workbench,
      {
        opacity: [0, 1],
        translateY: [24, 0],
        duration: 700,
      },
      '-=400',
    )
  }
}

export function tiltWalletCard(card: HTMLElement, clientX: number, clientY: number) {
  const rect = card.getBoundingClientRect()
  const px = (clientX - rect.left) / rect.width - 0.5
  const py = (clientY - rect.top) / rect.height - 0.5
  animate(card, {
    rotateY: px * 18,
    rotateX: 12 - py * 14,
    duration: 450,
    ease: 'outQuad',
    composition: 'blend',
  })
}

export function resetWalletTilt(card: HTMLElement) {
  animate(card, {
    rotateY: 0,
    rotateX: 12,
    duration: 700,
    ease: 'outElastic(1, 0.6)',
  })
}

export function pulseSuccess(el: HTMLElement) {
  animate(el, {
    scale: [1, 1.03, 1],
    duration: 520,
    ease: 'outBack(1.6)',
  })
}

export function shakeError(el: HTMLElement) {
  animate(el, {
    translateX: [0, -10, 10, -6, 6, 0],
    duration: 480,
    ease: 'outQuad',
  })
}

export function animateBalance(el: HTMLElement, from: number, to: number) {
  const obj = { n: from }
  animate(obj, {
    n: to,
    duration: 900,
    ease: 'outExpo',
    onUpdate: () => {
      el.textContent = `৳${Number(obj.n).toLocaleString('en-BD', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`
    },
  })
}

export function floatOrbs(root: HTMLElement) {
  const orbs = root.querySelectorAll('.orb')
  orbs.forEach((orb, i) => {
    animate(orb, {
      translateY: utils.random(-18, 18),
      translateX: utils.random(-14, 14),
      duration: utils.random(2800, 4600),
      delay: i * 200,
      loop: true,
      alternate: true,
      ease: 'inOutSine',
    })
  })
}

export function tabPanelSwap(el: HTMLElement) {
  animate(el, {
    opacity: [0, 1],
    translateY: [16, 0],
    rotateX: [8, 0],
    duration: 420,
    ease: 'outCubic',
  })
}
