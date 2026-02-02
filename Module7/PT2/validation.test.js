/* Jest tests for validation module
 * Covers valid, invalid and edge cases (10+ tests)
 */
const { validateEmail, validatePassword, validatePhone, validateAll } = require('./validation');

describe('validateEmail', () => {
  test('valid email', () => {
    expect(validateEmail('user@example.com')).toEqual({ valid: true, errors: [] });
  });

  test('invalid email missing @', () => {
    expect(validateEmail('userexample.com').valid).toBe(false);
  });

  test('empty email string', () => {
    const res = validateEmail('');
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('Email is required');
  });
});

describe('validatePassword', () => {
  test('valid password', () => {
    const res = validatePassword('P@ssw0rd123');
    expect(res.valid).toBe(true);
  });

  test('password too short', () => {
    const res = validatePassword('P@ss1');
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('Password must be at least 8 characters long');
  });

  test('password missing number', () => {
    const res = validatePassword('P@ssword!');
    expect(res.errors).toContain('Password must contain at least one number');
  });

  test('password missing special char', () => {
    const res = validatePassword('Passw0rd1');
    expect(res.errors).toContain('Password must contain at least one special character');
  });

  test('null password', () => {
    const res = validatePassword(null);
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('Password is required');
  });
});

describe('validatePhone', () => {
  test('valid E.164 phone', () => {
    expect(validatePhone('+14155552671')).toEqual({ valid: true, errors: [] });
  });

  test('phone with spaces and hyphens', () => {
    expect(validatePhone('+1 415-555-2671').valid).toBe(true);
  });

  test('invalid phone missing + and too short', () => {
    const res = validatePhone('415');
    expect(res.valid).toBe(false);
    expect(res.errors).toContain('Phone number must be in international format, e.g. +14155552671');
  });

  test('validateAll combination', () => {
    const result = validateAll({ email: 'user@example.com', password: 'P@ssw0rd1', phone: '+14155552671' });
    expect(result.valid).toBe(true);
    expect(result.errors.length).toBe(0);
  });

  test('validateAll with multiple errors', () => {
    const result = validateAll({ email: 'bad', password: 'short', phone: '' });
    expect(result.valid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(2);
  });
});
