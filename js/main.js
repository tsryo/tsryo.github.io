// Progressive extras. The page works fully without this file.

// Visitors who ask to save data get a still page (see .lite in style.css).
if (navigator.connection && navigator.connection.saveData) document.documentElement.classList.add('lite');

// Per-language strings, written into the page by tools/build.py.
const STRINGS = (() => {
  try { return JSON.parse(document.getElementById('strings').textContent); } catch { return {}; }
})();
const t = (key, fallback) => STRINGS[key] || fallback;

// One level for every year since the first PC, in 2001.
document.querySelectorAll('[data-level]').forEach((el) => {
  el.textContent = new Date().getFullYear() - 2001;
});

// Mark the nav link of the section in view.
const links = new Map(
  [...document.querySelectorAll('.topbar nav a[href^="#"]')].map((a) => [a.hash.slice(1), a])
);

if ('IntersectionObserver' in window && links.size) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      links.forEach((a) => a.removeAttribute('aria-current'));
      links.get(entry.target.id)?.setAttribute('aria-current', 'true');
    }
  }, { rootMargin: '-45% 0px -50% 0px' });
  links.forEach((_, id) => {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  });
}

// The road so far: pointing at a stop lights its pin on the map, and the other way round.
const stops = document.querySelectorAll('.stops li[data-stop], .pin[data-stop]');
stops.forEach((el) => {
  const light = (on) => document.querySelectorAll(`[data-stop="${el.dataset.stop}"]`).forEach((m) => m.classList.toggle('is-lit', on));
  el.addEventListener('mouseenter', () => light(true));
  el.addEventListener('mouseleave', () => light(false));
});

// Sections below the hero skip rendering at first (content-visibility in style.css), which brings the
// first paint forward. Lay them out once the page has loaded and painted, so that in-page links land
// where they should; following one sooner lays them out on the spot.
const unlaid = [...document.querySelectorAll('.section > .wrap')];
const layOutAll = () => unlaid.splice(0).forEach((wrap) => { wrap.style.contentVisibility = 'visible'; });
const whenIdle = window.requestIdleCallback || ((fn) => setTimeout(fn, 100));
addEventListener('load', () => requestAnimationFrame(() => setTimeout(() => whenIdle(layOutAll))), { once: true });
document.addEventListener('click', (event) => {
  if (event.target.closest('a[href^="#"]')) layOutAll();
}, true);
// Arriving at a section from elsewhere (the explainer links back to /#story): lay out now and land exactly.
const linked = location.hash && document.getElementById(location.hash.slice(1));
if (linked) {
  layOutAll();
  document.documentElement.style.scrollBehavior = 'auto';
  linked.scrollIntoView();
  document.documentElement.style.scrollBehavior = '';
}

// Rest what's out of sight: SVG animations (SMIL) in offscreen drawings, and CSS animations in the hero
// and in each section while scrolled away (the XP bars fill when their section comes into view).
if ('IntersectionObserver' in window) {
  const resting = new IntersectionObserver((entries) => {
    for (const { target, isIntersecting } of entries) {
      if (target instanceof SVGSVGElement) {
        if (isIntersecting) target.unpauseAnimations(); else target.pauseAnimations();
      } else {
        target.classList.toggle('is-resting', !isIntersecting);
      }
    }
  }, { rootMargin: '120px' });
  document.querySelectorAll('svg').forEach((svg) => {
    if (svg.querySelector('animate, animateMotion, animateTransform')) resting.observe(svg);
  });
  document.querySelectorAll('.hero, .section').forEach((part) => resting.observe(part));
}

// SMIL ignores CSS, so stop SVG animations (map traveller, flag, windmill) by hand when motion is reduced.
if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.querySelectorAll('svg animate, svg animateMotion, svg animateTransform').forEach((a) => a.remove());
  document.querySelectorAll('.traveller').forEach((t) => t.remove());
}

// SoundCloud player: loaded only on request, so the page stays tracker-free until then.
const scButton = document.getElementById('sc-load');
const scPlayer = document.getElementById('sc-player');
if (scButton && scPlayer) {
  scButton.addEventListener('click', () => {
    const src = 'https://w.soundcloud.com/player/?url=' + encodeURIComponent('https://soundcloud.com/trycep') +
      '&color=%23ff7a1a&auto_play=true&hide_related=true&show_comments=false&show_reposts=false&visual=false';
    const frame = document.createElement('iframe');
    frame.title = t('sc_title', 'CQ on SoundCloud');
    frame.allow = 'autoplay';
    // Third-party player: sandboxed, and told only our origin.
    frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.src = src;
    scPlayer.replaceChildren(frame);
    scPlayer.hidden = false;
    scButton.disabled = true;
    // Don't play two tunes at once.
    document.dispatchEvent(new CustomEvent('tseko:external-audio'));
  });
}

// Konami code: up up down down left right left right B A.
const code = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
const toast = document.getElementById('toast');
let pos = 0;
let toastTimer;

function say(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

document.addEventListener('keydown', (event) => {
  const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
  if (key === code[pos]) {
    pos += 1;
  } else if (key === 'ArrowUp') {
    // A third ArrowUp still leaves the last two as a valid start.
    pos = pos === 2 ? 2 : 1;
  } else {
    pos = 0;
  }
  if (pos === code.length) {
    pos = 0;
    const on = document.documentElement.classList.toggle('turbo');
    say(on ? t('cheat_on', 'Cheat code accepted. +1000 XP. Some habits never die.') : t('cheat_off', 'Cheat mode off. Back to honest grinding.'));
  }
});
