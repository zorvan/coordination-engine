export type MatchStateValue = 'proposed' | 'confirmed' | 'completed' | 'cancelled';

export interface Match {
  matchId: string;
  state: MatchStateValue;
  organizerId: string;
  title: string;
  description: string;
  scheduledTime: Date;
  durationMinutes: number;
  location: string;
  participantIds: string[];
  createdAt: Date;
  updatedAt: Date;
  completedAt: Date | null;
  cancelledAt: Date | null;
  notes: string | null;
  version: number;
}

export interface StoredEvent<TPayload = unknown> {
  id: string;
  aggregateId: string;
  type: string;
  timestamp: Date;
  payload: TPayload;
}

export interface EventStoreLike {
  append(event: unknown): Promise<void>;
  getEventsByAggregate(aggregateId: string): Promise<StoredEvent[]>;
  getEventsByType(type: string): Promise<StoredEvent[]>;
  getAllEvents(): Promise<StoredEvent[]>;
}

export interface MatchRepositoryLike {
  save(match: Match): Promise<void>;
  findById(id: string): Promise<Match | null>;
  findByOrganizer(organizerId: string): Promise<Match[]>;
  findAll(): Promise<Match[]>;
}

export interface ActorRepositoryLike {
  findById(id: string): Promise<unknown | null>;
  save(actor: unknown): Promise<void>;
}

export interface CreateMatchInput {
  organizerId: string;
  title: string;
  description?: string;
  scheduledTime: Date;
  durationMinutes: number;
  location: string;
  participantIds?: string[];
}

export interface CreateMatchUseCaseLike {
  execute(
    organizerId: string,
    title: string,
    description: string,
    scheduledTime: Date,
    durationMinutes: number,
    location: string,
    participantIds: string[]
  ): Promise<string>;
}

export interface ConfirmMatchUseCaseLike {
  execute(matchId: string, actorId: string): Promise<void>;
}

export interface CompleteMatchUseCaseLike {
  execute(matchId: string, completedBy: string, notes: string): Promise<void>;
}

export interface CancelMatchUseCaseLike {
  execute(matchId: string, cancelledBy: string, reason: string): Promise<void>;
}
