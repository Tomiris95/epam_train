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
    hasSpecial: /[!@#$%^&*(),.?":{}|<>\[\]\\/\\\\_\-+=~`;:]/,
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
    error: 'Phone number must be in international format, e.g. +14155552671'
  }
};

function validateEmail(email, rule = DEFAULT_RULES.email) {
  const errors = [];
  if (email === null || email === undefined || String(email).trim() === '') {
    errors.push('Email is required');
    return { valid: false, errors };
  }

  if (!rule.regex.test(String(email).trim())) {
    errors.push(rule.error);
  }

  return { valid: errors.length === 0, errors };
}

function validatePassword(password, rule = DEFAULT_RULES.password) {
  const errors = [];
  const pwd = password === null || password === undefined ? '' : String(password);

  if (pwd.length === 0) {
    errors.push('Password is required');
    return { valid: false, errors };
  }

  if (pwd.length < rule.minLength) errors.push(rule.errors.length);
  if (!rule.hasNumber.test(pwd)) errors.push(rule.errors.number);
  if (!rule.hasSpecial.test(pwd)) errors.push(rule.errors.special);

  return { valid: errors.length === 0, errors };
}

function validatePhone(phone, rule = DEFAULT_RULES.phone) {
  const errors = [];
  if (phone === null || phone === undefined || String(phone).trim() === '') {
    errors.push('Phone number is required');
    return { valid: false, errors };
  }

  // Normalize: remove spaces, hyphens, parentheses
  const normalized = String(phone).replace(/[\s()-]/g, '');
  if (!rule.regex.test(normalized)) {
    errors.push(rule.error);
  }

  return { valid: errors.length === 0, errors };
}

function validateAll({ email, password, phone }, rules = DEFAULT_RULES) {
  const result = {
    email: validateEmail(email, rules.email),
    password: validatePassword(password, rules.password),
    phone: validatePhone(phone, rules.phone)
  };

  const valid = result.email.valid && result.password.valid && result.phone.valid;
  const errors = [];
  Object.values(result).forEach(r => errors.push(...r.errors));

  return { valid, errors, details: result };
}

module.exports = { validateEmail, validatePassword, validatePhone, validateAll, DEFAULT_RULES };
