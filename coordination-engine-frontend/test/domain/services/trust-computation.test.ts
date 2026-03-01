/**
 * Trust computation service tests.
 * 
 * These tests verify that trust score and level calculations work correctly.
 * 
 * Business logic verified:
 * - Trust score = completed / accepted (with division by zero protection)
 * - Trust levels are correctly mapped from scores
 */

import { describe, it, expect } from 'vitest'
import { computeTrustScore, computeTrustLevel, getTrustLevel, TRUST_FORMULA_VERSION, getAllTrustLevels } from '@domain/services/trust-computation'
import { TrustLevel as TrustLevelEnum } from '@domain/valuables/trust-value'

/**
 * Tests for the trust computation service.
 */
describe('TrustComputation', () => {
  /**
   * Tests the trust formula version constant.
   */
  it('should have a version string', () => {
    expect(TRUST_FORMULA_VERSION).toBe('1.0')
  })

  /**
   * Tests trust score calculation when no accepted matches exist.
   */
  it('should return 0 when no accepted matches', () => {
    const score = computeTrustScore(0, 0)
    expect(score).toBe(0)
  })

  /**
   * Tests trust score calculation with no completed matches.
   */
  it('should return 0 when no completed matches', () => {
    const score = computeTrustScore(0, 5)
    expect(score).toBe(0)
  })

  /**
   * Tests trust score calculation with 100% completed matches.
   */
  it('should return 1 when all matches completed', () => {
    const score = computeTrustScore(5, 5)
    expect(score).toBe(1)
  })

  /**
   * Tests trust score calculation with partial completion.
   */
  it('should return correct partial score', () => {
    const score = computeTrustScore(3, 5)
    expect(score).toBe(0.6)
  })

  /**
   * Tests trust level mapping for very high trust.
   */
  it('should map very high trust score', () => {
    const level = computeTrustLevel(0.95)
    expect(level).toBe('very_high')
  })

  /**
   * Tests trust level mapping for high trust.
   */
  it('should map high trust score', () => {
    const level = computeTrustLevel(0.8)
    expect(level).toBe('high')
  })

  /**
   * Tests trust level mapping for medium trust.
   */
  it('should map medium trust score', () => {
    const level = computeTrustLevel(0.6)
    expect(level).toBe('medium')
  })

  /**
   * Tests trust level mapping for low trust.
   */
  it('should map low trust score', () => {
    const level = computeTrustLevel(0.4)
    expect(level).toBe('low')
  })

  /**
   * Tests trust level mapping for very low trust.
   */
  it('should map very low trust score', () => {
    const level = computeTrustLevel(0.1)
    expect(level).toBe('very_low')
  })

  /**
   * Tests that getTrustLevel is an alias for computeTrustLevel.
   */
  it('getTrustLevel should be alias for computeTrustLevel', () => {
    const level1 = getTrustLevel(0.8)
    const level2 = computeTrustLevel(0.8)
    expect(level1).toBe(level2)
  })

  /**
   * Tests that all trust levels are available.
   */
  it('should provide all trust levels', () => {
    const levels = getAllTrustLevels()
    expect(levels).toHaveProperty('VERY_LOW')
    expect(levels).toHaveProperty('LOW')
    expect(levels).toHaveProperty('MEDIUM')
    expect(levels).toHaveProperty('HIGH')
    expect(levels).toHaveProperty('VERY_HIGH')
  })
})