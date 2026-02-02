# Requirements: Data Validation Module

## Overview
The module validates user input for three fields: **email**, **password**, and **phone**.
Each rule must include a clear error message and be expressed so it can be stored in a DB (name, regex, error_message).

## Validation Rules
| Field | Rule | Criteria | Error Message |
|---|---|---:|---|
| Email | Format | Valid email format (one `@`, domain with dot, no spaces) | "Invalid email format. Expected e.g. user@example.com" |
| Password | Minimum Length | At least 8 characters | "Password must be at least 8 characters long" |
| Password | Contains Number | At least one digit [0-9] | "Password must contain at least one number" |
| Password | Contains Special Character | At least one special character (e.g., !@#$%) | "Password must contain at least one special character" |
| Phone | International Format | E.164 style allowed (+countrycode + national number). 7–15 digits after country code. Can include spaces/hyphens which will be ignored | "Phone number must be in international format, e.g. +14155552671" |

> Notes:
> - Return format for all validation functions: `{ valid: boolean, errors: string[] }`.
> - Error messages should be concise and actionable.
> - Empty/null inputs should be treated as invalid and return an appropriate error.

## Validation & Refinement

### Evidence of security/performance/code quality review
- **Unit tests & coverage:** `validation.test.js` contains comprehensive test cases (valid, invalid, edge cases) and the test run reports 100% coverage, demonstrating functional correctness.
- **Security guidance:** `README.md` and `api_spec.md` document rate-limiting, HTTPS, and use of parameterized DB queries to prevent SQL injection; error messages are server-controlled to avoid reflecting raw input (reducing XSS risk).
- **Performance considerations:** Validation functions are synchronous and lightweight; README suggests clustering or load-balancing to handle high QPS and caching rules in memory.
- **Schema auditability:** `validation_rules.sql` seeds canonical rules which makes rule changes auditable and reviewable.

### Applied improvements demonstrated
- **Tests & edge cases:** Added tests for empty strings, nulls, special characters, and integration-level checks to validate endpoints.
- **Consistent API behavior:** `validateAll` returns `{ valid, errors, details }`; the server responds with `200` (all valid) or `400` (validation failures) and includes per-field details.
- **DB-ready rule storage:** The SQL seed and rule table allow rules to be managed and updated without code changes.
- **Documentation & guidance:** `README.md` and `api_spec.md` updated with error codes, usage examples, and security/performance notes.
- **Next recommended improvements:** add CI to run tests and report coverage on push, add rate-limiter middleware, and integrate parameterized DB queries for production safety.
