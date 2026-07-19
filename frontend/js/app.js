// FICHIER : app.js
// DESCRIPTION : JavaScript principal de l'application ML Predictor Pro
// CONTENU :
//   1. Variables globales et etat de l'application
//   2. Dictionnaire de traductions FR/EN (I18N)
//   3. Fonctions utilitaires de traduction (t, getLabel, getDesc)
//   4. Initialisation (init) et configuration des evenements
//   5. Gestion de la langue (toggleLang)
//   6. Gestion du token et du quota journalier
//   7. Gestion des onglets (tabs)
//   8. Construction du formulaire Express (buildNormalForm)
//   9. Validation des champs du formulaire Express
//  10. Prediction Express (predictNormal)
//  11. Gestion de l'upload CSV (setupUpload, handleFile, predictCsv)
//  12. PayPal integration (cleanCSVWithPayment)


// 1. VARIABLES GLOBALES ET ETAT DE L'APPLICATION
const API = '/api/v1';
let modelInfo = null;
let columnGuide = [];
let columnGuideMap = {};
let selectedModel = 'xgboost';
let csvData = null;
let csvFileObj = null;
let csvColCount = 0;
const DAILY_LIMIT = 20;
let dailyCount = 0;
let lang = localStorage.getItem('ml_lang') || 'fr';


// 2. DICTIONNAIRE DE TRADUCTIONS FR/EN (I18N)
const I18N = {
  fr: {
    app_title: "Estimation Immobiliere",
    tab_express: "Express",
    tab_professional: "Professionnel",
    normal_title: "Estimation rapide",
    normal_subtitle: "Renseignez les 10 criteres les plus importants. Des valeurs par defaut seront utilisees pour les autres.",
    prof_title: "Mode professionnel",
    prof_subtitle: "Importez un fichier CSV pour lancer les predictions completes.",
    model_xgb_desc: "Modele boosting 6 696 arbres - Haute precision",
    model_cat_desc: "Modele boosting 6 623 arbres - Robuste",
    template_text: "Besoin d'un modele de fichier ?",
    template_btn: "Telecharger le template CSV",
    upload_text: "Deposez votre fichier CSV ici ou cliquez pour parcourir",
      upload_hint_clean: "Deposez un fichier CSV nettoye (161 colonnes) pour lancer les predictions.",
    btn_predict_csv_free: "Lancer les predictions",
    btn_clean_data: "Nettoyer les donnees",
    btn_estimate: "Estimer le prix",
    btn_reset: "Reinitialiser",
    result_label: "Valeur estimee du bien",
    select_default: "Choisir...",
    predictions_remaining: "Il vous reste {n} predictions sur {max} aujourd'hui.",
    predictions_badge: "{n}/{max} predictions aujourd'hui",
    loading: "Calcul...",
    loading_csv: "Traitement...",
    field_invalid: "Corrigez les champs en erreur",
    error_fields_invalid: "Champs invalides ou manquants :",
    error_csv_format: "Format CSV requis.",
    error_unknown: "Erreur inconnue",
    err_required: "Ce champ est obligatoire",
    err_number: "Veuillez entrer un nombre",
    err_min_max: "Valeur entre {min} et {max}",
    err_invalid_option: "Valeur non autorisee",
    reading_file: "Lecture de {name}...",
    csv_preview: "{name} - {rows} lignes, {cols} colonnes",
    csv_success: "Fichier telecharge avec succes",
    csv_success_desc: "Les predictions ont ete ajoutees au fichier CSV.",
    result_model: "Modele: {model}",
    date_locale: "fr-FR",
    group_fallback: "Groupe",
    csv_columns_info: "{cols} colonnes detectees",
    csv_needs_cleaning: "CSV brut detecte ({cols} colonnes) - Cliquez sur 'Nettoyer les donnees' pour continuer.",
    csv_ready: "CSV pret ({cols} colonnes) - Cliquez sur 'Lancer les predictions'.",
  },
  en: {
    app_title: "Real Estate Estimation",
    tab_express: "Express",
    tab_professional: "Professional",
    normal_title: "Quick Estimation",
    normal_subtitle: "Fill in the 10 most important criteria. Default values will be used for the others.",
    prof_title: "Professional Mode",
    prof_subtitle: "Import a CSV file to run complete predictions.",
    model_xgb_desc: "Boosting model 6,696 trees - High accuracy",
    model_cat_desc: "Boosting model 6,623 trees - Robust",
    template_text: "Need a file template?",
    template_btn: "Download CSV Template",
    upload_text: "Drop your CSV file here or click to browse",
      upload_hint_clean: "Drop a cleaned CSV file (161 columns) to run predictions.",
    btn_predict_csv_free: "Run Predictions",
    btn_clean_data: "Clean Data",
    btn_estimate: "Estimate Price",
    btn_reset: "Reset",
    result_label: "Estimated Property Value",
    select_default: "Choose...",
    predictions_remaining: "You have {n} of {max} predictions remaining today.",
    predictions_badge: "{n}/{max} predictions today",
    loading: "Calculating...",
    loading_csv: "Processing...",
    field_invalid: "Fix the fields with errors",
    error_fields_invalid: "Invalid or missing fields:",
    error_csv_format: "CSV format required.",
    error_unknown: "Unknown error",
    err_required: "This field is required",
    err_number: "Please enter a number",
    err_min_max: "Value between {min} and {max}",
    err_invalid_option: "Invalid option",
    reading_file: "Reading {name}...",
    csv_preview: "{name} - {rows} rows, {cols} columns",
    csv_success: "File downloaded successfully",
    csv_success_desc: "Predictions have been added to the CSV file.",
    result_model: "Model: {model}",
    date_locale: "en-US",
    group_fallback: "Group",
    csv_columns_info: "{cols} columns detected",
    csv_needs_cleaning: "Raw CSV detected ({cols} columns) - Click 'Clean Data' to continue.",
    csv_ready: "CSV ready ({cols} columns) - Click 'Run Predictions'.",
  }
};


