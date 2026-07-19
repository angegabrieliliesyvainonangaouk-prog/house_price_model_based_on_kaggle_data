const API = '/api/v1';
let lang = localStorage.getItem('ml_lang') || 'fr';
let token = localStorage.getItem('ml_token') || '';
let dailyCount = parseInt(localStorage.getItem('ml_daily_count') || '0');
let dailyDate = localStorage.getItem('ml_daily_date') || '';
const DAILY_LIMIT = 20;
let rawCSVText = null;
let rawCSVFile = null;
let cleanedCSVText = null;
let cleanedBlobUrl = null;
let selectedPrice = '1.00';
let rawColumnsData = [];

function t(key, replacements) {
  const dict = {
    fr: {
      csv_columns_info: "{cols} colonnes detectees",
      csv_success: "Fichier telecharge avec succes",
      csv_success_desc: "Le fichier CSV nettoye est pret.",
      loading_csv: "Nettoyage...",
      error_csv_format: "Format CSV requis.",
      error_unknown: "Erreur inconnue",
      predictions_remaining: "Il vous reste {n} predictions sur {max} aujourd'hui.",
      predictions_badge: "{n}/{max} predictions aujourd'hui",
      payment_error: "Erreur de paiement. Veuillez reessayer.",
      payment_cancel: "Paiement annule",
      reading_file: "Lecture de {name}...",
      csv_preview: "{name} - {rows} lignes, {cols} colonnes",
    },
    en: {
      csv_columns_info: "{cols} columns detected",
      csv_success: "File downloaded successfully",
      csv_success_desc: "The cleaned CSV file is ready.",
      loading_csv: "Cleaning...",
      error_csv_format: "CSV format required.",
      error_unknown: "Unknown error",
      predictions_remaining: "You have {n} of {max} predictions remaining today.",
      predictions_badge: "{n}/{max} predictions today",
      payment_error: "Payment error. Please try again.",
      payment_cancel: "Payment cancelled",
      reading_file: "Reading {name}...",
      csv_preview: "{name} - {rows} rows, {cols} columns",
    }
  };
  let s = (dict[lang] || dict.fr)[key] || key;
  if (replacements) {
    for (const [k, v] of Object.entries(replacements)) {
      s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), v);
    }
  }
  return s;
}

function getToken() {
  if (!token) {
    token = 'anon_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem('ml_token', token);
  }
  return token;
}

function resetDailyIfNeeded() {
  const today = new Date().toDateString();
  if (dailyDate !== today) {
    dailyCount = 0;
    dailyDate = today;
    localStorage.setItem('ml_daily_count', '0');
    localStorage.setItem('ml_daily_date', today);
  }
}

function incrementCount() {
  dailyCount++;
  localStorage.setItem('ml_daily_count', String(dailyCount));
  updateRemaining();
}

function updateRemaining() {
  const remaining = Math.max(0, DAILY_LIMIT - dailyCount);
  const el = document.getElementById('cleanRemaining');
  if (el) el.textContent = t('predictions_remaining', {n: remaining, max: DAILY_LIMIT});
}

function extractErrorDetail(data) {
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map(e => {
      const field = e.field || (e.loc ? e.loc.filter(x => x !== 'body').join('.') : '');
      const msg = e.message || e.msg || '';
      return (field ? '[' + field + '] ' : '') + msg;
    }).join(' | ');
  }
  return data.detail || t('error_unknown');
}

async function loadColumnsGuide() {
  try {
    const res = await fetch(API + '/raw-columns-guide');
    let data;
    try { data = await res.json(); } catch { data = { columns: [] }; }
    rawColumnsData = data.columns || [];
    const tbody = document.getElementById('columnsTableBody');
    const countBadge = document.getElementById('columnsCount');
    if (countBadge) countBadge.textContent = rawColumnsData.length + ' colonnes';
    tbody.innerHTML = '';
    rawColumnsData.forEach((col, i) => {
      const tr = document.createElement('tr');
      const typeClass = col.type === 'select' ? 'sel' : 'num';
      const typeLabel = col.type === 'select' ? 'Select' : 'Numerique';
      const options = col.options && col.options.length ? col.options.join(', ') : (col.unit || '-');
      const desc = lang === 'en' ? (col.desc_en || col.desc_fr || '') : (col.desc_fr || col.desc_en || '');
      const label = lang === 'en' ? (col.label_en || col.label_fr || col.name) : (col.label_fr || col.label_en || col.name);
      tr.innerHTML = '<td class="col-index">' + (i + 1) + '</td>' +
        '<td><span class="col-name">' + col.name + '</span><br><span class="col-label">' + label + '</span></td>' +
        '<td><span class="col-type ' + typeClass + '">' + typeLabel + '</span></td>' +
        '<td><span class="col-options">' + options + '</span></td>' +
        '<td><span class="col-desc">' + desc + '</span></td>';
      tbody.appendChild(tr);
    });
  } catch(e) {
    console.error('Failed to load columns guide:', e);
  }
}

