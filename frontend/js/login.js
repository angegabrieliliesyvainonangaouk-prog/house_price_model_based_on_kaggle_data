const API = '/api/v1';
let fingerprintHash = '';

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const fp = await Fingerprint.generate();
    fingerprintHash = fp.hash;
  } catch (e) {
    fingerprintHash = 'fallback-' + navigator.userAgent.length;
  }

  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.auth;
      document.getElementById('loginForm').classList.toggle('active', target === 'login');
      document.getElementById('registerForm').classList.toggle('active', target === 'register');
      hideMessage();
    });
  });

  document.getElementById('loginForm').addEventListener('submit', handleLogin);
  document.getElementById('registerForm').addEventListener('submit', handleRegister);

  document.querySelectorAll('.legal-link').forEach(link => {
    link.addEventListener('click', () => {
      showLegal(link.dataset.legal);
    });
  });

  document.getElementById('modalCloseBtn').addEventListener('click', closeLegal);
});

function showMessage(text, type) {
  const el = document.getElementById('authMessage');
  el.textContent = text;
  el.className = 'auth-message show ' + type;
}

function hideMessage() {
  document.getElementById('authMessage').className = 'auth-message';
}

async function handleLogin(e) {
  e.preventDefault();
  hideMessage();
  const btn = document.getElementById('loginBtn');
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;
  if (!email || !password) return showMessage('Veuillez remplir tous les champs.', 'error');

  btn.disabled = true;
  btn.textContent = 'Connexion...';
  try {
    const res = await fetch(API + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Fingerprint': fingerprintHash },
      body: JSON.stringify({ email, password }),
      credentials: 'same-origin'
    });
    let data;
    try { data = await res.json(); } catch { data = { detail: 'Erreur serveur (HTTP ' + res.status + ')' }; }
    if (!res.ok) throw new Error(data.detail || 'Erreur de connexion');
    if (data.must_change_password) {
      showMessage('Connecte ! Veuillez modifier votre mot de passe.', 'success');
      setTimeout(() => showChangePasswordModal(), 1000);
      return;
    }
    window.location.href = '/';
  } catch (err) {
    showMessage(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Se connecter';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideMessage();
  const btn = document.getElementById('registerBtn');
  const email = document.getElementById('registerEmail').value.trim();
  const password = document.getElementById('registerPassword').value;
  const confirm = document.getElementById('registerPasswordConfirm').value;

  if (!email || !password) return showMessage('Veuillez remplir tous les champs.', 'error');
  if (password !== confirm) return showMessage('Les mots de passe ne correspondent pas.', 'error');
  if (password.length < 8) return showMessage('Le mot de passe doit faire au moins 8 caracteres.', 'error');
  if (!email.toLowerCase().endsWith('@gmail.com')) return showMessage('Seules les adresses Gmail sont acceptees pour l\'inscription.', 'error');

  btn.disabled = true;
  btn.textContent = 'Creation...';
  try {
    const res = await fetch(API + '/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Fingerprint': fingerprintHash },
      body: JSON.stringify({ email, password }),
      credentials: 'same-origin'
    });
    let data;
    try { data = await res.json(); } catch { data = { detail: 'Erreur serveur (HTTP ' + res.status + ')' }; }
    if (!res.ok) throw new Error(data.detail || 'Erreur lors de l\'inscription');
    showMessage('Compte cree ! Un e-mail de confirmation a ete envoye. Verifiez votre boite de reception puis connectez-vous.', 'success');
    setTimeout(() => {
      document.querySelectorAll('.auth-tab')[0].click();
    }, 3000);
  } catch (err) {
    showMessage(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Creer un compte';
  }
}

function showChangePasswordModal() {
  const overlay = document.getElementById('legalModal');
  document.getElementById('legalContent').innerHTML = `
    <h2>Modifier votre mot de passe</h2>
    <p class="change-pwd-desc">Vous etes connecte avec un mot de passe temporaire. Veuillez le changer maintenant.</p>
    <form id="changePwdForm">
      <div class="form-group">
        <label class="form-label">Mot de passe actuel (temporaire)</label>
        <input type="password" id="changeOldPwd" class="form-input" required>
      </div>
      <div class="form-group">
        <label class="form-label">Nouveau mot de passe</label>
        <input type="password" id="changeNewPwd" class="form-input" required minlength="8">
      </div>
      <div class="form-group">
        <label class="form-label">Confirmer le nouveau mot de passe</label>
        <input type="password" id="changeConfirmPwd" class="form-input" required minlength="8">
      </div>
      <button type="submit" class="btn btn-primary change-pwd-btn">Modifier le mot de passe</button>
    </form>
  `;
  overlay.classList.add('show');
  document.getElementById('changePwdForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const oldPwd = document.getElementById('changeOldPwd').value;
    const newPwd = document.getElementById('changeNewPwd').value;
    const confirm = document.getElementById('changeConfirmPwd').value;
    if (newPwd !== confirm) return showMessage('Les mots de passe ne correspondent pas.', 'error');
    if (newPwd.length < 8) return showMessage('Minimum 8 caracteres.', 'error');
    try {
      const res = await fetch(API + '/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCookie('csrf_token'),
          'X-Fingerprint': fingerprintHash
        },
        body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
        credentials: 'same-origin'
      });
      let data;
      try { data = await res.json(); } catch { data = { detail: 'Erreur serveur (HTTP ' + res.status + ')' }; }
      if (!res.ok) throw new Error(data.detail || 'Erreur');
      window.location.href = '/';
    } catch (err) {
      showMessage(err.message, 'error');
    }
  });
}

