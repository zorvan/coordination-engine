/**
 * Trust value tests.
 * 
 * These tests verify the trust computation logic.
 */

import { describe, it, expect } from 'vitest'
import {
  TrustLevel,
  computeTrustLevel,
  getTrustLevel,
  computeTrustScore,
  createTrustValueObject,
} from '@domain/valuables/trust-value'

/**
 * Tests for TrustLevel constants.
 */
describe('TrustLevel', () => {
  /**
   * Tests that all trust levels are defined.
   */
  it('should define all trust levels', () => {
    expect(TrustLevel.VERY_LOW).toBe('very_low')
    expect(TrustLevel.LOW).toBe('low')
    expect(TrustLevel.MEDIUM).toBe('medium')
    expect(TrustLevel.HIGH).toBe('high')
    expect(TrustLevel.VERY_HIGH).toBe('very_high')
  })
})

/**
 * Tests for computeTrustLevel function.
 */
describe('computeTrustLevel', () => {
  /**
   * Tests very high trust level.
   */
  it('should return very_high for 0.9+', () => {
    expect(computeTrustLevel(0.9)).toBe('very_high')
    expect(computeTrustLevel(1.0)).toBe('very_high')
  })

  /**
   * Tests high trust level.
   */
  it('should return high for 0.7-0.9', () => {
    expect(computeTrustLevel(0.7)).toBe('high')
    expect(computeTrustLevel(0.85)).toBe('high')
  })

  /**
   * Tests medium trust level.
   */
  it('should return medium for 0.5-0.7', () => {
    expect(computeTrustLevel(0.5)).toBe('medium')
    expect(computeTrustLevel(0.6)).toBe('medium')
  })

  /**
   * Tests low trust level.
   */
  it('should return low for 0.3-0.5', () => {
    expect(computeTrustLevel(0.3)).toBe('low')
    expect(computeTrustLevel(0.4)).toBe('low')
  })

  /**
   * Tests very low trust level.
   */
  it('should return very_low for <0.3', () => {
    expect(computeTrustLevel(0.0)).toBe('very_low')
    expect(computeTrustLevel(0.2)).toBe('very_low')
  })
})

/**
 * Tests for getTrustLevel function (alias).
 */
describe('getTrustLevel', () => {
  /**
   * Tests that getTrustLevel is an alias for computeTrustLevel.
   */
  it('should be an alias for computeTrustLevel', () => {
    expect(getTrustLevel(0.85)).toBe('high')
    expect(getTrustLevel(0.4)).toBe('low')
  })
})

/**
 * Tests for computeTrustScore function.
 */
describe('computeTrustScore', () => {
  /**
   * Tests zero when no accepted matches.
   */
  it('should return 0 when no accepted matches', () => {
    expect(computeTrustScore(0, 0)).toBe(0)
    expect(computeTrustScore(5, 0)).toBe(0)
  })

  /**
   * Tests zero when no completed matches.
   */
  it('should return 0 when no completed matches', () => {
    expect(computeTrustScore(0, 5)).toBe(0)
  })

  /**
   * Tests 100% completion.
   */
  it('should return 1 for 100% completion', () => {
    expect(computeTrustScore(5, 5)).toBe(1)
  })

  /**
   * Tests partial completion.
   */
  it('should return correct partial score', () => {
    expect(computeTrustScore(3, 5)).toBe(0.6)
    expect(computeTrustScore(2, 4)).toBe(0.5)
    expect(computeTrustScore(1, 3)).toBe(0.3333333333333333)
  })
})

/**
 * Tests for createTrustValueObject function.
 */
describe('createTrustValueObject', () => {
  /**
   * Tests creating a trust value object.
   */
  it('should create a trust value object', () => {
    const score = 0.8
    const version = 1
    const computedAt = new Date()
    
    const trustValue = createTrustValueObject(score, version, computedAt)
    
    expect(trustValue.score).toBe(0.8)
    expect(trustValue.level).toBe('high')
    expect(trustValue.version).toBe(1)
    expect(trustValue.computedAt).toBe(computedAt)
  })
})