/* validation.js
 * Modern JS (ES6+) style, CommonJS exports for test compatibility
 * Exports: validateEmail, validatePassword, validatePhone, validateAll
 */

const DEFAULT_RULES = {
  email: {
    name: 'email_format',
    regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    error: 'Invalid email format. Expected e.g. user@example.com'
  },
  password: {
    minLength: 8,
    hasNumber: /\d/,
    hasSpecial: /[!@#$%^&*(),.?":{}|<>\[\]\/\\_\-+=~`;:]/,
    errors: {
      length: 'Password must be at least 8 characters long',
      number: 'Password must contain at least one number',
      special: 'Password must contain at least one special character'
    }
  },
  phone: {
    // E.164-ish: country code + national number, 7-15 digits total (excluding +)
    name: 'phone_international',
    regex: /^\+?[1-9]\d{6,14}$/, 
    error: 'Phone number must be in international format, e.g. +14155552777'
  }
};

// Active rules in use (defaults to DEFAULT_RULES, can be replaced by DB-loaded rules)
let CURRENT_RULES = {
  email: { ...DEFAULT_RULES.email },
  password: { ...DEFAULT_RULES.password, errors: { ...DEFAULT_RULES.password.errors } },
  phone: { ...DEFAULT_RULES.phone }
};

function setRules(rules) {
  CURRENT_RULES = rules;
}

function getCurrentRules() {
  return CURRENT_RULES;
}

function validateEmail(email, rule) {
  const r = rule || CURRENT_RULES.email;
  const errors = [];
  if (email === null || email === undefined || String(email).trim() === '') {
    errors.push('Email is required');
    return { valid: false, errors };
  }

  if (!r.regex.test(String(email).trim())) {
    errors.push(r.error);
  }

  return { valid: errors.length === 0, errors };
} 

function validatePassword(password, rule) {
  const r = rule || CURRENT_RULES.password;
  const errors = [];
  const pwd = password === null || password === undefined ? '' : String(password);

  if (pwd.length === 0) {
    errors.push('Password is required');
    return { valid: false, errors };
  }

  if (pwd.length < r.minLength) errors.push(r.errors.length);
  if (!r.hasNumber.test(pwd)) errors.push(r.errors.number);
  if (!r.hasSpecial.test(pwd)) errors.push(r.errors.special);

  return { valid: errors.length === 0, errors };
} 

function validatePhone(phone, rule) {
  const r = rule || CURRENT_RULES.phone;
  const errors = [];
  if (phone === null || phone === undefined || String(phone).trim() === '') {
    errors.push('Phone number is required');
    return { valid: false, errors };
  }

  // Normalize: remove spaces, hyphens, parentheses
  const normalized = String(phone).replace(/[\s()-]/g, '');
  if (!r.regex.test(normalized)) {
    errors.push(r.error);
  }

  return { valid: errors.length === 0, errors };
} 

function validateAll({ email, password, phone }, rules) {
  const r = rules || CURRENT_RULES;
  const result = {
    email: validateEmail(email, r.email),
    password: validatePassword(password, r.password),
    phone: validatePhone(phone, r.phone)
  };

  const valid = result.email.valid && result.password.valid && result.phone.valid;
  const errors = [];
  Object.values(result).forEach(res => errors.push(...res.errors));

  return { valid, errors, details: result };
}

// --- DB-backed rules loader -------------------------------------------------
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Attempt to read rules synchronously from the SQL seed file so
// validators use DB-seeded messages immediately (useful for tests)
function loadRulesFromSqlFileSync(sqlPath = path.join(__dirname, 'validation_rules.sql')) {
  try {
    const txt = fs.readFileSync(sqlPath, 'utf8');

    // phone_international
    const phoneMatch = txt.match(/\('phone_international',\s*'([^']*)',\s*'([^']*)'\)/);
    if (phoneMatch) {
      try {
        CURRENT_RULES.phone.regex = new RegExp(phoneMatch[1].replace(/\\\\/g, '\\'));
      } catch (e) {
        // ignore invalid regex in seed
      }
      CURRENT_RULES.phone.error = phoneMatch[2];
    }

    // email_format
    const emailMatch = txt.match(/\('email_format',\s*'([^']*)',\s*'([^']*)'\)/);
    if (emailMatch) {
      try {
        CURRENT_RULES.email.regex = new RegExp(emailMatch[1].replace(/\\\\/g, '\\'));
      } catch (e) {}
      CURRENT_RULES.email.error = emailMatch[2];
    }

    // password_min_length
    const pwdLenMatch = txt.match(/\('password_min_length',\s*(NULL|'([^']*)'),\s*'([^']*)'\)/);
    if (pwdLenMatch) {
      // try to parse numeric min length from message
      const msg = pwdLenMatch[3];
      const m = msg && msg.match(/(\d+)/);
      if (m) CURRENT_RULES.password.minLength = parseInt(m[1], 10);
      CURRENT_RULES.password.errors.length = msg;
    }
  } catch (e) {
    // ignore; keep defaults
  }
}

// Load seed file synchronously at module init so tests get DB-like messages
loadRulesFromSqlFileSync();

function loadRulesFromDb(dbPath = path.join(__dirname, 'validation_rules.db')) {
  return new Promise((resolve, reject) => {
    const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) return reject(err);
    });

    db.all('SELECT rule_name, regex_pattern, error_message FROM validation_rules', [], (err, rows) => {
      if (err) {
        db.close();
        return reject(err);
      }

      // Start from defaults and override any values from DB
      const rules = {
        email: { ...DEFAULT_RULES.email },
        password: { ...DEFAULT_RULES.password, errors: { ...DEFAULT_RULES.password.errors } },
        phone: { ...DEFAULT_RULES.phone }
      };

      rows.forEach(r => {
        const name = r.rule_name;
        const pattern = r.regex_pattern;
        const msg = r.error_message;

        if (name === 'email_format') {
          if (pattern) {
            try { rules.email.regex = new RegExp(pattern.replace(/\\\\/g, '\\')); } catch (e) {}
          }
          if (msg) rules.email.error = msg;
        } else if (name === 'phone_international') {
          if (pattern) {
            try { rules.phone.regex = new RegExp(pattern.replace(/\\\\/g, '\\')); } catch (e) {}
          }
          if (msg) rules.phone.error = msg;
        } else if (name === 'password_has_number') {
          if (pattern) {
            try { rules.password.hasNumber = new RegExp(pattern.replace(/\\\\/g, '\\')); } catch (e) {}
          }
          if (msg) rules.password.errors.number = msg;
        } else if (name === 'password_has_special') {
          if (pattern) {
            try { rules.password.hasSpecial = new RegExp(pattern.replace(/\\\\/g, '\\')); } catch (e) {}
          }
          if (msg) rules.password.errors.special = msg;
        } else if (name === 'password_min_length') {
          // try to parse numeric min length from pattern or message
          let min = null;
          if (pattern) {
            const parsed = parseInt(pattern, 10);
            if (!Number.isNaN(parsed)) min = parsed;
          }
          if (min === null && msg) {
            const m = msg.match(/(\d+)/);
            if (m) min = parseInt(m[1], 10);
          }
          if (min !== null) rules.password.minLength = min;
          if (msg) rules.password.errors.length = msg;
        }
      });

      db.close(() => resolve(rules));
    });
  });
}

function validateAllFromDb(data, dbPath) {
  return loadRulesFromDb(dbPath).then(rules => validateAll(data, rules));
}

function applyRulesFromDb(dbPath) {
  return loadRulesFromDb(dbPath).then(rules => {
    setRules(rules);
    return rules;
  });
}

// Try to load DB rules on module load (non-fatal)
applyRulesFromDb().catch(err => {
  // Not fatal: keep using defaults until user calls applyRulesFromDb explicitly
  // console.warn('Could not load validation rules from DB:', err.message);
});

module.exports = { validateEmail, validatePassword, validatePhone, validateAll, DEFAULT_RULES, loadRulesFromDb, validateAllFromDb, applyRulesFromDb, setRules, getCurrentRules };

