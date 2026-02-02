# Validation Module

## Overview ✅
A compact validation service for user input: **email**, **password**, and **phone**. The project includes a small validation library (`validation.js`), an example Express server (`server.js`), a SQL schema for rule storage (`validation_rules.sql`), and comprehensive Jest tests.

---

## Installation 🔧
Prerequisites:
- Node.js 16+ (or compatible LTS)

Install dependencies:
```bash
npm install
```

Run the server locally:
```bash
npm start
```

Run tests and see coverage:
```bash
npm test
```

---

## Usage Examples 💡
Validate via HTTP (cURL):
```bash
curl -X POST http://localhost:3000/validate \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"P@ssw0rd1","phone":"+14155552671"}'
```
Response (success):
```json
{ "valid": true, "errors": [], "details": { ... } }
```

Get available validation rules:
```bash
curl http://localhost:3000/validation-rules
```

---

## API Endpoints 🔌
### GET /validation-rules
- Returns: `200` with JSON body `{ rules: [ { rule_name, regex_pattern, error_message }, ... ] }`.
- Errors: `500` if rules cannot be loaded.

### POST /validate
- Accepts JSON body containing any of: `email`, `password`, `phone`.
- Example request:
```json
{ "email": "user@example.com", "password": "P@ssw0rd1", "phone": "+14155552671" }
```
- Success response (all valid): `200`
```json
{
  "valid": true,
  "errors": [],
  "details": {
    "email": { "valid": true, "errors": [] },
    "password": { "valid": true, "errors": [] },
    "phone": { "valid": true, "errors": [] }
  }
}
```
- Validation failure: `400` with `valid: false`, aggregated `errors` array and per-field `details`.
- Other errors: `400` for malformed requests, `500` for server errors.

---

## Error Codes & Messages ❗
- `400 Bad Request` — malformed JSON, missing all fields, or validation failures. Example validation error: `Password must contain at least one number`.
- `500 Internal Server Error` — database or unexpected server error.

---

## Example Code 🧩
Use validation functions directly in Node.js (synchronous, test-friendly):
```js
const { validateAll } = require('./validation');

const result = validateAll({
  email: 'user@example.com',
  password: 'P@ssw0rd1',
  phone: '+14155552671'
});

console.log(result);
// { valid: true, errors: [], details: { ... } }
```

Example using fetch to call the API:
```js
fetch('http://localhost:3000/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com', password: 'P@ssw0rd1' })
}).then(r => r.json()).then(console.log);
```

---

## Notes & Best Practices ✅
- Store rules in DB (`validation_rules` table) and cache them in memory for performance.
- Use parameterized queries when integrating with DB to avoid SQL injection.
- Protect `/validate` with rate limiting and authentication in production.
- Consider adding TypeScript types for larger codebases.

---

## Files 🔍
- `validation.js` — core validation functions (`validateEmail`, `validatePassword`, `validatePhone`, `validateAll`).
- `validation_rules.sql` — schema + seed data for `validation_rules` table.
- `server.js` — example Express API using the validation module.
- `validation.test.js` — Jest unit tests.
- `validation.integration.test.js` — (optional) integration tests using Supertest.

---

## License
MIT

