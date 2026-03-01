/**
 * Repository interface for match operations.
 * 
 * This interface defines the contract for match storage.
 * Infrastructure implementations (REST, local storage, etc.) must satisfy this interface.
 * 
 * Pattern: Repository - abstracts data access logic
 * Pattern: Dependency Inversion - domain depends on abstractions
 */

import { MatchAggregate } from '@domain/aggregates/match-aggregate'

/**
 * Match repository interface.
 */
export interface MatchRepository {
  /**
   * Find a match by ID.
   * 
   * @param id - Match identifier
   * @returns Match aggregate or null if not found
   */
  findById(id: string): Promise<MatchAggregate | null>
  
  /**
   * Save a match to storage.
   * 
   * @param match - Match aggregate to persist
   */
  save(match: MatchAggregate): Promise<void>
  
  /**
   * Find matches by organizer.
   * 
   * @param organizerId - Organizer actor ID
   * @returns Array of match aggregates
   */
  findByOrganizer(organizerId: string): Promise<MatchAggregate[]>
  
  /**
   * Find all matches.
   * 
   * @returns Array of all match aggregates
   */
  findAll(): Promise<MatchAggregate[]>
}