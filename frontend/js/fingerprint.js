const Fingerprint = (() => {
  async function sha256(str) {
    const buf = new TextEncoder().encode(str);
    const hash = await crypto.subtle.digest('SHA-256', buf);
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  function getCanvasFingerprint() {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 200;
      canvas.height = 50;
      const ctx = canvas.getContext('2d');
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillStyle = '#f60';
      ctx.fillRect(0, 0, 200, 50);
      ctx.fillStyle = '#069';
      ctx.fillText('fingerprint-test-2024', 2, 15);
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.fillText('fp-test', 4, 30);
      return canvas.toDataURL();
    } catch (e) { return 'canvas-blocked'; }
  }

  function getWebGLInfo() {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      if (!gl) return 'webgl-blocked';
      const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
      const vendor = gl.getParameter(debugInfo ? debugInfo.UNMASKED_VENDOR_WEBGL : gl.VENDOR);
      const renderer = gl.getParameter(debugInfo ? debugInfo.UNMASKED_RENDERER_WEBGL : gl.RENDERER);
      const version = gl.getParameter(gl.VERSION);
      return `${vendor}|${renderer}|${version}`;
    } catch (e) { return 'webgl-error'; }
  }

  function getAudioFingerprint() {
    try {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return 'audio-blocked';
      const ctx = new AC();
      const osc = ctx.createOscillator();
      const analyser = ctx.createAnalyser();
      const gain = ctx.createGain();
      const script = ctx.createScriptProcessor(4096, 1, 1);
      gain.gain.value = 0;
      osc.type = 'triangle';
      osc.frequency.value = 10000;
      osc.connect(analyser);
      analyser.connect(script);
      script.connect(gain);
      gain.connect(ctx.destination);
      osc.start(0);
      const data = new Float32Array(analyser.frequencyBinCount);
      analyser.getFloatFrequencyData(data);
      osc.stop();
      ctx.close();
      let sum = 0;
      for (let i = 0; i < data.length; i++) sum += Math.abs(data[i]);
      return sum.toString();
    } catch (e) { return 'audio-error'; }
  }

  function getScreenInfo() {
    return `${screen.colorDepth}|${screen.width}x${screen.height}|${window.devicePixelRatio}`;
  }

  function getNavigatorInfo() {
    const props = [];
    props.push(navigator.language || '');
    props.push(navigator.platform || '');
    props.push(navigator.hardwareConcurrency || 0);
    props.push(navigator.deviceMemory || 0);
    props.push(navigator.maxTouchPoints || 0);
    props.push(navigator.cookieEnabled ? 1 : 0);
    props.push(navigator.doNotTrack || '');
    return props.join('|');
  }

  function getTimezoneInfo() {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (e) {
      return new Date().getTimezoneOffset().toString();
    }
  }

  function getFontFingerprint() {
    const testFonts = [
      'Arial', 'Verdana', 'Times New Roman', 'Courier New', 'Georgia',
      'Palatino', 'Garamond', 'Comic Sans MS', 'Impact', 'Lucida Console',
      'Tahoma', 'Trebuchet MS', 'Century Gothic', 'Futura', 'Rockwell',
      'Consolas', 'Helvetica', 'Calibri', 'Cambria', 'Gill Sans'
    ];
    const baseFonts = ['monospace', 'sans-serif', 'serif'];
    const span = document.createElement('span');
    span.style.fontSize = '72px';
    span.style.position = 'absolute';
    span.style.left = '-9999px';
    span.innerHTML = 'mmmmmmmmmmlli';
    document.body.appendChild(span);
    const baseWidths = {};
    for (const bf of baseFonts) {
      span.style.fontFamily = bf;
      baseWidths[bf] = span.offsetWidth;
    }
    const detected = [];
    for (const f of testFonts) {
      let found = false;
      for (const bf of baseFonts) {
        span.style.fontFamily = `'${f}', ${bf}`;
        if (span.offsetWidth !== baseWidths[bf]) { found = true; break; }
      }
      if (found) detected.push(f);
    }
    document.body.removeChild(span);
    return detected.join(',');
  }

  function getPluginsFingerprint() {
    const plugins = [];
    if (navigator.plugins) {
      for (let i = 0; i < Math.min(navigator.plugins.length, 20); i++) {
        const p = navigator.plugins[i];
        plugins.push(`${p.name}|${p.filename}`);
      }
    }
    return plugins.join(';');
  }

  async function generate() {
    const components = [
      getCanvasFingerprint(),
      getWebGLInfo(),
      getAudioFingerprint(),
      getScreenInfo(),
      getNavigatorInfo(),
      getTimezoneInfo(),
      getFontFingerprint(),
      getPluginsFingerprint(),
    ];
    const raw = components.join('|||');
    const hash = await sha256(raw);
    return { hash, components: components.length };
  }

  return { generate };
})();