// 3. FONCTIONS UTILITAIRES DE TRADUCTION
function t(key, replacements) {
  let s = (I18N[lang] || I18N.fr)[key] || (I18N.fr)[key] || key;
  if (replacements) {
    for (const [k, v] of Object.entries(replacements)) {
      s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), v);
    }
  }
  return s;
}

function getLabel(col) {
  if (lang === 'en') return col.label_en || col.label_fr || col.name;
  return col.label_fr || col.label_en || col.name;
}

function getDesc(col) {
  if (lang === 'en') return col.desc_en || col.desc_fr || '';
  return col.desc_fr || col.desc_en || '';
}

function getGroupName(group) {
  if (lang === 'en') return group.name_en || group.name_fr || group.name || t('group_fallback');
  return group.name_fr || group.name_en || group.name || t('group_fallback');
}

function applyTranslations() {
  document.getElementById('appTitle').textContent = t('app_title');
  document.getElementById('langLabel').textContent = lang === 'fr' ? 'EN' : 'FR';
  document.documentElement.lang = lang === 'fr' ? 'fr' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  updateTokenDisplay();
  if (modelInfo) {
  }
  updateCsvButton();
}


// 4. INITIALISATION ET CONFIGURATION DES EVENEMENTS
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

async function tryRefreshToken() {
  try {
    const refreshRes = await fetch(API + '/auth/refresh', {
      method: 'POST',
      credentials: 'same-origin'
    });
    return refreshRes.ok;
  } catch (e) {
    return false;
  }
}

