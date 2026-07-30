import type { Transition, Variants } from "framer-motion";

/**
 * Shared animation tokens. Keep durations short for micro-interactions
 * (hover, badge changes, list item enter/exit) and slightly longer for
 * page-level/panel-level transitions, so motion reads as one coherent
 * system rather than a grab-bag of per-component tuning.
 *
 * `prefers-reduced-motion` is already respected globally for CSS
 * transitions/animations (see globals.css). Framer Motion doesn't pick
 * that media query up automatically, so components using these tokens
 * should read `useReducedMotion()` from `framer-motion` and fall back to
 * the `reduced` variants below when it's true.
 */
export const DURATION = {
  fast: 0.15,
  base: 0.25,
  slow: 0.4,
} as const;

export const EASE = {
  standard: [0.4, 0, 0.2, 1] as const,
  decelerate: [0, 0, 0.2, 1] as const,
  accelerate: [0.4, 0, 1, 1] as const,
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.base, ease: EASE.decelerate },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: DURATION.base, ease: EASE.standard } },
};

export const staggerChildren = (stagger = 0.05): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren: stagger },
  },
});

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: DURATION.fast, ease: EASE.decelerate },
  },
};

export const listItemTransition: Transition = {
  duration: DURATION.fast,
  ease: EASE.standard,
};

/** Motion variants collapse to an instant, no-motion state — used when useReducedMotion() is true. */
export const reducedMotionVariants: Variants = {
  hidden: { opacity: 1 },
  visible: { opacity: 1 },
};