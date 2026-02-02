/* server.js
 * Simple Express server exposing /validation-rules and /validate
 */
const express = require('express');
const bodyParser = require('body-parser');
const { validateAll, DEFAULT_RULES } = require('./validation');

const app = express();
app.use(bodyParser.json());

// In-memory rules store (production: load from DB)
const rules = [
  { rule_name: 'email_format', regex_pattern: String(DEFAULT_RULES.email.regex), error_message: DEFAULT_RULES.email.error },
  { rule_name: 'password_min_length', regex_pattern: null, error_message: DEFAULT_RULES.password.errors.length },
  { rule_name: 'password_has_number', regex_pattern: String(DEFAULT_RULES.password.hasNumber), error_message: DEFAULT_RULES.password.errors.number },
  { rule_name: 'password_has_special', regex_pattern: String(DEFAULT_RULES.password.hasSpecial), error_message: DEFAULT_RULES.password.errors.special },
  { rule_name: 'phone_international', regex_pattern: String(DEFAULT_RULES.phone.regex), error_message: DEFAULT_RULES.phone.error }
];

app.get('/validation-rules', (req, res) => {
  res.json({ rules });
});

app.post('/validate', (req, res) => {
  const { email, password, phone } = req.body || {};
  if (req.headers['content-type'] && !req.is('application/json')) {
    return res.status(400).json({ error: 'Content-Type must be application/json' });
  }

  if (email === undefined && password === undefined && phone === undefined) {
    return res.status(400).json({ error: 'Request body must contain at least one of: email, password, phone' });
  }

  try {
    const result = validateAll({ email, password, phone });
    const status = result.valid ? 200 : 400;
    return res.status(status).json(result);
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`Validation service running on http://localhost:${port}`));
}

module.exports = app;