async function init() {
  let meRes = await fetch(API + '/me', { credentials: 'same-origin' });
  if (!meRes.ok) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      meRes = await fetch(API + '/me', { credentials: 'same-origin' });
    }
  }
  try {
    if (!meRes.ok) { window.location.href = '/login'; return; }
    const meData = await meRes.json();
    if (meData.must_change_password) {
      window.location.href = '/login#change-password';
      return;
    }
  } catch (e) {
    window.location.href = '/login';
    return;
  }

  buildNormalForm();
  updateTokenDisplay();

  try {
    const [healthRes, modelRes, guideRes] = await Promise.all([
      fetch(API + '/health', { credentials: 'same-origin' }),
      fetch(API + '/models', { credentials: 'same-origin' }),
      fetch(API + '/column-guide', { credentials: 'same-origin' })
    ]);
    let health, guideData;
    try { health = await healthRes.json(); } catch { health = { app: '?' }; }
    try { modelInfo = await modelRes.json(); } catch { modelInfo = {}; }
    try { guideData = await guideRes.json(); } catch { guideData = { columns: [] }; }
    columnGuide = guideData.columns || [];
    columnGuideMap = {};
    columnGuide.forEach(c => { columnGuideMap[c.name] = c; });
    document.getElementById('versionInfo').textContent = health.app;
    applyTranslations();
    buildNormalForm();
  } catch(e) {
  }

  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
  document.getElementById('predictNormalBtn').addEventListener('click', predictNormal);
  document.getElementById('resetNormalBtn').addEventListener('click', resetNormal);
  document.getElementById('predictCsvBtn').addEventListener('click', predictCsv);
  document.getElementById('cleanCsvBtn').addEventListener('click', redirectToCleaning);
  document.getElementById('langToggle').addEventListener('click', toggleLang);
  setupModelSelector('normalModelSelector');
  setupModelSelector('profModelSelector');
  setupUpload();

  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await fetch(API + '/auth/logout', { method: 'POST', credentials: 'same-origin', headers: {'X-CSRF-Token': getCookie('csrf_token')} });
    window.location.href = '/login';
  });
}


// 5. GESTION DE LA LANGUE
function toggleLang() {
  lang = lang === 'fr' ? 'en' : 'fr';
  localStorage.setItem('ml_lang', lang);
  applyTranslations();
  buildNormalForm();
}


// 6. GESTION DU QUOTA JOURNALIER
function updateTokenDisplay() {
  const remaining = Math.max(0, DAILY_LIMIT - dailyCount);
  const badge = document.getElementById('tokenBadge');
  if (badge) {
    badge.textContent = t('predictions_badge', {n: remaining, max: DAILY_LIMIT});
    badge.className = 'token-badge' + (remaining <= 3 ? ' warning' : '');
  }
  ['normalRemaining','csvRemaining'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = t('predictions_remaining', {n: remaining, max: DAILY_LIMIT});
  });
}

function incrementCount() {
  dailyCount++;
  updateTokenDisplay();
}


