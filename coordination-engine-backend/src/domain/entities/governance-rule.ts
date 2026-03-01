/**
 * Governance rule entity
 * 
 * Represents a governance rule with versioning
 * Supports multiple versions with activation timeline
 */

const RuleType = {
  VALIDATION: 'validation',
  RESTRICTION: 'restriction',
  PREFERENCE: 'preference',
  CONFIDENCE: 'confidence',
} as const;

type RuleTypeValue = (typeof RuleType)[keyof typeof RuleType];

interface GovernanceRule {
  ruleId: string;
  name: string;
  type: RuleTypeValue;
  content: unknown;
  activatedAt: Date;
  expiresAt: Date | null;
  isActive: boolean;
  isExpired: boolean;
  createdAt: Date;
}

/**
 * Create a new governance rule version
 * 
 * @param {string} ruleId - Unique rule identifier
 * @param {string} name - Rule name
 * @param {string} type - Rule type (validation, restriction, preference, confidence)
 * @param {Object} content - Rule content/configuration
 * @param {Date} activatedAt - When rule becomes active
 * @param {Date} expiresAt - When rule expires (optional)
 * @returns {Object} Governance rule entity
 */
function createGovernanceRule(
  ruleId: string,
  name: string,
  type: RuleTypeValue,
  content: unknown,
  activatedAt: Date,
  expiresAt: Date | null = null
): GovernanceRule {
  if (!Object.values(RuleType).includes(type)) {
    throw new Error(`Invalid rule type: ${type}`);
  }

  const now = new Date();
  const isActive = activatedAt <= now && (!expiresAt || expiresAt >= now);
  const isExpired = !!expiresAt && now > expiresAt;

  return {
    ruleId,
    name,
    type,
    content,
    activatedAt,
    expiresAt,
    isActive,
    isExpired,
    createdAt: new Date(),
  };
}

/**
 * Check if a rule is currently active
 * 
 * @param {Object} rule - Governance rule entity
 * @param {Date} atDate - Date to check (default: now)
 * @returns {boolean} True if rule is active
 */
function isRuleActive(rule: GovernanceRule, atDate: Date = new Date()): boolean {
  if (rule.isExpired) return false;
  if (atDate < rule.activatedAt) return false;
  if (rule.expiresAt && atDate > rule.expiresAt) return false;
  return true;
}

/**
 * Check if a rule will expire within a time frame
 * 
 * @param {Object} rule - Governance rule entity
 * @param {number} timeFrameMs - Time frame in milliseconds
 * @returns {boolean} True if rule will expire within time frame
 */
function willRuleExpire(rule: GovernanceRule, timeFrameMs: number): boolean {
  if (!rule.expiresAt) return false;
  
  const now = new Date();
  const expirationTime = rule.expiresAt.getTime();
  const currentTime = now.getTime();
  
  return (expirationTime - currentTime) <= timeFrameMs;
}

export { RuleType,
  createGovernanceRule,
  isRuleActive,
  willRuleExpire, };
