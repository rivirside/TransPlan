/**
 * Vercel Analytics queue stub (#250).
 *
 * This exact 90-byte snippet was inline on 15 pages. Inline script blocks
 * force `script-src 'unsafe-inline'` in any Content-Security-Policy, which
 * removes most of what a CSP is for — so the 15 copies were, between them,
 * one of the two things blocking a useful policy.
 *
 * It queues analytics calls made before the real Vercel script loads, so it
 * must still run BEFORE `/_vercel/insights/script.js`. Position, not just
 * presence, is what makes it work.
 */
window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