// 7. GESTION DES ONGLETS (TABS)
function setupModelSelector(id) {
  document.querySelectorAll('#' + id + ' .model-option').forEach(opt => {
    opt.addEventListener('click', () => {
      document.querySelectorAll('#' + id + ' .model-option').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      selectedModel = opt.dataset.model;
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
    t.setAttribute('aria-selected', t.dataset.tab === tabId);
  });
  document.querySelectorAll('.panel').forEach(p => {
    p.classList.toggle('active', p.id === 'panel-' + tabId);
  });
}


// 8. CONSTRUCTION DU FORMULAIRE EXPRESS (buildNormalForm)
function buildNormalForm() {
  const fields = [
    {name:'OverallQual',type:'number',min:1,max:10,step:1,placeholder:'Note 1 a 10'},
    {name:'GrLivArea',type:'number',min:100,max:10000,step:1,placeholder:'Ex: 1500'},
    {name:'YearBuilt',type:'number',min:1800,max:2026,step:1,placeholder:'Ex: 1970'},
    {name:'TotalBsmtSF',type:'number',min:0,max:10000,step:1,placeholder:'Ex: 800'},
    {name:'LotArea',type:'number',min:500,max:1000000,step:1,placeholder:'Ex: 10000'},
    {name:'BedroomAbvGr',type:'number',min:0,max:20,step:1,placeholder:'Ex: 3'},
    {name:'Totalbath',type:'number',min:0,max:10,step:0.5,placeholder:'Ex: 1.5'},
    {name:'Fireplaces',type:'number',min:0,max:10,step:1,placeholder:'Ex: 1'},
    {name:'KitchenQual',type:'select',options:['Ex','Gd','TA','Fa','Po']},
    {name:'CentralAir',type:'select',options:['Y','N']},
  ];
  const c = document.getElementById('normalForm');
  c.innerHTML = '';
  fields.forEach(f => {
    const g = document.createElement('div');
    g.className = 'form-group';
    const guide = columnGuideMap[f.name] || {};
    const label = document.createElement('label');
    label.className = 'form-label';
    label.htmlFor = 'nf-'+f.name;
    label.textContent = getLabel(guide) || f.name;
    const info = document.createElement('span');
    info.className = 'info-icon';
    info.textContent = '?';
    info.dataset.tip = getDesc(guide) || '';
    label.appendChild(info);
    g.appendChild(label);
    if (f.type === 'select') {
      const s = document.createElement('select');
      s.className = 'form-select'; s.id = 'nf-'+f.name;
      s.innerHTML = '<option value="">' + t('select_default') + '</option>';
      f.options.forEach(o => { const opt = document.createElement('option'); opt.value = o; opt.textContent = o; s.appendChild(opt); });
      s.addEventListener('change', updateNormalButtonState);
      g.appendChild(s);
      const err = document.createElement('div');
      err.className = 'form-error'; err.id = 'nfe-'+f.name;
      g.appendChild(err);
    } else {
      const inp = document.createElement('input');
      inp.type = 'number'; inp.className = 'form-input'; inp.id = 'nf-'+f.name;
      inp.min = f.min; inp.max = f.max; inp.step = f.step || 1; inp.placeholder = f.placeholder || f.min + '-' + f.max;
      inp.dataset.min = f.min; inp.dataset.max = f.max;
      inp.addEventListener('input', updateNormalButtonState);
      g.appendChild(inp);
      const err = document.createElement('div');
      err.className = 'form-error'; err.id = 'nfe-'+f.name;
      g.appendChild(err);
    }
    c.appendChild(g);
    setupTooltip(info);
  });
  updateNormalButtonState();
}


// 9. VALIDATION UNIVERSELLE DE TOUS LES CHAMPS
function validateFieldValue(name, value) {
  const v = value.trim();
  if (!v) return null;
  const guide = columnGuideMap[name];
  if (!guide) return null;
  if (guide.type === 'select') {
    if (guide.options && guide.options.length && !guide.options.includes(v)) {
      return t('err_invalid_option');
    }
    return null;
  }
  const num = parseFloat(v);
  if (isNaN(num)) return t('err_number');
  if (guide.min !== undefined && num < guide.min) return t('err_min_max', {min: guide.min, max: guide.max});
  if (guide.max !== undefined && num > guide.max) return t('err_min_max', {min: guide.min, max: guide.max});
  return null;
}

function validateAndShowField(prefix, name) {
  const el = document.getElementById(prefix + '-' + name);
  const errEl = document.getElementById(prefix + 'e-' + name);
  if (!el) return true;
  const val = el.value.trim();
  if (!val) {
    el.classList.remove('invalid');
    if (errEl) { errEl.textContent = ''; errEl.classList.remove('show'); }
    return false;
  }
  const error = validateFieldValue(name, val);
  if (error) {
    el.classList.add('invalid');
    if (errEl) { errEl.textContent = error; errEl.classList.add('show'); }
    return false;
  }
  el.classList.remove('invalid');
  if (errEl) { errEl.textContent = ''; errEl.classList.remove('show'); }
  return true;
}

const NORMAL_FIELDS = ['OverallQual','GrLivArea','YearBuilt','TotalBsmtSF','LotArea','BedroomAbvGr','Totalbath','Fireplaces','KitchenQual','CentralAir'];

function updateNormalButtonState() {
  const btn = document.getElementById('predictNormalBtn');
  const allValid = NORMAL_FIELDS.every(n => validateAndShowField('nf', n));
  btn.disabled = !allValid;
  btn.title = allValid ? '' : t('field_invalid');
}

function setupTooltip(el) {
  el.addEventListener('mouseenter', (e) => {
    const tip = el.dataset.tip;
    if (!tip) return;
    const existing = document.querySelector('.info-tooltip');
    if (existing) existing.remove();
    const t2 = document.createElement('div');
    t2.className = 'info-tooltip show';
    t2.textContent = tip;
    const rect = el.getBoundingClientRect();
    t2.style.left = Math.min(rect.left, window.innerWidth - 300) + 'px';
    t2.style.top = (rect.bottom + 8) + 'px';
    document.body.appendChild(t2);
  });
  el.addEventListener('mouseleave', () => {
    document.querySelectorAll('.info-tooltip').forEach(t2 => t2.remove());
  });
}


// 11. PREDICTION EXPRESS (predictNormal)
function getNormalFeatures() {
  const fields = ['OverallQual','GrLivArea','YearBuilt','TotalBsmtSF','LotArea','BedroomAbvGr','Totalbath','Fireplaces','KitchenQual','CentralAir'];
  const f = {};
  fields.forEach(n => {
    const el = document.getElementById('nf-'+n);
    if (!el) return;
    if (el.tagName === 'SELECT') f[n] = el.value || null;
    else {
      const v = el.value.trim();
      f[n] = v !== '' ? parseFloat(v) : null;
    }
  });
  return f;
}

function getCookie(name) {
  const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return m ? decodeURIComponent(m[2]) : '';
}

async function predictNormal() {
  const btn = document.getElementById('predictNormalBtn');
  const result = document.getElementById('normalResult');
  const price = document.getElementById('normalPrice');
  const meta = document.getElementById('normalMeta');
  const features = getNormalFeatures();
  const invalid = NORMAL_FIELDS.filter(n => !validateAndShowField('nf', n));
  if (invalid.length > 0) {
    const names = invalid.map(n => getLabel(columnGuideMap[n]) || n);
    result.className = 'result-card show error';
    price.innerHTML = '';
    meta.innerHTML = '<div class="error-text">' + t('error_fields_invalid') + '<br>' + names.join('<br>') + '</div>';
    return;
  }
  btn.disabled = true; btn.innerHTML = '<span class="loading-text"><span class="spinner"></span>' + t('loading') + '</span>';
  result.className = 'result-card';
  try {
    const res = await fetch(API + '/predict/normal', {
      method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':getCookie('csrf_token')},
      body:JSON.stringify({model:selectedModel,features}),
      credentials:'same-origin'
    });
    if (res.status === 401) { window.location.href = '/login'; return; }
    let data;
    try { data = await res.json(); } catch { data = { detail: 'Erreur serveur (HTTP ' + res.status + ')' }; }
    if (!res.ok) throw new Error(extractErrorDetail(data));
    result.className = 'result-card show success';
    price.textContent = '$' + Number(data.prediction).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
    meta.textContent = t('result_model', {model: data.model.toUpperCase()}) + ' | ' + new Date().toLocaleString(t('date_locale'));
    incrementCount();
  } catch(e) {
    result.className = 'result-card show error';
    price.innerHTML = ''; meta.innerHTML = '<div class="error-text">' + e.message + '</div>';
  } finally {
    btn.disabled = false; btn.textContent = t('btn_estimate');
  }
}

function resetNormal() {
  ['OverallQual','GrLivArea','YearBuilt','TotalBsmtSF','LotArea','BedroomAbvGr','Totalbath','Fireplaces'].forEach(n => {
    const el = document.getElementById('nf-'+n); if (el) el.value = '';
  });
  ['KitchenQual','CentralAir'].forEach(n => {
    const el = document.getElementById('nf-'+n); if (el) el.value = '';
  });
  document.getElementById('normalResult').className = 'result-card';
}


// 13. GESTION DE L'UPLOAD CSV
function setupUpload() {
  const zone = document.getElementById('uploadZone');
  const input = document.getElementById('csvInput');
  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => { e.preventDefault(); zone.classList.remove('dragover'); if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; handleFile(e.dataTransfer.files[0]); } });
  input.addEventListener('change', () => { if (input.files.length) handleFile(input.files[0]); });
}

