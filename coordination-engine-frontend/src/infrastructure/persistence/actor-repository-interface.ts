/**
 * Actor repository interface.
 * 
 * This interface defines the contract for actor storage.
 * Infrastructure implementations must satisfy this interface.
 */

import { MatchAggregate } from '@domain/aggregates/match-aggregate'

/**
 * Actor repository interface.
 */
export interface ActorRepository {
  /**
   * Find an actor by ID.
   * 
   * @param id - Actor identifier
   * @returns Actor aggregate or null if not found
   */
  findById(id: string): Promise<MatchAggregate | null>
  
  /**
   * Save an actor to storage.
   * 
   * @param actor - Actor aggregate to persist
   */
  save(actor: MatchAggregate): Promise<void>
  
  /**
   * Find actor by email.
   * 
   * @param email - Actor email
   * @returns Actor aggregate or null if not found
   */
  findByEmail(email: string): Promise<MatchAggregate | null>
  
  /**
   * Find all actors.
   * 
   * @returns Array of all actor aggregates
   */
  findAll(): Promise<MatchAggregate[]>
}