// Optional background ambience, off until the visitor turns it on.
// An original, generative piece in the mood of old gothic RPG towns: slow
// twelve-string-style arpeggios in D minor over a low drone and wind.
// Everything is synthesised live with the Web Audio API; no recordings are used.

(() => {
  const midiToHz = (m) => 440 * Math.pow(2, (m - 69) / 12);
  const pick = (list) => list[Math.floor(Math.random() * list.length)];

  // i – VI – iv – V in D minor, plus a III for variety. MIDI notes: bass first.
  const CHORDS = {
    Dm: [50, 57, 62, 65, 69],
    Bb: [46, 53, 58, 62, 65],
    Gm: [43, 50, 55, 58, 62],
    A: [45, 52, 57, 61, 64],
    F: [41, 48, 53, 57, 60],
  };
  const PROGRESSIONS = [
    ['Dm', 'Bb', 'Gm', 'A'],
    ['Dm', 'F', 'Gm', 'A'],
    ['Dm', 'Bb', 'F', 'A'],
  ];
  // Six eighth notes per bar (6/8). Numbers index into the chord.
  const PATTERNS = [
    [0, 1, 2, 3, 2, 1],
    [0, 2, 1, 4, 3, 2],
    [0, 1, 3, 2, 4, 2],
  ];
  const MELODY = [62, 64, 65, 67, 69, 70, 72, 74]; // D natural minor, upper octave
  const EIGHTH = 0.43; // seconds
  const BARS_PER_CHORD = 2;

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
  function pluckBuffer(ctx, freq, seconds) {
    const sr = ctx.sampleRate;
    const n = Math.floor(sr * seconds);
    const buf = ctx.createBuffer(1, n, sr);
    const out = buf.getChannelData(0);
    const period = Math.max(2, Math.round(sr / freq));
    const ring = new Float32Array(period);
    for (let i = 0; i < period; i++) ring[i] = Math.random() * 2 - 1;
    for (let i = 1; i < period; i++) ring[i] = 0.55 * ring[i] + 0.45 * ring[i - 1]; // soften the pick
    let idx = 0;
    for (let i = 0; i < n; i++) {
      const next = idx + 1 === period ? 0 : idx + 1;
      const v = ring[idx];
      out[i] = v;
      ring[idx] = 0.4985 * (v + ring[next]);
      idx = next;
    }
    // Short fade at the end so notes never click.
    const fade = Math.floor(sr * 0.2);
    for (let i = 0; i < fade; i++) out[n - fade + i] *= 1 - i / fade;
    return buf;
  }

  function createAmbience(ctx) {
    const master = ctx.createGain();
    master.gain.value = 0;
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -12;
    limiter.ratio.value = 6;
    master.connect(limiter).connect(ctx.destination);

    const reverb = ctx.createConvolver();
    reverb.buffer = impulse(ctx, 4.5, 2.6);
    const wet = ctx.createGain();
    wet.gain.value = 0.55;
    reverb.connect(wet).connect(master);

    // Guitar bus: a gentle tone filter, then dry and reverb.
    const guitar = ctx.createGain();
    guitar.gain.value = 0.9;
    const tone = ctx.createBiquadFilter();
    tone.type = 'lowpass';
    tone.frequency.value = 3600;
    const body = ctx.createBiquadFilter();
    body.type = 'peaking';
    body.frequency.value = 220;
    body.gain.value = 4;
    guitar.connect(body).connect(tone);
    tone.connect(master);
    tone.connect(reverb);

    // Drone on D with a slowly breathing filter.
    const droneFilter = ctx.createBiquadFilter();
    droneFilter.type = 'lowpass';
    droneFilter.frequency.value = 240;
    droneFilter.Q.value = 0.8;
    const droneGain = ctx.createGain();
    droneGain.gain.value = 0.05;
    droneFilter.connect(droneGain);
    droneGain.connect(master);
    droneGain.connect(reverb);
    const sources = [];
    [[midiToHz(38), 'sawtooth'], [midiToHz(38) * 1.004, 'sawtooth'], [midiToHz(45), 'triangle']].forEach(([f, type]) => {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f;
      o.connect(droneFilter);
      sources.push(o);
    });
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.045;
    const lfoDepth = ctx.createGain();
    lfoDepth.gain.value = 110;
    lfo.connect(lfoDepth).connect(droneFilter.frequency);
    sources.push(lfo);

    // Wind: filtered noise that rises and falls.
    const noise = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
    const nd = noise.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    const wind = ctx.createBufferSource();
    wind.buffer = noise;
    wind.loop = true;
    const windFilter = ctx.createBiquadFilter();
    windFilter.type = 'bandpass';
    windFilter.frequency.value = 520;
    windFilter.Q.value = 0.7;
    const windGain = ctx.createGain();
    windGain.gain.value = 0.022;
    wind.connect(windFilter).connect(windGain);
    windGain.connect(master);
    windGain.connect(reverb);
    const gust = ctx.createOscillator();
    gust.frequency.value = 0.07;
    const gustDepth = ctx.createGain();
    gustDepth.gain.value = 0.016;
    gust.connect(gustDepth).connect(windGain.gain);
    const sweep = ctx.createOscillator();
    sweep.frequency.value = 0.031;
    const sweepDepth = ctx.createGain();
    sweepDepth.gain.value = 260;
    sweep.connect(sweepDepth).connect(windFilter.frequency);
    sources.push(wind, gust, sweep);

    const cache = new Map();
    const bufferFor = (midi) => {
      if (!cache.has(midi)) cache.set(midi, pluckBuffer(ctx, midiToHz(midi), midi < 55 ? 5 : 3.5));
      return cache.get(midi);
    };

    function pluck(midi, time, gain, pan) {
      // Twelve-string: low notes get an octave partner, high notes a slightly detuned twin.
      const voices = midi < 60
        ? [[midi, 0, 1], [midi + 12, 0.014, 0.35]]
        : [[midi, 0, 1], [midi, 0.011, 0.5, 1.0035]];
      for (const [m, delay, g, rate = 1] of voices) {
        const src = ctx.createBufferSource();
        src.buffer = bufferFor(m);
        src.playbackRate.value = rate;
        const amp = ctx.createGain();
        amp.gain.value = gain * g;
        const p = ctx.createStereoPanner();
        p.pan.value = Math.max(-1, Math.min(1, pan + (delay ? -0.15 : 0)));
        src.connect(amp).connect(p).connect(guitar);
        src.start(time + delay);
      }
    }

    let step = 0;
    let nextTime = 0;
    let progression = PROGRESSIONS[0];
    let pattern = PATTERNS[0];

    function scheduleStep(t) {
      const stepsPerChord = 6 * BARS_PER_CHORD;
      const chordIndex = Math.floor(step / stepsPerChord) % progression.length;
      const inBar = step % 6;
      if (step % (stepsPerChord * progression.length) === 0) progression = pick(PROGRESSIONS);
      if (inBar === 0) pattern = pick(PATTERNS);
      const chord = CHORDS[progression[chordIndex]];
      const human = (Math.random() - 0.5) * 0.024;
      const accent = inBar === 0 ? 1 : inBar === 3 ? 0.8 : 0.62;
      if (inBar === 0 || Math.random() > 0.12) {
        const note = chord[pattern[inBar]];
        pluck(note, t + human, 0.16 * accent * (0.85 + Math.random() * 0.3), (pattern[inBar] - 2) * 0.18);
      }
      // Now and then a high note floats over the arpeggio.
      if ((inBar === 3 || inBar === 5) && Math.random() < 0.22) {
        const near = MELODY.filter((m) => chord.some((c) => (m - c) % 12 === 0));
        pluck(pick(near.length ? near : MELODY), t + human + 0.05, 0.1, 0.35 - Math.random() * 0.7);
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
          nextTime += EIGHTH;
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

  window.TsekoAmbience = { createAmbience };

  // ---- The toggle ----
  const button = document.getElementById('music');
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!button) return;
  if (!AudioCtx) {
    button.hidden = true;
    return;
  }

  const state = button.querySelector('.music-state');
  let ctx = null;
  let amb = null;
  let timer = null;
  let playing = false;

  function render() {
    button.setAttribute('aria-pressed', String(playing));
    state.textContent = playing ? 'on' : 'off';
    button.title = playing ? 'Turn the ambience off' : 'Play an original ambient tune';
  }

  async function play() {
    if (!ctx) {
      ctx = new AudioCtx();
      amb = createAmbience(ctx);
      amb.start();
    }
    await ctx.resume();
    amb.fade(1.8, 3);
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
