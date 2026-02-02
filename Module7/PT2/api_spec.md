# API Specification: Validation Service

## Overview
Provides validation for user-provided email, password, and phone using stored rules.

## Endpoints

### GET /validation-rules
- Description: Returns all validation rules (name, regex, error_message).
- Response 200 JSON:
  {
    "rules": [
      { "rule_name": "email_format", "regex_pattern": "...", "error_message": "..." },
      ...
    ]
  }

### POST /validate
- Description: Validates the provided payload and returns results per field.
- Request JSON body:
  {
    "email": "user@example.com",
    "password": "P@ssword123",
    "phone": "+14155552671"
  }

- Response 200 JSON (all ok):
  {
    "valid": true,
    "errors": [],
    "details": {
      "email": { "valid": true, "errors": [] },
      "password": { "valid": true, "errors": [] },
      "phone": { "valid": true, "errors": [] }
    }
  }

- Response 400 JSON (validation failed):
  {
    "valid": false,
    "errors": ["Password must contain at least one number"],
    "details": { ... }
  }

## Error Codes
- 400 Bad Request: malformed JSON or missing fields
- 500 Internal Server Error: server-side error

## Notes
- The implementation returns rules from an in-memory source. A production service should fetch rules from a DB using the `validation_rules` table.
- Use HTTPS and rate limiting for production.
