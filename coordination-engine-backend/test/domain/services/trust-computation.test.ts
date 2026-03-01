import { computeTrustScore, getTrustLevel, getTrustFormulaVersion, TRUST_FORMULA_VERSION } from '../../../src/domain/services/trust-computation';

test('computeTrustScore returns 0 when acceptedMatches is 0', () => {
  expect(computeTrustScore(0, 0)).toBe(0);
  expect(computeTrustScore(5, 0)).toBe(0);
});

test('computeTrustScore correctly calculates trust score', () => {
  expect(computeTrustScore(5, 5)).toBe(1);
  expect(computeTrustScore(3, 6)).toBe(0.5);
  expect(computeTrustScore(2, 4)).toBe(0.5);
  expect(computeTrustScore(1, 2)).toBe(0.5);
});

test('getTrustLevel categorizes scores correctly', () => {
  expect(getTrustLevel(0.9)).toBe('very_high');
  expect(getTrustLevel(0.8)).toBe('high');
  expect(getTrustLevel(0.7)).toBe('high');
  expect(getTrustLevel(0.6)).toBe('medium');
  expect(getTrustLevel(0.5)).toBe('medium');
  expect(getTrustLevel(0.4)).toBe('low');
  expect(getTrustLevel(0)).toBe('very_low');
});

test('getTrustFormulaVersion returns the version', () => {
  expect(getTrustFormulaVersion()).toBe('1.0');
});

test('TRUST_FORMULA_VERSION is exported correctly', () => {
  expect(TRUST_FORMULA_VERSION).toBe('1.0');
});
