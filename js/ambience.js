// Optional background ambience, off until the visitor turns it on.
// Original, generative music synthesised live with the Web Audio API; no
// recordings are used. The flavour follows the page language:
//   es  Lut Gholein / Spain: Hijaz mode, oud-like plucks, darbuka in maqsum
//   bg  Bulgaria: the same mode in a 7/8 ruchenitsa, tambura-like plucks, tapan
//   en  Scotland: a Dorian air on a harp-like pluck over a pipe drone, soft bodhran
//   nl  the Netherlands: a carillon air in 3/4, as from a church tower, over a soft drone and the wind

(() => {
  const midiToHz = (m) => 440 * Math.pow(2, (m - 69) / 12);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];

  const HIJAZ = [0, 1, 4, 5, 7, 8, 10];
  const DORIAN = [0, 2, 3, 5, 7, 9, 10];
  const IONIAN = [0, 2, 4, 5, 7, 9, 11];

  // D = dum (low), T = tek (high), k = ka (soft high), '' = rest.
  // grace: chance of an oud-style grace note; fifth: a fifth over the bass, like pipes; weak: chance of
  // a note between beats; bell: struck bells instead of plucked strings.
  const FLAVOURS = {
    es: { scale: HIJAZ, root: 62, step: 0.27, beats: ['D', 'T', '', 'T', 'D', '', 'T', ''], strong: [0, 4],
          pluck: { bright: 0.62, sustain: 0.4972, seconds: 2.6 }, drone: { gain: 0.032, cutoff: 260 },
          drum: { dum: [118, 58], tek: 3400, gain: 1 }, wind: 0.018, grace: 0.18 },
    bg: { scale: HIJAZ, root: 62, step: 0.2, beats: ['D', '', 'T', '', 'D', '', 'k'], strong: [0, 4],
          pluck: { bright: 0.7, sustain: 0.4975, seconds: 2.4 }, drone: { gain: 0.03, cutoff: 300 },
          drum: { dum: [96, 46], tek: 2600, gain: 1.1 }, wind: 0.016, grace: 0.18 },
    en: { scale: DORIAN, root: 62, step: 0.34, beats: ['D', '', 'k', 'T', '', 'k'], strong: [0, 3],
          pluck: { bright: 0.45, sustain: 0.4988, seconds: 4 }, drone: { gain: 0.05, cutoff: 620 },
          drum: { dum: [80, 42], tek: 1800, gain: 0.7 }, wind: 0.026, fifth: true },
    nl: { scale: IONIAN, root: 67, step: 0.3, beats: ['', '', '', '', '', ''], strong: [0, 2, 4], weak: 0.3,
          bell: { seconds: 4.5 }, drone: { gain: 0.02, cutoff: 240 },
          drum: { dum: [80, 42], tek: 1800, gain: 0 }, wind: 0.03 },
  };

  function impulse(ctx, seconds, decay) {
    const length = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, length, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
    }
    return buf;
  }

  // Karplus–Strong plucked string, rendered once per note and cached.
  function pluckBuffer(ctx, freq, { bright, sustain, seconds }) {
    const sr = ctx.sampleRate;
    const n = Math.floor(sr * seconds);
    const buf = ctx.createBuffer(1, n, sr);
    const out = buf.getChannelData(0);
    const period = Math.max(2, Math.round(sr / freq));
    const ring = new Float32Array(period);
    for (let i = 0; i < period; i++) ring[i] = Math.random() * 2 - 1;
    for (let i = 1; i < period; i++) ring[i] = bright * ring[i] + (1 - bright) * ring[i - 1];
    let idx = 0;
    for (let i = 0; i < n; i++) {
      const next = idx + 1 === period ? 0 : idx + 1;
      const v = ring[idx];
      out[i] = v;
      ring[idx] = sustain * (v + ring[next]);
      idx = next;
    }
    const fade = Math.floor(sr * 0.2);
    for (let i = 0; i < fade; i++) out[n - fade + i] *= 1 - i / fade;
    return buf;
  }

  // Carillon bell: decaying partials at the ratios of a tuned bell (hum, prime, minor third, fifth,
  // nominal and above), the higher ones dying sooner, and small bells sooner than big ones.
  const BELL_PARTIALS = [[0.5, 0.11, 1], [1, 0.2, 0.6], [1.2, 0.125, 0.45], [1.5, 0.055, 0.35],
                         [2, 0.15, 0.3], [2.5, 0.04, 0.2], [3, 0.03, 0.15], [4.2, 0.018, 0.08]];
  function bellBuffer(ctx, freq, { seconds }) {
    const sr = ctx.sampleRate;
    const n = Math.floor(sr * seconds);
    const buf = ctx.createBuffer(1, n, sr);
    const out = buf.getChannelData(0);
    const size = Math.min(1, Math.max(0.6, Math.sqrt(392 / freq)));
    for (const [ratio, amp, life] of BELL_PARTIALS) {
      const f = freq * ratio;
      if (f > sr * 0.45) continue;
      // Turn a phasor instead of calling Math.sin for every sample.
      const cw = Math.cos((2 * Math.PI * f) / sr);
      const sw = Math.sin((2 * Math.PI * f) / sr);
      const decay = Math.exp(-1 / (sr * seconds * life * size));
      let c = 1;
      let s = 0;
      let a = amp;
      for (let i = 0; i < n; i++) {
        out[i] += a * s;
        const c2 = c * cw - s * sw;
        s = s * cw + c * sw;
        c = c2;
        a *= decay;
      }
    }
    const attack = Math.floor(sr * 0.003);
    for (let i = 0; i < attack; i++) out[i] *= i / attack;
    const fade = Math.floor(sr * 0.5);
    for (let i = 0; i < fade; i++) out[n - fade + i] *= 1 - i / fade;
    return buf;
  }

  function createAmbience(ctx, lang) {
    const F = FLAVOURS[lang] || FLAVOURS.en;

    const master = ctx.createGain();
    master.gain.value = 0;
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -12;
    limiter.ratio.value = 6;
    master.connect(limiter).connect(ctx.destination);

    const reverb = ctx.createConvolver();
    reverb.buffer = impulse(ctx, 3.6, 2.8);
    const wet = ctx.createGain();
    wet.gain.value = 0.42;
    reverb.connect(wet).connect(master);

    const strings = ctx.createGain();
    const body = ctx.createBiquadFilter();
    body.type = 'peaking';
    body.frequency.value = 260;
    body.gain.value = 5;
    const tone = ctx.createBiquadFilter();
    tone.type = 'lowpass';
    tone.frequency.value = 4200;
    strings.connect(body).connect(tone);
    tone.connect(master);
    tone.connect(reverb);

    const drums = ctx.createGain();
    drums.gain.value = 0.38 * F.drum.gain;
    drums.connect(master);
    const drumVerb = ctx.createGain();
    drumVerb.gain.value = 0.25;
    drums.connect(drumVerb).connect(reverb);

    const sources = [];

    // Drone on the tonic and fifth: a soft tanpura hum, or highland pipes for Scotland.
    const droneFilter = ctx.createBiquadFilter();
    droneFilter.type = 'lowpass';
    droneFilter.frequency.value = F.drone.cutoff;
    droneFilter.Q.value = 0.7;
    const droneGain = ctx.createGain();
    droneGain.gain.value = F.drone.gain;
    droneFilter.connect(droneGain);
    droneGain.connect(master);
    droneGain.connect(reverb);
    [[F.root - 24, 'sawtooth'], [F.root - 24, 'sawtooth', 1.004], [F.root - 17, 'sawtooth']].forEach(([m, type, detune = 1]) => {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = midiToHz(m) * detune;
      o.connect(droneFilter);
      sources.push(o);
    });
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.05;
    const lfoDepth = ctx.createGain();
    lfoDepth.gain.value = F.drone.cutoff * 0.35;
    lfo.connect(lfoDepth).connect(droneFilter.frequency);
    sources.push(lfo);

    // Breeze: filtered noise that rises and falls.
    const noise = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
    const nd = noise.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    const wind = ctx.createBufferSource();
    wind.buffer = noise;
    wind.loop = true;
    const windFilter = ctx.createBiquadFilter();
    windFilter.type = 'bandpass';
    windFilter.frequency.value = 600;
    windFilter.Q.value = 0.6;
    const windGain = ctx.createGain();
    windGain.gain.value = F.wind;
    wind.connect(windFilter).connect(windGain);
    windGain.connect(master);
    const gust = ctx.createOscillator();
    gust.frequency.value = 0.06;
    const gustDepth = ctx.createGain();
    gustDepth.gain.value = F.wind * 0.7;
    gust.connect(gustDepth).connect(windGain.gain);
    sources.push(wind, gust);

    const cache = new Map();
    const bufferFor = (midi) => {
      if (!cache.has(midi)) {
        cache.set(midi, F.bell ? bellBuffer(ctx, midiToHz(midi), F.bell) : pluckBuffer(ctx, midiToHz(midi), F.pluck));
      }
      return cache.get(midi);
    };

    function voice(midi, time, gain, pan) {
      const src = ctx.createBufferSource();
      src.buffer = bufferFor(midi);
      const amp = ctx.createGain();
      amp.gain.value = gain;
      const p = ctx.createStereoPanner();
      p.pan.value = Math.max(-1, Math.min(1, pan));
      src.connect(amp).connect(p).connect(strings);
      src.start(time);
    }

    function dum(time, gain) {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(F.drum.dum[0], time);
      o.frequency.exponentialRampToValueAtTime(F.drum.dum[1], time + 0.14);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, time);
      g.gain.exponentialRampToValueAtTime(gain, time + 0.006);
      g.gain.exponentialRampToValueAtTime(0.0001, time + 0.4);
      o.connect(g).connect(drums);
      o.start(time);
      o.stop(time + 0.45);
    }

    function tek(time, gain) {
      const s = ctx.createBufferSource();
      s.buffer = noise;
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = F.drum.tek;
      bp.Q.value = 1.4;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, time);
      g.gain.exponentialRampToValueAtTime(gain, time + 0.003);
      g.gain.exponentialRampToValueAtTime(0.0001, time + 0.08);
      s.connect(bp).connect(g).connect(drums);
      s.start(time, Math.random() * 2);
      s.stop(time + 0.1);
    }

    // Melody: a wandering line on the mode, two octaves wide, drawn home at phrase ends.
    const degrees = [...F.scale, ...F.scale.map((s) => s + 12), 24];
    let deg = 0;
    let step = 0;
    let nextTime = 0;
    const barLen = F.beats.length;
    const phraseBars = 4;

    function scheduleStep(t) {
      const inBar = step % barLen;
      const bar = Math.floor(step / barLen);
      const inPhrase = bar % phraseBars;
      const human = (Math.random() - 0.5) * 0.018;
      const resting = inPhrase === phraseBars - 1 && inBar > barLen / 2 && Math.random() < 0.7;

      // Percussion
      const beat = F.beats[inBar];
      if (beat === 'D') dum(t + human, inBar === 0 ? 0.9 : 0.7);
      else if (beat === 'T') tek(t + human, 0.32);
      else if (beat === 'k') tek(t + human, 0.16);

      // Bass on the bar
      if (inBar === 0) {
        voice(F.root - 12, t + human, 0.2, -0.25);
        if (F.fifth) voice(F.root - 5, t + human + 0.01, 0.12, 0.25);
      }

      // Melody
      const strong = F.strong.includes(inBar);
      if (!resting && Math.random() < (strong ? 0.85 : F.weak ?? 0.5)) {
        const towardHome = inPhrase === phraseBars - 1 ? Math.sign(-deg) : 0;
        deg += pick([-2, -1, -1, 0, 1, 1, 2]) + towardHome;
        deg = Math.max(0, Math.min(degrees.length - 1, deg));
        const note = F.root + degrees[deg];
        // An oud-style grace note from the step above, now and then.
        if (F.grace && Math.random() < F.grace && deg + 1 < degrees.length) {
          voice(F.root + degrees[deg + 1], t + human - 0.05, 0.07, 0.2);
        }
        voice(note, t + human, (strong ? 0.17 : 0.12) * (0.85 + Math.random() * 0.3), 0.3 - Math.random() * 0.6);
      }
      step += 1;
    }

    return {
      start(at = ctx.currentTime) {
        sources.forEach((s) => s.start(at));
        nextTime = at + 0.3;
      },
      scheduleUntil(t) {
        while (nextTime < t) {
          scheduleStep(nextTime);
          nextTime += F.step;
        }
      },
      fade(to, seconds) {
        const now = ctx.currentTime;
        master.gain.cancelScheduledValues(now);
        master.gain.setValueAtTime(master.gain.value, now);
        master.gain.linearRampToValueAtTime(to, now + seconds);
      },
    };
  }

  window.TsekoAmbience = { createAmbience, FLAVOURS };

  // ---- The toggle ----
  const button = document.getElementById('music');
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!button) return;
  if (!AudioCtx) {
    button.hidden = true;
    return;
  }

  const S = (() => {
    try { return JSON.parse(document.getElementById('strings').textContent); } catch { return {}; }
  })();
  const t = (key, fallback) => S[key] || fallback;
  const lang = (document.documentElement.lang || 'en').slice(0, 2);
  const state = button.querySelector('.music-state');
  const name = button.querySelector('.music-name');
  if (name) name.textContent = t('music_name', 'Ambience');
  button.hidden = false;
  let ctx = null;
  let amb = null;
  let timer = null;
  let playing = false;

  function render() {
    button.setAttribute('aria-pressed', String(playing));
    state.textContent = playing ? t('music_on', 'on') : t('music_off', 'off');
    button.title = playing ? t('music_title_on', 'Turn the ambience off') : t('music_title_off', 'Play an original ambient tune');
  }

  async function play() {
    if (!ctx) {
      ctx = new AudioCtx();
      amb = createAmbience(ctx, lang);
      amb.start();
    }
    await ctx.resume();
    amb.fade(0.8, 3);
    clearInterval(timer);
    timer = setInterval(() => amb.scheduleUntil(ctx.currentTime + 0.8), 200);
    amb.scheduleUntil(ctx.currentTime + 0.8);
    playing = true;
    render();
  }

  function stop() {
    amb.fade(0, 1.2);
    clearInterval(timer);
    playing = false;
    render();
    setTimeout(() => { if (!playing) ctx.suspend(); }, 1300);
  }

  button.addEventListener('click', () => (playing ? stop() : play()));
  document.addEventListener('tseko:external-audio', () => { if (playing) stop(); });
  render();
})();