function setupCleaningUpload() {
  const zone = document.getElementById('cleanUploadZone');
  const input = document.getElementById('cleanCsvInput');
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      handleCleanFile(e.dataTransfer.files[0]);
    }
  });
  input.addEventListener('change', () => { if (input.files.length) handleCleanFile(input.files[0]); });
}

async function handleCleanFile(file) {
  const preview = document.getElementById('cleanPreview');
  if (!file.name.endsWith('.csv')) {
    preview.className = 'upload-preview show error';
    preview.textContent = t('error_csv_format');
    rawCSVText = null;
    rawCSVFile = null;
    document.getElementById('startCleanBtn').disabled = true;
    return;
  }
  preview.className = 'upload-preview show';
  preview.textContent = t('reading_file', {name: file.name});
  rawCSVFile = file;
  rawCSVText = await file.text();
  const lines = rawCSVText.trim().split('\n');
  const csvColCount = lines[0].split(',').length;
  const rowCount = lines.length - 1;
  preview.textContent = t('csv_preview', {name: file.name, rows: rowCount, cols: csvColCount}) + ' | ' + t('csv_columns_info', {cols: csvColCount});
  if (csvColCount < 161) {
    document.getElementById('startCleanBtn').disabled = false;
  } else {
    preview.textContent += ' - Ce fichier semble deja nettoye (161 colonnes). Retournez a la page principale pour lancer les predictions.';
    document.getElementById('startCleanBtn').disabled = true;
  }
}

async function startCleaning() {
  if (!rawCSVFile) return;
  const step1 = document.getElementById('step1');
  const step2 = document.getElementById('step2');
  const step3 = document.getElementById('step3');
  const progress = document.getElementById('cleaningProgress');
  const cleanBtn = document.getElementById('startCleanBtn');
  const result = document.getElementById('cleaningResult');
  const downloadSection = document.getElementById('downloadSection');

  step1.classList.remove('active');
  step1.classList.add('done');
  step2.classList.add('active');
  cleanBtn.disabled = true;
  progress.style.display = 'flex';
  result.className = 'result-card';
  downloadSection.style.display = 'none';

  try {
    const formData = new FormData();
    formData.append('file', rawCSVFile);
    const res = await fetch(API + '/clean', {
      method: 'POST',
      headers: {'X-Token': getToken()},
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({detail: t('error_unknown')}));
      throw new Error(extractErrorDetail(err));
    }
    const respBlob = await res.blob();
    cleanedCSVText = await respBlob.text();
    const blob = new Blob([cleanedCSVText], {type: 'text/csv'});
    const blobUrl = URL.createObjectURL(blob);
    cleanedBlobUrl = blobUrl;

    step2.classList.remove('active');
    step2.classList.add('done');
    step3.classList.add('active');
    result.className = 'result-card show success';
    result.innerHTML = '<div class="result-label">Nettoyage termine !</div><div class="result-detail">Le fichier CSV a ete transforme de 80 a ' + countCleanedColumns() + ' colonnes.</div>';
    downloadSection.style.display = 'block';
    document.getElementById('downloadBtn').disabled = false;
    document.getElementById('predictCleanBtn').disabled = false;
    var dlWrap = document.getElementById('directDownloadWrap');
    var dlLink = document.getElementById('directDownloadLink');
    if (dlWrap && dlLink) {
      dlLink.href = blobUrl;
      dlWrap.style.display = 'block';
    }
    incrementCount();
  } catch(e) {
    step2.classList.remove('active');
    step2.classList.add('error');
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">' + e.message + '</div>';
    cleanBtn.disabled = false;
  } finally {
    progress.style.display = 'none';
  }
}

