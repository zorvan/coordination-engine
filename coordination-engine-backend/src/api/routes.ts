import { Request, Response } from 'express';
import { randomUUID } from 'crypto';
import {
  CancelMatchUseCaseLike,
  CompleteMatchUseCaseLike,
  ConfirmMatchUseCaseLike,
  CreateMatchUseCaseLike,
  EventStoreLike,
  MatchRepositoryLike,
} from '../types/match';
import { createActor } from '../domain/entities/actor';
import { logger } from '../infrastructure/logging/logger';

type RouteEntry = {
  path: string;
  method: 'get' | 'post' | 'put';
  handler: (req: Request, res: Response) => void;
};

type RouterDef = {
  routes: RouteEntry[];
  post: (path: string, handler: (req: Request, res: Response) => void) => void;
  get: (path: string, handler: (req: Request, res: Response) => void) => void;
  put: (path: string, handler: (req: Request, res: Response) => void) => void;
};

type AuthProvider = 'email' | 'google' | 'facebook';

type AuthSessionPayload = {
  status: 'authenticated';
  token: string;
  user: {
    id: string;
    email: string;
    provider: AuthProvider;
    // name may be undefined for some providers but is useful for the
    // frontend to pre‑fill profile/onboarding UI.
    name?: string;
  };
};

type CalendarCommitmentDegree = 'soft' | 'moderate' | 'firm' | 'locked';
type CalendarSlotStatus = 'free' | 'busy';

type CommunityCalendarSlot = {
  day: string;
  period: string;
  status: CalendarSlotStatus;
  probability: number;
  commitment: CalendarCommitmentDegree;
  eventTitle?: string;
};

type CommunityFriend = {
  id: string;
  email: string;
  name: string;
  relationship: string;
  trustScore: number;
  reliability: number;
  lastInteraction: string;
  groupIds: string[];
};

type CommunityGroupMember = {
  friendId: string;
  role: string;
  historyReliability: number;
  commitmentConsistency: number;
  responsePace: number;
};

type CommunityGroup = {
  id: string;
  name: string;
  purpose: string;
  members: CommunityGroupMember[];
};

type CommunitySnapshot = {
  calendarSlots: CommunityCalendarSlot[];
  friends: CommunityFriend[];
  groups: CommunityGroup[];
  updatedAt: string;
};

const FRONTEND_BASE_URL = process.env.FRONTEND_BASE_URL || 'http://localhost:5173';
const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://localhost:3000';
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID || '';
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET || '';
const FACEBOOK_CLIENT_ID = process.env.FACEBOOK_CLIENT_ID || '';
const FACEBOOK_CLIENT_SECRET = process.env.FACEBOOK_CLIENT_SECRET || '';

const createSession = function(provider: AuthProvider, email: string, idSeed: string, name?: string): AuthSessionPayload {
  const session: AuthSessionPayload = {
    status: 'authenticated',
    token: `local-${randomUUID()}`,
    user: {
      id: `${provider}:${idSeed}`,
      email: email.toLowerCase(),
      provider
    }
  };
  if (name && typeof name === 'string' && name.trim()) {
    session.user.name = name.trim();
  }
  return session;
};


const displayNameFromEmail = function(email: string): string {
  const localPart = email.split('@')[0] || 'User';
  return localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ');
};

const ensureActorExists = async function(
  actorRepository: any,
  eventStore: EventStoreLike,
  actorId: string,
  email: string,
  name?: string
): Promise<void> {
  try {
    logger.info('ensureActorExists called', { actorId, email, name });

    // check for any existing events first (fast path)
    const hasEvents = eventStore && typeof eventStore.getEventsByAggregate === 'function'
      ? (await eventStore.getEventsByAggregate(actorId)).length > 0
      : false;
    logger.info('ensureActorExists hasEvents?', { actorId, hasEvents });
    if (hasEvents) {
      logger.info('ensureActorExists early return: events present', { actorId });
      return;
    }

    // if a repository is present we can also try to read the projected actor
    const existing = actorRepository && typeof actorRepository.findById === 'function'
      ? await actorRepository.findById(actorId)
      : null;
    logger.info('ensureActorExists existing actor?', { actorId, exists: !!existing });
    if (existing) {
      logger.info('ensureActorExists early return: actor exists in repo', { actorId });
      return;
    }

    // build a new actor and persist it
    const actor = createActor(
      actorId,
      name && name.trim() ? name.trim() : displayNameFromEmail(email),
      email.toLowerCase(),
      ''
    );

    if (actorRepository && typeof actorRepository.save === 'function') {
      await actorRepository.save(actor);
      logger.info('ensureActorExists appended ActorCreated via repository', { actorId });
      return;
    }

    await eventStore.append({
      id: `evt-${randomUUID()}`,
      aggregateId: actorId,
      type: 'ActorCreated',
      timestamp: new Date(),
      payload: actor,
    });
    logger.info('ensureActorExists appended ActorCreated directly', { actorId });
  } catch (_err) {
    // auth can still succeed when profile persistence fails
  }
};

