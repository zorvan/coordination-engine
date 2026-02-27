const {
  TRUST_FORMULA_VERSION,
  computeTrustScore,
  computeTrustLevel,
  getTrustLevel,
  getTrustFormulaVersion,
} = require('../../../src/domain/services/trust-computation');
const { TrustValue } = require('../../../src/domain/valuables/trust-value');

describe('TrustComputation', () => {
  test('computeTrustScore returns 0 when acceptedMatches is 0', () => {
    expect(computeTrustScore(0, 0)).toBe(0);
    expect(computeTrustScore(10, 0)).toBe(0);
  });

  test('computeTrustScore returns correct ratio', () => {
    expect(computeTrustScore(0, 10)).toBe(0);
    expect(computeTrustScore(5, 10)).toBe(0.5);
    expect(computeTrustScore(10, 10)).toBe(1);
    expect(computeTrustScore(8, 10)).toBe(0.8);
  });

  test('computeTrustLevel returns correct levels', () => {
    // Very High: >= 0.9
    expect(computeTrustLevel(0.9)).toBe(TrustValue.VERY_HIGH);
    expect(computeTrustLevel(0.95)).toBe(TrustValue.VERY_HIGH);
    expect(computeTrustLevel(1.0)).toBe(TrustValue.VERY_HIGH);

    // High: >= 0.7 and < 0.9
    expect(computeTrustLevel(0.7)).toBe(TrustValue.HIGH);
    expect(computeTrustLevel(0.8)).toBe(TrustValue.HIGH);
    expect(computeTrustLevel(0.89)).toBe(TrustValue.HIGH);

    // Medium: >= 0.5 and < 0.7
    expect(computeTrustLevel(0.5)).toBe(TrustValue.MEDIUM);
    expect(computeTrustLevel(0.6)).toBe(TrustValue.MEDIUM);
    expect(computeTrustLevel(0.69)).toBe(TrustValue.MEDIUM);

    // Low: >= 0.3 and < 0.5
    expect(computeTrustLevel(0.3)).toBe(TrustValue.LOW);
    expect(computeTrustLevel(0.4)).toBe(TrustValue.LOW);
    expect(computeTrustLevel(0.49)).toBe(TrustValue.LOW);

    // Very Low: < 0.3
    expect(computeTrustLevel(0.0)).toBe(TrustValue.VERY_LOW);
    expect(computeTrustLevel(0.2)).toBe(TrustValue.VERY_LOW);
    expect(computeTrustLevel(0.29)).toBe(TrustValue.VERY_LOW);
  });

  test('getTrustLevel returns same as computeTrustLevel', () => {
    expect(getTrustLevel(0.5)).toBe(TrustValue.MEDIUM);
    expect(getTrustLevel(0.8)).toBe(TrustValue.HIGH);
  });

  test('TRUST_FORMULA_VERSION is defined', () => {
    expect(TRUST_FORMULA_VERSION).toBe('1.0');
  });

  test('getTrustFormulaVersion returns correct version', () => {
    expect(getTrustFormulaVersion()).toBe('1.0');
  });
});