function countCleanedColumns() {
  if (!cleanedCSVText) return 0;
  const lines = cleanedCSVText.trim().split('\n');
  return lines[0].split(',').length;
}

function setupPriceSelector() {
  document.querySelectorAll('.price-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('.price-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      selectedPrice = opt.dataset.price;
      document.getElementById('customPrice').value = '';
    });
  });
  document.getElementById('customPrice').addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    if (val >= 1) {
      document.querySelectorAll('.price-option').forEach(o => o.classList.remove('selected'));
      selectedPrice = val.toFixed(2);
    }
  });
}

// FONCTION APPELEE DIRECTEMENT AU CLIC (synchrone)
// Ouvre la popup AVANT tout travail async pour eviter le blocage par le navigateur
function downloadWithPayment() {
  if (!cleanedCSVText) return;
  // Ouvrir la popup SYNCHRONEMENT depuis le handler de clic
  // Si on appelle window.open() apres un await, le navigateur le bloque
  const paypalWindow = window.open('', 'paypal', 'width=600,height=700,scrollbars=yes');
  if (!paypalWindow) {
    const result = document.getElementById('cleaningResult');
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">La popup a ete bloquee. Autorisez les popups pour ce site.</div>';
    return;
  }
  // Maintenant on lance le travail asynchrome en passant la reference de la fenetre
  processPayment(paypalWindow);
}

// FONCTION ASYNCHROME : cree l'ordre, redirige la popup, ecoute le retour
async function processPayment(paypalWindow) {
  const btn = document.getElementById('downloadBtn');
  const paypalSection = document.getElementById('paypalSection');
  const paypalStatus = document.getElementById('paypalStatus');

  const price = parseFloat(selectedPrice);
  if (isNaN(price) || price < 1) { selectedPrice = '1.00'; }

  btn.disabled = true;
  paypalSection.style.display = 'block';
  paypalStatus.textContent = 'Creation de la commande PayPal...';

  try {
    // Creer l'ordre aupres de notre backend
    const createRes = await fetch(API + '/paypal/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({amount: selectedPrice, currency_code: 'EUR'})
    });
    let createData;
    try { createData = await createRes.json(); } catch { createData = { detail: 'Erreur serveur (HTTP ' + createRes.status + ')' }; }
    if (!createRes.ok) throw new Error(extractErrorDetail(createData));

    const orderId = createData.order_id;
    const approvalUrl = createData.approval_url;
    if (!approvalUrl) throw new Error('No approval URL from PayPal');

    paypalStatus.textContent = 'Ouverture de PayPal... La fenetre de paiement s\'ouvre.';

    // Rediriger la popup (deja ouverte) vers PayPal
    paypalWindow.location.href = approvalUrl;

    // Drapeau pour eviter de traiter le succes deux fois
    let resolved = false;

    function onPaymentSuccess(orderIdFromPaypal) {
      if (resolved) return;
      resolved = true;
      clearInterval(pollInterval);
      clearTimeout(timeoutId);
      window.removeEventListener('message', messageHandler);
      handlePaymentComplete();
    }

    function handlePaymentComplete() {
      var url = cleanedBlobUrl;
      if (!url) {
        var blob = new Blob([cleanedCSVText], {type: 'text/csv'});
        url = URL.createObjectURL(blob);
        cleanedBlobUrl = url;
      }
      // Mettre a jour le lien de telechargement visible
      var dlLink = document.getElementById('directDownloadLink');
      if (dlLink) { dlLink.href = url; dlLink.click(); }
      // Aussi tenter l'auto-download via un lien temporaire
      try {
        var a = document.createElement('a');
        a.href = url; a.download = 'cleaned.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } catch(_) {}
      paypalSection.style.display = 'none';
      var result = document.getElementById('cleaningResult');
      result.className = 'result-card show success';
      result.innerHTML = '<div class="result-label">' + t('csv_success') + '</div><div class="result-detail">' + t('csv_success_desc') + '</div>';
    }

    function onPaymentError(message) {
      if (resolved) return;
      resolved = true;
      clearInterval(pollInterval);
      clearTimeout(timeoutId);
      window.removeEventListener('message', messageHandler);
      paypalSection.style.display = 'none';
      const result = document.getElementById('cleaningResult');
      result.className = 'result-card show error';
      result.innerHTML = '<div class="error-text">' + message + '</div>';
      btn.disabled = false;
    }

    // METHODE 1 (principale): postMessage depuis la page de retour PayPal
    function messageHandler(event) {
      if (event.data && event.data.type === 'paypal-success' && event.data.order_id === orderId) {
        onPaymentSuccess(event.data.order_id);
      }
    }
    window.addEventListener('message', messageHandler);

    // METHODE 2 (fallback): polling - detecte quand la popup se ferme
    const pollInterval = setInterval(async () => {
      try {
        if (paypalWindow.closed) {
          clearInterval(pollInterval);
          paypalStatus.textContent = 'Verification du paiement...';
          const captureRes = await fetch(API + '/paypal/capture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({order_id: orderId})
          });
          let captureData;
          try { captureData = await captureRes.json(); } catch { captureData = { detail: 'Erreur serveur' }; }
          if (!captureRes.ok) throw new Error(extractErrorDetail(captureData));
          if (captureData.status === 'COMPLETED') {
            onPaymentSuccess(orderId);
          } else {
            onPaymentError(t('payment_error'));
          }
        }
      } catch(err) {
        onPaymentError(err.message);
      }
    }, 1500);

    // Timeout de 5 minutes
    const timeoutId = setTimeout(() => {
      if (!resolved && !paypalWindow.closed) {
        onPaymentError(t('payment_cancel'));
      }
    }, 300000);

  } catch(e) {
    paypalSection.style.display = 'none';
    const result = document.getElementById('cleaningResult');
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">' + e.message + '</div>';
    btn.disabled = false;
  }
}

