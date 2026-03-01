/**
 * Domain commands represent intention-to-action
 * They are the "what" without the "how"
 * 
 * Commands should:
 * - Be named as imperative verbs
 * - Contain all data needed for execution
 * - Be serializable for event sourcing
 * - Not contain business logic
 */

const MatchCommands = {
  Create: 'CreateMatch',
  Confirm: 'ConfirmMatch',
  Complete: 'CompleteMatch',
  Cancel: 'CancelMatch',
};

const TrustCommands = {
  Update: 'UpdateTrust',
};

const GovernanceCommands = {
  CreateRule: 'CreateGovernanceRule',
  UpdateRule: 'UpdateGovernanceRule',
};

const ActorCommands = {
  Create: 'CreateActor',
  Update: 'UpdateActor',
};

export { MatchCommands,
  TrustCommands,
  GovernanceCommands,
  ActorCommands, };