async function handleFile(file) {
  const preview = document.getElementById('uploadPreview');
  if (!file.name.endsWith('.csv')) {
    preview.className = 'upload-preview show error'; preview.textContent = t('error_csv_format');
    csvData = null; csvFileObj = null; csvColCount = 0;
    updateCsvButton();
    return;
  }
  preview.className = 'upload-preview show';
  preview.textContent = t('reading_file', {name: file.name});
  csvFileObj = file;
  csvData = await file.text();
  const lines = csvData.trim().split('\n');
  csvColCount = lines[0].split(',').length;
  const rowCount = lines.length - 1;
  const colInfo = t('csv_columns_info', {cols: csvColCount});
  preview.textContent = t('csv_preview', {name: file.name, rows: rowCount, cols: csvColCount}) + ' | ' + colInfo;
  updateCsvButton();
}

function updateCsvButton() {
  const predictBtn = document.getElementById('predictCsvBtn');
  const cleanBtn = document.getElementById('cleanCsvBtn');
  const hint = document.getElementById('uploadHint');

  predictBtn.style.display = 'inline-flex';
  cleanBtn.style.display = 'inline-flex';
  cleanBtn.disabled = false;

  if (!csvData) {
    predictBtn.disabled = true;
    predictBtn.title = t('upload_hint_clean');
    cleanBtn.title = '';
    if (hint) hint.textContent = t('upload_hint_clean');
    return;
  }

  if (csvColCount < 161) {
    predictBtn.disabled = true;
    predictBtn.title = t('csv_needs_cleaning', {cols: csvColCount});
    if (hint) hint.textContent = t('csv_needs_cleaning', {cols: csvColCount});
  } else {
    predictBtn.disabled = false;
    predictBtn.title = '';
    if (hint) hint.textContent = t('csv_ready', {cols: csvColCount});
  }
}