async function predictDirectly() {
  if (!cleanedCSVText) return;
  const btn = document.getElementById('predictCleanBtn');
  const result = document.getElementById('cleaningResult');
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-text"><span class="spinner"></span>Calcul...</span>';
  result.className = 'result-card';
  try {
    const formData = new FormData();
    formData.append('file', new Blob([cleanedCSVText], {type: 'text/csv'}), 'cleaned.csv');
    formData.append('model', 'xgboost');
    const res = await fetch(API + '/predict/csv', {
      method: 'POST',
      headers: {'X-Token': getToken()},
      body: formData
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({detail: t('error_unknown')}));
      throw new Error(extractErrorDetail(err));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'predictions.csv';
    a.click();
    URL.revokeObjectURL(url);
    result.className = 'result-card show success';
    result.innerHTML = '<div class="result-label">' + t('csv_success') + '</div><div class="result-detail">Les predictions ont ete ajoutees au fichier CSV.</div>';
    incrementCount();
  } catch(e) {
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">' + e.message + '</div>';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Lancer les predictions (gratuit)';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  resetDailyIfNeeded();
  loadColumnsGuide();
  setupCleaningUpload();
  setupPriceSelector();
  updateRemaining();
  document.getElementById('startCleanBtn').addEventListener('click', startCleaning);
  document.getElementById('downloadBtn').addEventListener('click', downloadWithPayment);
  document.getElementById('predictCleanBtn').addEventListener('click', predictDirectly);

  const pendingCSV = sessionStorage.getItem('pendingCleaningCSV');
  const pendingName = sessionStorage.getItem('pendingCleaningName');
  if (pendingCSV && pendingName) {
    sessionStorage.removeItem('pendingCleaningCSV');
    sessionStorage.removeItem('pendingCleaningName');
    rawCSVText = pendingCSV;
    rawCSVFile = new File([pendingCSV], pendingName, {type: 'text/csv'});
    const lines = pendingCSV.trim().split('\n');
    const colCount = lines[0].split(',').length;
    const rowCount = lines.length - 1;
    const preview = document.getElementById('cleanPreview');
    preview.className = 'upload-preview show';
    preview.textContent = pendingName + ' - ' + rowCount + ' lignes, ' + colCount + ' colonnes | ' + colCount + ' colonnes detectees';
    if (colCount <= 80) {
      document.getElementById('startCleanBtn').disabled = false;
    }
  }
});