function getCookie(name) {
  const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return m ? decodeURIComponent(m[2]) : '';
}

const LEGAL_CONTENT = {
  mentions: `
    <h2>Mentions Legales</h2>
    <h3>1. Editeur du site</h3>
    <p><strong>Nom :</strong> thecreator</p>
    <p><strong>E-mail :</strong> obsedereussite@gmail.com</p>
    <h3>2. Hebergeur</h3>
    <p>Ce site est heberge sur des infrastructures cloud containerisees (Docker).</p>
    <h3>3. Propriete intellectuelle</h3>
    <p>L'ensemble du contenu de ce site (textes, images, graphismes, logo, icons, code source) est la propriete exclusive de thecreator, sauf mention contraire. Toute reproduction, representation, modification, publication, transmission, denaturation du site ou de son contenu, par quel que moyen que ce soit, est interdite sans autorisation prealable ecrite.</p>
    <h3>4. Donnees personnelles</h3>
    <p>Les donnees collectees (adresse e-mail, empreinte numerique) sont utilisees uniquement pour l'authentification et la securisation du service. Elles ne sont jamais transmises a des tiers. Conformement au RGPD, vous disposez d'un droit d'acces, de rectification et de suppression de vos donnees en contactant obsedereussite@gmail.com.</p>
    <h3>5. Cookies</h3>
    <p>Ce site utilise des cookies strictement necessaires au fonctionnement (cookies de session authentifiee, cookies CSRF). Aucun cookie publicitaire ou de suivi n'est utilise.</p>
  `,
  cgu: `
    <h2>Conditions d'Utilisation</h2>
    <h3>1. Objet</h3>
    <p>Les presentes conditions generales d'utilisation (CGU) regissent l'utilisation du service ML Predictor Pro, outil d'estimation immobiliere base sur l'intelligence artificielle.</p>
    <h3>2. Acceptation</h3>
    <p>L'inscription et l'utilisation du service impliquent l'acceptation sans reserve des presentes CGU.</p>
    <h3>3. Description du service</h3>
    <p>ML Predictor Pro propose une estimation du prix d'un bien immobilier basee sur des modeles de machine learning (XGBoost, CatBoost). Le service comprend :</p>
    <ul>
      <li>Un mode Express avec estimation rapide (10 criteres)</li>
      <li>Un mode CSV pour les predictions par lots</li>
      <li>Un service de nettoyage de donnees CSV</li>
    </ul>
    <h3>4. Limitation de responsabilite</h3>
    <p><strong>Les estimations fournies par le service sont indicatives et ne constituent en aucun cas une expertise immobiliere officielle.</strong> Les resultats dependent de la qualite des donnees saisies et des modeles utilises. thecreator ne saurait etre tenu responsable de decisions prises sur la base de ces estimations.</p>
    <h3>5. Obligations de l'utilisateur</h3>
    <ul>
      <li>Fournir des informations exactes lors de l'inscription</li>
      <li>Ne pas tenter de contourner les mesures de securite</li>
      <li>Ne pas utiliser le service a des fins frauduleuses</li>
      <li>Respecter la limite de predictions quotidiennes (20/jour)</li>
    </ul>
    <h3>6. Suspension</h3>
    <p>theclient se reserve le droit de suspendre tout compte en cas de manquement aux presentes CGU ou d'utilisation abusive du service.</p>
    <h3>7. Modification</h3>
    <p>thecreator se reserve le droit de modifier les presentes CGU a tout moment. Les utilisateurs seront informes de tout changement substantiel.</p>
  `,
  privacy: `
    <h2>Politique de Confidentialite</h2>
    <h3>1. Donnees collectees</h3>
    <p>Le service collecte les donnees suivantes :</p>
    <ul>
      <li><strong>Adresse e-mail :</strong> utilisee pour l'authentification et l'envoi du mot de passe initial</li>
      <li><strong>Hash du mot de passe :</strong> stocke de facon irreversible (bcrypt)</li>
      <li><strong>Empreinte numerique (fingerprint) :</strong> generee cote client a partir de caracteristiques du navigateur, stockee sous forme de hash SHA-256. Utilisee uniquement pour la securisation anti-fraude</li>
      <li><strong>Adresse IP :</strong> utilisee pour la limitation de debit (rate limiting)</li>
      <li><strong>Donnees d'inscription immobiliere :</strong> saisies par l'utilisateur pour les previsions, non stockees de facon permanente</li>
    </ul>
    <h3>2. Finalite</h3>
    <p>Les donnees sont collectees pour :</p>
    <ul>
      <li>L'authentification et la gestion des comptes</li>
      <li>La securisation du service contre les abus</li>
      <li>La limitation de l'utilisation (rate limiting)</li>
      <li>L'amelioration des modeles de prediction</li>
    </ul>
    <h3>3. Base legale</h3>
    <p>Le traitement est fonde sur :</p>
    <ul>
      <li>L'execution du contrat (fourniture du service)</li>
      <li>Le legitime interet (securisation contre les abus)</li>
      <li>Le consentement (inscription volontaire)</li>
    </ul>
    <h3>4. Conservation</h3>
    <p>Les donnees de compte sont conservees tant que le compte est actif. Les donnees de prediction ne sont pas stockees. Les logs de connexion sont conserves 30 jours.</p>
    <h3>5. Droits</h3>
    <p>Conformement au RGPD, vous disposez des droits suivants :</p>
    <ul>
      <li>Droit d'acces a vos donnees personnelles</li>
      <li>Droit de rectification</li>
      <li>Droit de suppression (droit a l'oubli)</li>
      <li>Droit a la portabilite</li>
      <li>Droit d'opposition au traitement</li>
    </ul>
    <p>Pour exercer ces droits : obsedereussite@gmail.com</p>
    <h3>6. Securite</h3>
    <p>Les donnees sont protegees par :</p>
    <ul>
      <li>Mots de passe hashes avec bcrypt</li>
      <li>Tokens JWT signes stockes en cookies HttpOnly</li>
      <li>Protection CSRF par double soumission</li>
      <li>En-tetes de securite (CSP, XSS Protection)</li>
      <li>Chiffrement TLS en transit</li>
    </ul>
  `,
  rgpd: `
    <h2>Reglement General sur la Protection des Donnees (RGPD)</h2>
    <h3>1. Responsable du traitement</h3>
    <p><strong>thecreator</strong><br>Contact : obsedereussite@gmail.com</p>
    <h3>2. Donnees traitees</h3>
    <table class="rgpd-table">
      <tr class="rgpd-row"><td class="rgpd-cell">Donnee</td><td class="rgpd-cell">Finalite</td><td class="rgpd-cell">Base legale</td><td class="rgpd-cell">Conservation</td></tr>
      <tr class="rgpd-row"><td class="rgpd-cell">E-mail</td><td class="rgpd-cell">Authentification</td><td class="rgpd-cell">Contrat</td><td class="rgpd-cell">Duree du compte</td></tr>
      <tr class="rgpd-row"><td class="rgpd-cell">Hash mot de passe</td><td class="rgpd-cell">Authentification</td><td class="rgpd-cell">Contrat</td><td class="rgpd-cell">Duree du compte</td></tr>
      <tr class="rgpd-row"><td class="rgpd-cell">Fingerprint hash</td><td class="rgpd-cell">Securite anti-fraude</td><td class="rgpd-cell">Legitime interet</td><td class="rgpd-cell">Duree du compte</td></tr>
      <tr class="rgpd-row"><td class="rgpd-cell">Adresse IP</td><td class="rgpd-cell">Rate limiting</td><td class="rgpd-cell">Legitime interet</td><td class="rgpd-cell">30 jours</td></tr>
      <tr><td class="rgpd-cell">Donnees immo</td><td class="rgpd-cell">Prediction</td><td class="rgpd-cell">Contrat</td><td class="rgpd-cell">Non stockees</td></tr>
    </table>
    <h3>3. Vos droits</h3>
    <p>Vous disposez des droits suivants :</p>
    <ul>
      <li><strong>Droit d'acces (art. 15) :</strong> obtenir une copie de vos donnees</li>
      <li><strong>Droit de rectification (art. 16) :</strong> corriger des donnees inexactes</li>
      <li><strong>Droit a l'effacement (art. 17) :</strong> demander la suppression de vos donnees</li>
      <li><strong>Droit a la limitation (art. 18) :</strong> limiter le traitement</li>
      <li><strong>Droit a la portabilite (art. 20) :</strong> recevoir vos donnees dans un format structure</li>
      <li><strong>Droit d'opposition (art. 21) :</strong> vous opposer au traitement pour motif legitime</li>
    </ul>
    <h3>4. Exercer vos droits</h3>
    <p>Pour exercer l'un de ces droits, contactez-nous a : <strong>obsedereussite@gmail.com</strong></p>
    <p>Nous repondrons dans un delai de 30 jours.</p>
    <h3>5. Transferts</h3>
    <p>Aucun transfert de donnees en dehors de l'Union europeenne n'est effectue.</p>
    <h3>6. Reclamation</h3>
    <p>En cas de reclamation, vous pouvez adresser une plainte a la CNIL : <a href="https://www.cnil.fr" target="_blank">www.cnil.fr</a></p>
  `
};

function showLegal(key) {
  document.getElementById('legalContent').innerHTML = LEGAL_CONTENT[key] || '';
  document.getElementById('legalModal').classList.add('show');
}

function closeLegal() {
  document.getElementById('legalModal').classList.remove('show');
}

document.getElementById('legalModal').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeLegal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeLegal();
});