async function predictCsv() {
  const btn = document.getElementById('predictCsvBtn');
  const result = document.getElementById('csvResult');
  if (!csvData) return;

  // Verifier que le CSV a bien 161 colonnes (fichier nettoye)
  if (csvColCount < 161) {
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">Ce fichier contient ' + csvColCount + ' colonnes. Les predictions necessitent un fichier nettoye (161 colonnes). Utilisez "Nettoyer les donnees" d\'abord.</div>';
    return;
  }

  btn.disabled = true; btn.innerHTML = '<span class="loading-text"><span class="spinner"></span>' + t('loading_csv') + '</span>';
  result.className = 'result-card';
  const formData = new FormData();
  formData.append('file', new Blob([csvData], {type:'text/csv'}), 'data.csv');
  formData.append('model', selectedModel);
  try {
    const res = await fetch(API + '/predict/csv', {
      method:'POST', headers:{'X-CSRF-Token':getCookie('csrf_token')},
      body:formData,
      credentials:'same-origin'
    });
    if (res.status === 401) { window.location.href = '/login'; return; }
    if (!res.ok) {
      const err = await res.json().catch(()=>({detail:t('error_unknown')}));
      throw new Error(extractErrorDetail(err));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'predictions.csv';
    a.click();
    URL.revokeObjectURL(url);
    result.className = 'result-card show success';
    result.innerHTML = '<div class="result-label">' + t('csv_success') + '</div><div class="result-detail">' + t('csv_success_desc') + '</div>';
    incrementCount();
  } catch(e) {
    result.className = 'result-card show error';
    result.innerHTML = '<div class="error-text">' + e.message + '</div>';
  } finally {
    btn.disabled = false;
    updateCsvButton();
  }
}


// 14. REDIRECTION VERS LA PAGE DE NETTOYAGE
function redirectToCleaning() {
  if (csvFileObj && csvData) {
    sessionStorage.setItem('pendingCleaningCSV', csvData);
    sessionStorage.setItem('pendingCleaningName', csvFileObj.name);
  }
  window.location.href = '/static/cleaning.html';
}


// POINT D'ENTREE
document.addEventListener('DOMContentLoaded', init);