const redirectWithSession = function(res: Response, session: AuthSessionPayload): void {
  const encodedUser = Buffer.from(JSON.stringify(session.user), 'utf8').toString('base64url');
  const params = new URLSearchParams({
    token: session.token,
    user: encodedUser
  });
  res.redirect(`${FRONTEND_BASE_URL}/login?${params.toString()}`);
};

const redirectWithError = function(res: Response, message: string): void {
  const params = new URLSearchParams({ error: message });
  res.redirect(`${FRONTEND_BASE_URL}/login?${params.toString()}`);
};

/*  -----------------------------------------------------------------------
                                  CREATE ROUTES
    -----------------------------------------------------------------------  */

const createRoutes = function(
  matchRepository: MatchRepositoryLike,
  createMatchUseCase: CreateMatchUseCaseLike,
  confirmMatchUseCase: ConfirmMatchUseCaseLike,
  completeMatchUseCase: CompleteMatchUseCaseLike,
  cancelMatchUseCase: CancelMatchUseCaseLike,
  eventStore: EventStoreLike,
  actorRepository: any
): RouterDef {
  const readCommunitySnapshot = async function(actorId: string): Promise<CommunitySnapshot | null> {
    const events = await eventStore.getEventsByAggregate(actorId);
    const snapshots = events
      .filter((event) => event.type === 'ActorCommunitySnapshotSet')
      .sort((a, b) => +new Date(a.timestamp) - +new Date(b.timestamp));
    const latest = snapshots[snapshots.length - 1];
    if (!latest) {
      return null;
    }
    return latest.payload as CommunitySnapshot;
  };

  const errorStatus = function(error: unknown): number {
    const message = error instanceof Error ? error.message.toLowerCase() : '';
    if (message.includes('not authorized')) {
      return 403;
    }
    if (message.includes('not found')) {
      return 404;
    }
    if (message.includes('only proposed') || message.includes('only confirmed') || message.includes('invalid')) {
      return 400;
    }
    return 500;
  };
  const sanitizeForLogs = function(value: unknown): unknown {
    if (Array.isArray(value)) {
      return value.map(sanitizeForLogs);
    }
    if (value && typeof value === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
        const lower = key.toLowerCase();
        if (lower.includes('password') || lower.includes('token') || lower.includes('secret')) {
          result[key] = '[REDACTED]';
        } else {
          result[key] = sanitizeForLogs(raw);
        }
      }
      return result;
    }
    return value;
  };

  const withActionLog = function(method: 'get' | 'post' | 'put', path: string, handler: (req: Request, res: Response) => void) {
    return function(req: Request, res: Response): void {
      logger.info('Route action started', {
        method: method.toUpperCase(),
        path,
        query: req.query,
        params: req.params,
        body: sanitizeForLogs(req.body)
      });

      try {
        handler(req, res);
      } catch (error) {
        logger.error('Route action failed (sync)', {
          method: method.toUpperCase(),
          path,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        throw error;
      }
    };
  };

  // we keep a list instead of a simple map so the same path can be
  // registered for multiple HTTP methods (GET + PUT etc).  previously the
  // second registration would clobber the first which caused 404s in tests.
  const router: RouterDef = {
    routes: [],
    post: function(path, handler) {
      this.routes.push({ path, method: 'post', handler: withActionLog('post', path, handler) });
    },
    get: function(path, handler) {
      this.routes.push({ path, method: 'get', handler: withActionLog('get', path, handler) });
    },
    put: function(path, handler) {
      this.routes.push({ path, method: 'put', handler: withActionLog('put', path, handler) });
    }
  };

  router.post('/matches', function(req: Request, res: Response) {
    logger.info('Create match requested', {
      organizerId: req.body.organizerId,
      participantCount: Array.isArray(req.body.participantIds) ? req.body.participantIds.length : 0
    });
    createMatchUseCase.execute(
      req.body.organizerId,
      req.body.title,
      req.body.description,
      new Date(req.body.scheduledTime),
      req.body.durationMinutes,
      req.body.location,
      req.body.participantIds
    ).then(function(matchId: string) {
      logger.info('Match created', { matchId });
      res.status(201).json({
        matchId: matchId,
        status: 'match_created',
        message: 'Match has been created successfully'
      });
    }).catch(function(error: unknown) {
      logger.error('Create match failed', {
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      res.status(500).json({
        error: 'failed_to_create_match',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    });
  });

  router.post('/matches/confirm', function(req: Request, res: Response) {
    confirmMatchUseCase.execute(req.body.matchId, req.body.actorId)
      .then(function() {
        res.status(200).json({
          status: 'match_confirmed',
          message: 'Match has been confirmed successfully'
        });
      })
      .catch(function(error: unknown) {
        const status = errorStatus(error);
        res.status(status).json({
          error: 'failed_to_confirm_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.post('/matches/complete', function(req: Request, res: Response) {
    completeMatchUseCase.execute(req.body.matchId, req.body.actorId, req.body.notes)
      .then(function() {
        res.status(200).json({
          status: 'match_completed',
          message: 'Match has been completed successfully'
        });
      })
      .catch(function(error: unknown) {
        const status = errorStatus(error);
        res.status(status).json({
          error: 'failed_to_complete_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.post('/matches/cancel', function(req: Request, res: Response) {
    cancelMatchUseCase.execute(req.body.matchId, req.body.actorId, req.body.reason)
      .then(function() {
        res.status(200).json({
          status: 'match_cancelled',
          message: 'Match has been cancelled successfully'
        });
      })
      .catch(function(error: unknown) {
        const status = errorStatus(error);
        res.status(status).json({
          error: 'failed_to_cancel_match',
          message: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      });
  });

  router.get('/matches', async function(req: Request, res: Response) {
    try {
      const actorId = typeof req.query.actorId === 'string' ? req.query.actorId : '';
      const matches = actorId
        ? await matchRepository.findByOrganizer(actorId)
        : await matchRepository.findAll();
      res.status(200).json({ matches });
    } catch (error: unknown) {
      res.status(500).json({
        error: 'failed_to_fetch_matches',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  });

  router.get('/matches/:matchId', async function(req: Request, res: Response) {
    try {
      const match = await matchRepository.findById(req.params.matchId);
      if (!match) {
        res.status(404).json({
          error: 'match_not_found',
          message: 'Match not found'
        });
        return;
      }
      res.status(200).json(match);
    } catch (error: unknown) {
      res.status(500).json({
        error: 'failed_to_fetch_match',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  });

  router.get('/matches/:matchId/availability/:actorId', async function(req: Request, res: Response) {
    const matchId = typeof req.params.matchId === 'string' ? req.params.matchId : '';
    const actorId = typeof req.params.actorId === 'string' ? req.params.actorId : '';
    if (!matchId || !actorId) {
      res.status(400).json({
        error: 'invalid_availability_params',
        message: 'Match id and actor id are required'
      });
      return;
    }

    try {
      const events = await eventStore.getEventsByAggregate(matchId);
      const availabilityEvents = events
        .filter((event) => event.type === 'MatchAvailabilityProvided')
        .filter((event) => {
          const payload = event.payload as { actorId?: string };
          return payload.actorId === actorId;
        })
        .sort((a, b) => +new Date(a.timestamp) - +new Date(b.timestamp));

      const latest = availabilityEvents[availabilityEvents.length - 1];
      if (!latest) {
        res.status(404).json({
          error: 'availability_not_found',
          message: 'Availability not found'
        });
        return;
      }

      res.status(200).json({ availability: latest.payload });
    } catch (error: unknown) {
      res.status(500).json({
        error: 'failed_to_fetch_availability',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  });

  router.post('/matches/availability', async function(req: Request, res: Response) {
    const matchId = typeof req.body.matchId === 'string' ? req.body.matchId : '';
    const actorId = typeof req.body.actorId === 'string' ? req.body.actorId : '';
    const priority = typeof req.body.priority === 'string' ? req.body.priority : '';
    const availabilityStart = typeof req.body.availabilityStart === 'string' ? req.body.availabilityStart : '';
    const availabilityEnd = typeof req.body.availabilityEnd === 'string' ? req.body.availabilityEnd : '';
    const commitments = typeof req.body.commitments === 'string' ? req.body.commitments : '';

    if (!matchId || !actorId || !priority || !availabilityStart || !availabilityEnd) {
      res.status(400).json({
        error: 'invalid_availability_payload',
        message: 'matchId, actorId, priority, availabilityStart and availabilityEnd are required'
      });
      return;
    }

    try {
      logger.info('Match availability submitted', { matchId, actorId, priority });
      await eventStore.append({
        id: `evt-${randomUUID()}`,
        aggregateId: matchId,
        type: 'MatchAvailabilityProvided',
        timestamp: new Date(),
        payload: {
          actorId,
          priority,
          availabilityStart,
          availabilityEnd,
          commitments,
          submittedAt: new Date().toISOString()
        },
      });

      res.status(200).json({
        status: 'availability_recorded',
        message: 'Availability preferences saved successfully'
      });
    } catch (error: unknown) {
      logger.error('Saving match availability failed', {
        matchId,
        actorId,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      res.status(500).json({
        error: 'failed_to_save_availability',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  });

  router.post('/auth/email/login', async function(req: Request, res: Response) {
    const email = typeof req.body.email === 'string' ? req.body.email.trim() : '';
    const password = typeof req.body.password === 'string' ? req.body.password : '';

    if (!email || !password) {
      res.status(400).json({
        error: 'invalid_credentials',
        message: 'Email and password are required'
      });
      return;
    }

    let session = createSession('email', email, email.toLowerCase());
    // if we already have an actor record, grab the stored name so the
    // client can prepopulate fields and avoid an extra fetch.
    try {
      const existing = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(session.user.id)
        : null;
      if (existing && typeof existing.name === 'string' && existing.name.trim()) {
        session.user.name = existing.name;
      }
    } catch (_e) {
      // ignore, we still want login to succeed even if profile lookup fails
    }

    await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
    logger.info('Email login succeeded', { userId: session.user.id });
    res.status(200).json(session);
  });

  router.post('/auth/email/signup', async function(req: Request, res: Response) {
    const email = typeof req.body.email === 'string' ? req.body.email.trim() : '';
    const password = typeof req.body.password === 'string' ? req.body.password : '';
    const fullName = typeof req.body.fullName === 'string' ? req.body.fullName.trim() : '';

    if (!fullName || !email || !password) {
      res.status(400).json({
        error: 'invalid_signup_payload',
        message: 'Full name, email and password are required'
      });
      return;
    }

    if (password.length < 8) {
      res.status(400).json({
        error: 'weak_password',
        message: 'Password must be at least 8 characters'
      });
      return;
    }

    // persist actor to event store via actorRepository
    const session = createSession('email', email, email.toLowerCase());
    await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email, fullName);
    logger.info('Email signup succeeded', { userId: session.user.id });
    res.status(201).json(session);
  });

  router.post('/auth/google/login', async function(req: Request, res: Response) {
    const idToken = typeof req.body.idToken === 'string' ? req.body.idToken : '';
    if (!idToken) {
      res.status(400).json({
        error: 'missing_google_token',
        message: 'Google ID token is required'
      });
      return;
    }

    const tokenInfoRes = await fetch(`https://oauth2.googleapis.com/tokeninfo?id_token=${encodeURIComponent(idToken)}`);
    if (!tokenInfoRes.ok) {
      res.status(401).json({
        error: 'invalid_google_token',
        message: 'Google authentication failed'
      });
      return;
    }

    const tokenInfo = await tokenInfoRes.json() as { email?: string; sub?: string; email_verified?: string; name?: string };
    if (!tokenInfo.email || !tokenInfo.sub || tokenInfo.email_verified !== 'true') {
      res.status(401).json({
        error: 'invalid_google_identity',
        message: 'Google identity is invalid'
      });
      return;
    }

    // some tokens include a `name` field, use it if present
    let session = createSession('google', tokenInfo.email, tokenInfo.sub, tokenInfo.name || undefined);
    try {
      const existing = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(session.user.id)
        : null;
      if (existing && typeof existing.name === 'string' && existing.name.trim()) {
        session.user.name = existing.name;
      }
    } catch (_e) {
      // ignore
    }
    await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
    logger.info('Google login succeeded', { userId: session.user.id });
    res.status(200).json(session);
  });

  router.post('/auth/facebook/login', async function(req: Request, res: Response) {
    const accessToken = typeof req.body.accessToken === 'string' ? req.body.accessToken : '';
    if (!accessToken) {
      res.status(400).json({
        error: 'missing_facebook_token',
        message: 'Facebook access token is required'
      });
      return;
    }

    const userParams = new URLSearchParams({
      fields: 'id,email,name',
      access_token: accessToken
    });
    const userRes = await fetch(`https://graph.facebook.com/me?${userParams.toString()}`);
    if (!userRes.ok) {
      res.status(401).json({
        error: 'invalid_facebook_token',
        message: 'Facebook authentication failed'
      });
      return;
    }

    const userInfo = await userRes.json() as { id?: string; email?: string };
    if (!userInfo.id || !userInfo.email) {
      res.status(401).json({
        error: 'invalid_facebook_identity',
        message: 'Facebook identity is invalid'
      });
      return;
    }

    let session = createSession('facebook', userInfo.email, userInfo.id, (userInfo as any).name);
    try {
      const existing = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(session.user.id)
        : null;
      if (existing && typeof existing.name === 'string' && existing.name.trim()) {
        session.user.name = existing.name;
      }
    } catch (_e) {
      // ignore
    }
    await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
    logger.info('Facebook login succeeded', { userId: session.user.id });
    res.status(200).json(session);
  });

  router.get('/auth/google/start', function(_req: Request, res: Response) {
    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
      // Development fallback: redirect to callback with dev code
      const devEmail = 'dev.google@example.com';
      res.redirect(`${BACKEND_BASE_URL}/auth/google/callback?code=__dev__&dev_email=${encodeURIComponent(devEmail)}`);
      return;
    }

    const redirectUri = `${BACKEND_BASE_URL}/auth/google/callback`;
    const params = new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'openid email profile',
      access_type: 'offline',
      prompt: 'consent'
    });

    res.redirect(`https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`);
  });

  router.get('/auth/google/callback', async function(req: Request, res: Response) {
    const code = typeof req.query.code === 'string' ? req.query.code : '';
    if (!code) {
      redirectWithError(res, 'Missing Google auth code');
      return;
    }

    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
      // dev fallback: if code is our dev marker, accept and create session
      if (code === '__dev__') {
        const devEmail = typeof req.query.dev_email === 'string' ? req.query.dev_email : 'dev.google@example.com';
        const session = createSession('google', devEmail, devEmail);
        await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
        redirectWithSession(res, session);
        return;
      }
      redirectWithError(res, 'Google OAuth is not configured');
      return;
    }

    try {
      const redirectUri = `${BACKEND_BASE_URL}/auth/google/callback`;
      const tokenBody = new URLSearchParams({
        code,
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        redirect_uri: redirectUri,
        grant_type: 'authorization_code'
      });

      const tokenRes = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: tokenBody.toString()
      });

      if (!tokenRes.ok) {
        redirectWithError(res, 'Google token exchange failed');
        return;
      }

      const tokenData = await tokenRes.json() as { access_token?: string };
      const accessToken = tokenData.access_token;
      if (!accessToken) {
        redirectWithError(res, 'Google access token missing');
        return;
      }

      const userRes = await fetch('https://openidconnect.googleapis.com/v1/userinfo', {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (!userRes.ok) {
        redirectWithError(res, 'Google user info fetch failed');
        return;
      }

      const userInfo = await userRes.json() as { sub?: string; email?: string };
      const email = userInfo.email || 'google.user@example.com';
      const session = createSession('google', email, userInfo.sub || email);
      await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
      redirectWithSession(res, session);
    } catch (_error) {
      redirectWithError(res, 'Google authentication failed');
    }
  });

  router.get('/auth/facebook/start', function(_req: Request, res: Response) {
    if (!FACEBOOK_CLIENT_ID || !FACEBOOK_CLIENT_SECRET) {
      const devEmail = 'dev.facebook@example.com';
      res.redirect(`${BACKEND_BASE_URL}/auth/facebook/callback?code=__dev__&dev_email=${encodeURIComponent(devEmail)}`);
      return;
    }

    const redirectUri = `${BACKEND_BASE_URL}/auth/facebook/callback`;
    const params = new URLSearchParams({
      client_id: FACEBOOK_CLIENT_ID,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'email,public_profile'
    });

    res.redirect(`https://www.facebook.com/v20.0/dialog/oauth?${params.toString()}`);
  });

  router.get('/auth/facebook/callback', async function(req: Request, res: Response) {
    const code = typeof req.query.code === 'string' ? req.query.code : '';
    if (!code) {
      redirectWithError(res, 'Missing Facebook auth code');
      return;
    }

    if (!FACEBOOK_CLIENT_ID || !FACEBOOK_CLIENT_SECRET) {
      if (code === '__dev__') {
        const devEmail = typeof req.query.dev_email === 'string' ? req.query.dev_email : 'dev.facebook@example.com';
        const session = createSession('facebook', devEmail, devEmail);
        await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
        redirectWithSession(res, session);
        return;
      }
      redirectWithError(res, 'Facebook OAuth is not configured');
      return;
    }

    try {
      const redirectUri = `${BACKEND_BASE_URL}/auth/facebook/callback`;
      const tokenParams = new URLSearchParams({
        client_id: FACEBOOK_CLIENT_ID,
        client_secret: FACEBOOK_CLIENT_SECRET,
        redirect_uri: redirectUri,
        code
      });

      const tokenRes = await fetch(`https://graph.facebook.com/v20.0/oauth/access_token?${tokenParams.toString()}`);
      if (!tokenRes.ok) {
        redirectWithError(res, 'Facebook token exchange failed');
        return;
      }

      const tokenData = await tokenRes.json() as { access_token?: string };
      const accessToken = tokenData.access_token;
      if (!accessToken) {
        redirectWithError(res, 'Facebook access token missing');
        return;
      }

      const userParams = new URLSearchParams({
        fields: 'id,email,name',
        access_token: accessToken
      });
      const userRes = await fetch(`https://graph.facebook.com/me?${userParams.toString()}`);
      if (!userRes.ok) {
        redirectWithError(res, 'Facebook user info fetch failed');
        return;
      }

      const userInfo = await userRes.json() as { id?: string; email?: string };
      const email = userInfo.email || 'facebook.user@example.com';
      const session = createSession('facebook', email, userInfo.id || email, email);
      await ensureActorExists(actorRepository, eventStore, session.user.id, session.user.email);
      redirectWithSession(res, session);
    } catch (_error) {
      redirectWithError(res, 'Facebook authentication failed');
    }
  });

  // Actor profile endpoints
  router.get('/actors/:id', async function(req: Request, res: Response) {
    const id = typeof req.params.id === 'string' ? req.params.id : '';
    if (!id) {
      res.status(400).json({ error: 'invalid_actor_id', message: 'Actor id is required' });
      return;
    }

    try {
      const actor = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(id)
        : null;
      if (!actor) {
        res.status(404).json({ error: 'actor_not_found', message: 'Actor not found' });
        return;
      }
      res.status(200).json({ actor });
    } catch (err) {
      res.status(500).json({ error: 'failed_to_fetch_actor', message: err instanceof Error ? err.message : 'Unknown error' });
    }
  });

  router.put('/actors/:id', async function(req: Request, res: Response) {
    const id = typeof req.params.id === 'string' ? req.params.id : '';
    const updates = req.body || {};
    if (!id) {
      res.status(400).json({ error: 'invalid_actor_id', message: 'Actor id is required' });
      return;
    }

    try {
      // remove undefined values so we never overwrite with "nothing"
      const cleanUpdates: Record<string, unknown> = {};
      Object.entries(updates).forEach(([k, v]) => {
        if (v !== undefined) {
          cleanUpdates[k] = v;
        }
      });

      logger.info('Actor update requested', { actorId: id, fields: Object.keys(cleanUpdates) });

      const existing = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(id)
        : null;

      if (!existing) {
        res.status(404).json({ error: 'actor_not_found', message: 'Actor not found' });
        return;
      }

      if (Object.keys(cleanUpdates).length === 0) {
        // nothing to change
        res.status(400).json({ error: 'no_updates', message: 'No valid update fields provided' });
        return;
      }

      // append a patch event rather than trying to merge on the server side.  the
      // repository/projection layer will take care of merging with previous state.
      if (actorRepository && typeof actorRepository.update === 'function') {
        await actorRepository.update({ id, ...cleanUpdates });
      } else {
        await eventStore.append({
          id: `evt-${randomUUID()}`,
          aggregateId: id,
          type: 'ActorUpdated',
          timestamp: new Date(),
          payload: { id, ...cleanUpdates },
        });
      }

      const saved = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(id)
        : { ...existing, ...cleanUpdates, id };

      logger.info('Actor updated', { actorId: id, resultingFields: Object.keys(saved) });
      res.status(200).json({ actor: saved });
    } catch (err) {
      logger.error('Actor update failed', {
        actorId: id,
        error: err instanceof Error ? err.message : 'Unknown error'
      });
      res.status(500).json({ error: 'failed_to_update_actor', message: err instanceof Error ? err.message : 'Unknown error' });
    }
  });

  router.get('/actors/:id/community', async function(req: Request, res: Response) {
    const id = typeof req.params.id === 'string' ? req.params.id : '';
    if (!id) {
      res.status(400).json({ error: 'invalid_actor_id', message: 'Actor id is required' });
      return;
    }

    try {
      const actor = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(id)
        : null;

      if (!actor) {
        res.status(404).json({ error: 'actor_not_found', message: 'Actor not found' });
        return;
      }

      const snapshot = await readCommunitySnapshot(id);
      if (!snapshot) {
        res.status(200).json({
          community: {
            calendarSlots: [],
            friends: [],
            groups: [],
            updatedAt: new Date(0).toISOString(),
          }
        });
        return;
      }

      res.status(200).json({ community: snapshot });
    } catch (err) {
      res.status(500).json({
        error: 'failed_to_fetch_community',
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    }
  });

  router.put('/actors/:id/community', async function(req: Request, res: Response) {
    const id = typeof req.params.id === 'string' ? req.params.id : '';
    const body = req.body || {};

    if (!id) {
      res.status(400).json({ error: 'invalid_actor_id', message: 'Actor id is required' });
      return;
    }

    const calendarSlots = Array.isArray(body.calendarSlots) ? body.calendarSlots : undefined;
    const friends = Array.isArray(body.friends) ? body.friends : undefined;
    const groups = Array.isArray(body.groups) ? body.groups : undefined;

    if (!calendarSlots && !friends && !groups) {
      res.status(400).json({
        error: 'invalid_community_payload',
        message: 'At least one of calendarSlots, friends or groups must be provided'
      });
      return;
    }

    try {
      const actor = actorRepository && typeof actorRepository.findById === 'function'
        ? await actorRepository.findById(id)
        : null;

      if (!actor) {
        res.status(404).json({ error: 'actor_not_found', message: 'Actor not found' });
        return;
      }

      const current = await readCommunitySnapshot(id);
      const next: CommunitySnapshot = {
        calendarSlots: (calendarSlots as CommunityCalendarSlot[] | undefined) || current?.calendarSlots || [],
        friends: (friends as CommunityFriend[] | undefined) || current?.friends || [],
        groups: (groups as CommunityGroup[] | undefined) || current?.groups || [],
        updatedAt: new Date().toISOString(),
      };

      await eventStore.append({
        id: `evt-${randomUUID()}`,
        aggregateId: id,
        type: 'ActorCommunitySnapshotSet',
        timestamp: new Date(),
        payload: next,
      });

      res.status(200).json({
        status: 'community_updated',
        message: 'Community data updated successfully',
        community: next,
      });
    } catch (err) {
      res.status(500).json({
        error: 'failed_to_update_community',
        message: err instanceof Error ? err.message : 'Unknown error'
      });
    }
  });

  return router;
};

export { createRoutes };
