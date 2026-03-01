import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMatchCommands, useMatchesData } from '@presentation/hooks/useMatch'
import {
  AvailabilityCalendar,
  Button,
  Form,
  FormGroup,
  FriendsList,
  GroupsList,
  Input,
  Modal,
  TextArea,
  type AvailabilitySlot,
  type Friend,
  type Group,
  type GroupMember,
} from '@presentation/components'
import { getSessionUserId } from '@presentation/auth/session-storage'
import { fetchCommunitySnapshot, saveCommunitySnapshot } from '@infrastructure/api/community-service'

const FRIENDS: Friend[] = [
  {
    id: 'friend-lina',
    email: 'lina@example.com',
    name: 'Lina Morais',
    relationship: 'Friend + design collaborator',
    trustScore: 91,
    reliability: 88,
    lastInteraction: '2 days ago',
    groupIds: ['group-product-guild'],
  },
  {
    id: 'friend-kerem',
    email: 'kerem@example.com',
    name: 'Kerem Tan',
    relationship: 'Running partner',
    trustScore: 84,
    reliability: 79,
    lastInteraction: 'Yesterday',
    groupIds: ['group-weekend-outdoors'],
  },
  {
    id: 'friend-jade',
    email: 'jade@example.com',
    name: 'Jade Kim',
    relationship: 'Product mastermind',
    trustScore: 87,
    reliability: 92,
    lastInteraction: 'Today',
    groupIds: ['group-product-guild'],
  },
]

const GROUPS: Group[] = [
  {
    id: 'group-product-guild',
    name: 'Product Guild',
    purpose: 'Roadmapping, sprint shaping, decision prep',
    members: [
      { friendId: 'friend-lina', role: 'Facilitator', historyReliability: 93, commitmentConsistency: 89, responsePace: 85 },
      { friendId: 'friend-jade', role: 'Planner', historyReliability: 88, commitmentConsistency: 91, responsePace: 83 },
    ],
  },
  {
    id: 'group-weekend-outdoors',
    name: 'Weekend Outdoors',
    purpose: 'Trail runs and short hikes',
    members: [
      { friendId: 'friend-kerem', role: 'Route Lead', historyReliability: 86, commitmentConsistency: 82, responsePace: 77 },
      { friendId: 'friend-lina', role: 'Member', historyReliability: 79, commitmentConsistency: 80, responsePace: 91 },
    ],
  },
]

function buildCalendarSlots(input: {
  actorId: string
  matches: Array<{
    organizerId: string
    participantIds: string[]
    state: 'proposed' | 'confirmed' | 'completed' | 'cancelled'
    scheduledTime: Date
    durationMinutes: number
    title: string
  }>
}): AvailabilitySlot[] {
  const result: AvailabilitySlot[] = []
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const firstDay = new Date(today)
  firstDay.setDate(today.getDate() - 1)
  const lastDay = new Date(today)
  lastDay.setDate(today.getDate() + 6)
  lastDay.setHours(23, 59, 59, 999)

  const periods: Array<{ label: string; hour: number }> = []
  for (let hour = 8; hour <= 21; hour++) {
    const nextHour = hour + 1
    periods.push({
      label: `${String(hour).padStart(2, '0')}:00-${String(nextHour).padStart(2, '0')}:00`,
      hour,
    })
  }

  const userMatches = input.matches.filter((match) => {
    if (match.state === 'cancelled') {
      return false
    }
    if (match.scheduledTime < firstDay || match.scheduledTime > lastDay) {
      return false
    }
    return match.organizerId === input.actorId || match.participantIds.includes(input.actorId)
  })

  for (let offset = -1; offset < 7; offset++) {
    const day = new Date(today)
    day.setDate(today.getDate() + offset)
    const dayLabel = day.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })

    for (const period of periods) {
      const matchInPeriod = userMatches
        .filter((match) => {
          const start = new Date(match.scheduledTime)
          const duration = Math.max(30, match.durationMinutes || 60)
          const end = new Date(start.getTime() + duration * 60 * 1000)
          const slotStart = new Date(day)
          slotStart.setHours(period.hour, 0, 0, 0)
          const slotEnd = new Date(slotStart)
          slotEnd.setHours(period.hour + 1, 0, 0, 0)
          return start < slotEnd && end > slotStart
        })
        .sort((a, b) => {
          const rank = { completed: 3, confirmed: 2, proposed: 1, cancelled: 0 } as const
          return rank[b.state] - rank[a.state]
        })[0]

      if (!matchInPeriod) {
        result.push({
          day: dayLabel,
          period: period.label,
          status: 'free',
          probability: 72,
          commitment: 'soft',
        })
        continue
      }

      result.push({
        day: dayLabel,
        period: period.label,
        status: 'busy',
        matchState: matchInPeriod.state === 'cancelled' ? undefined : matchInPeriod.state,
        probability: matchInPeriod.state === 'completed' ? 100 : matchInPeriod.state === 'confirmed' ? 90 : 64,
        commitment: matchInPeriod.state === 'completed' ? 'locked' : matchInPeriod.state === 'confirmed' ? 'firm' : 'moderate',
        eventTitle: matchInPeriod.title,
      })
    }
  }

  return result
}

function syncFriendMemberships(friends: Friend[], groups: Group[]): Friend[] {
  const groupIdsByFriend = new Map<string, string[]>()
  for (const group of groups) {
    for (const member of group.members) {
      const ids = groupIdsByFriend.get(member.friendId) || []
      ids.push(group.id)
      groupIdsByFriend.set(member.friendId, ids)
    }
  }

  return friends.map((friend) => ({
    ...friend,
    groupIds: groupIdsByFriend.get(friend.id) || [],
  }))
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function defaultWhenValue(): string {
  const nextHour = new Date(Date.now() + 60 * 60 * 1000)
  return nextHour.toISOString().slice(0, 16)
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { matches, loading, error, refresh } = useMatchesData()
  const { createMatch, confirmMatch } = useMatchCommands()
  const actorId = getSessionUserId()
  const [calendarSlots, setCalendarSlots] = useState<AvailabilitySlot[]>([])
  const [friends, setFriends] = useState<Friend[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [communityReady, setCommunityReady] = useState(false)
  const [friendEmail, setFriendEmail] = useState('')
  const [friendName, setFriendName] = useState('')
  const [groupName, setGroupName] = useState('')
  const [groupPurpose, setGroupPurpose] = useState('')
  const [selectedFriendIds, setSelectedFriendIds] = useState<string[]>([])
  const [communityError, setCommunityError] = useState('')
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [createFormData, setCreateFormData] = useState({
    title: '',
    description: '',
    when: defaultWhenValue(),
    duration: '90',
    location: '',
  })

  const invitations = useMemo(
    () =>
      matches.filter(
        (match) =>
          actorId &&
          match.organizerId !== actorId &&
          match.participantIds.includes(actorId) &&
          match.state === 'proposed'
      ),
    [actorId, matches]
  )

  const pendingCount = invitations.length
  const upcoming = useMemo(
    () =>
      matches
        .filter(
          (match) =>
            actorId &&
            (match.organizerId === actorId || match.participantIds.includes(actorId)) &&
            match.state !== 'cancelled'
        )
        .sort((a, b) => a.scheduledTime.getTime() - b.scheduledTime.getTime())
        .slice(0, 6),
    [actorId, matches]
  )

  useEffect(() => {
    setCommunityReady(false)
    setCalendarSlots([])
    setFriends([])
    setGroups([])
    setCommunityError('')
  }, [actorId])

  useEffect(() => {
    if (!actorId || loading || communityReady) {
      return
    }

    let cancelled = false

    async function loadCommunity() {
      const snapshot = await fetchCommunitySnapshot(actorId)
      if (cancelled) {
        return
      }

      if (snapshot) {
        const normalizedFriends = snapshot.friends || []
        const normalizedGroups = snapshot.groups || []
        setFriends(syncFriendMemberships(normalizedFriends, normalizedGroups))
        setGroups(normalizedGroups)
        setCalendarSlots(snapshot.calendarSlots || [])
        setCommunityReady(true)
        return
      }

      const seededCalendar = buildCalendarSlots({ actorId, matches })
      const seededFriends = syncFriendMemberships(FRIENDS, GROUPS)
      const seeded = { calendarSlots: seededCalendar, friends: seededFriends, groups: GROUPS }
      const saved = await saveCommunitySnapshot(actorId, seeded)
      if (cancelled) {
        return
      }
      setCalendarSlots(saved?.calendarSlots || seededCalendar)
      setGroups(saved?.groups || GROUPS)
      setFriends(syncFriendMemberships(saved?.friends || seededFriends, saved?.groups || GROUPS))
      setCommunityReady(true)
    }

    void loadCommunity()
    return () => {
      cancelled = true
    }
  }, [actorId, loading, communityReady, matches])

  const computedCalendarSlots = useMemo(
    () => (actorId ? buildCalendarSlots({ actorId, matches }) : []),
    [actorId, matches]
  )

  useEffect(() => {
    if (!actorId || !communityReady) {
      return
    }
    const current = JSON.stringify(calendarSlots)
    const computed = JSON.stringify(computedCalendarSlots)
    if (current === computed) {
      return
    }

    setCalendarSlots(computedCalendarSlots)
    void saveCommunitySnapshot(actorId, {
      calendarSlots: computedCalendarSlots,
      friends,
      groups,
    })
  }, [actorId, calendarSlots, communityReady, computedCalendarSlots, friends, groups])

  async function persistCommunity(nextFriends: Friend[], nextGroups: Group[]) {
    if (!actorId) {
      return
    }
    const normalizedFriends = syncFriendMemberships(nextFriends, nextGroups)
    setFriends(normalizedFriends)
    setGroups(nextGroups)
    const saved = await saveCommunitySnapshot(actorId, {
      calendarSlots: computedCalendarSlots,
      friends: normalizedFriends,
      groups: nextGroups,
    })
    if (saved) {
      setCalendarSlots(saved.calendarSlots || computedCalendarSlots)
      setGroups(saved.groups || nextGroups)
      setFriends(syncFriendMemberships(saved.friends || normalizedFriends, saved.groups || nextGroups))
    }
  }

  async function handleAddFriend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCommunityError('')
    const email = friendEmail.trim().toLowerCase()
    if (!isValidEmail(email)) {
      setCommunityError('Please enter a valid friend email.')
      return
    }

    if (friends.some((friend) => friend.email.toLowerCase() === email)) {
      setCommunityError('This friend email is already added.')
      return
    }

    const fallbackName = email.split('@')[0] || 'Friend'
    const nextFriend: Friend = {
      id: `friend-${email.replace(/[^a-z0-9]+/g, '-')}`,
      email,
      name: friendName.trim() || fallbackName,
      relationship: 'Friend',
      trustScore: 60,
      reliability: 60,
      lastInteraction: 'Just added',
      groupIds: [],
    }

    await persistCommunity([...friends, nextFriend], groups)
    setFriendEmail('')
    setFriendName('')
  }

  async function handleCreateGroup(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCommunityError('')

    if (!groupName.trim()) {
      setCommunityError('Group name is required.')
      return
    }
    if (selectedFriendIds.length === 0) {
      setCommunityError('Select at least one friend for the group.')
      return
    }

    const members: GroupMember[] = selectedFriendIds.map((friendId, index) => ({
      friendId,
      role: index === 0 ? 'Coordinator' : 'Member',
      historyReliability: 70,
      commitmentConsistency: 70,
      responsePace: 70,
    }))

    const nextGroup: Group = {
      id: `group-${groupName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')}-${Date.now()}`,
      name: groupName.trim(),
      purpose: groupPurpose.trim() || 'General collaboration',
      members,
    }

    await persistCommunity(friends, [...groups, nextGroup])
    setGroupName('')
    setGroupPurpose('')
    setSelectedFriendIds([])
  }

  function toggleFriendSelection(friendId: string) {
    setSelectedFriendIds((prev) =>
      prev.includes(friendId) ? prev.filter((id) => id !== friendId) : [...prev, friendId]
    )
  }

  async function handleCreateGathering(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!actorId) {
      return
    }
    setCreateError('')

    const scheduledTime = new Date(createFormData.when)
    if (Number.isNaN(scheduledTime.getTime())) {
      setCreateError('Please choose a valid date and time.')
      return
    }

    setCreating(true)
    try {
      const createdId = await createMatch({
        organizerId: actorId,
        title: createFormData.title.trim() || 'New Gathering',
        description: createFormData.description,
        scheduledTime,
        durationMinutes: Number(createFormData.duration) || 90,
        location: createFormData.location.trim() || 'TBD',
        participantIds: [actorId],
      })

      if (!createdId) {
        setCreateError('Failed to create gathering.')
        return
      }

      await refresh()
      setCreateModalOpen(false)
      setCreateFormData({
        title: '',
        description: '',
        when: defaultWhenValue(),
        duration: '90',
        location: '',
      })
      navigate(`/matches/${createdId}`)
    } finally {
      setCreating(false)
    }
  }

  function openCreateModal() {
    setCreateError('')
    setCreateModalOpen(true)
  }

  async function handleInviteAccept(matchId: string) {
    if (!actorId) {
      return
    }
    await confirmMatch(matchId, actorId)
    await refresh()
  }

  return (
    <>
      <section className="panel">
        <div className="section-head">
          <h2>Upcoming Gatherings</h2>
          <Button variant="primary" onClick={openCreateModal}>+ Create Gathering</Button>
        </div>

        {loading ? <p className="subtle">Loading gatherings...</p> : null}
        {error ? <p className="subtle">{error}</p> : null}

        <div className="card-grid">
          {upcoming.map((g) => (
            <article key={g.matchId} className="card">
              <div className="card-head">
                <span className="type">Match</span>
                <span className={`state ${g.state}`}>{g.state}</span>
              </div>
              <h3>{g.title}</h3>
              <p>{g.scheduledTime.toLocaleString()}</p>
              <div className="meta">
                <span>{g.participantIds.length} members</span>
                <Button variant="ghost" onClick={() => navigate(`/matches/${g.matchId}`)}>View</Button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <Modal open={createModalOpen} title="Create New Gathering" onClose={() => setCreateModalOpen(false)}>
        <Form onSubmit={handleCreateGathering}>
          <FormGroup label="Title" required>
            <Input
              type="text"
              placeholder="Gathering title"
              value={createFormData.title}
              onChange={(event) => setCreateFormData((prev) => ({ ...prev, title: event.target.value }))}
              required
            />
          </FormGroup>
          <FormGroup label="Description">
            <TextArea
              placeholder="Describe the gathering..."
              value={createFormData.description}
              onChange={(event) => setCreateFormData((prev) => ({ ...prev, description: event.target.value }))}
              rows={3}
            />
          </FormGroup>
          <FormGroup label="When" required>
            <Input
              type="datetime-local"
              value={createFormData.when}
              onChange={(event) => setCreateFormData((prev) => ({ ...prev, when: event.target.value }))}
              required
            />
          </FormGroup>
          <FormGroup label="Duration (minutes)" required>
            <Input
              type="number"
              min="15"
              step="15"
              value={createFormData.duration}
              onChange={(event) => setCreateFormData((prev) => ({ ...prev, duration: event.target.value }))}
              required
            />
          </FormGroup>
          <FormGroup label="Location" required>
            <Input
              type="text"
              placeholder="Where will this gathering happen?"
              value={createFormData.location}
              onChange={(event) => setCreateFormData((prev) => ({ ...prev, location: event.target.value }))}
              required
            />
          </FormGroup>
          {createError ? <p className="auth-error">{createError}</p> : null}
          <div className="inline-actions">
            <Button variant="ghost" onClick={() => setCreateModalOpen(false)} disabled={creating}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" loading={creating} disabled={creating}>
              Create Gathering
            </Button>
          </div>
        </Form>
      </Modal>

      <section className="panel">
        <div className="section-head">
          <h2>Invitations</h2>
          <span className="subtle">{pendingCount} pending</span>
        </div>
        <div className="invite-list">
          {invitations.map((invite) => (
            <div key={invite.matchId} className="invite">
              <div>
                <strong>{invite.title}</strong>
                <p>{invite.scheduledTime.toLocaleString()}</p>
              </div>
              <div className="inline-actions">
                <Button variant="ghost" onClick={() => navigate('/invitations')}>Decline</Button>
                <Button variant="primary" onClick={() => void handleInviteAccept(invite.matchId)}>Accept</Button>
              </div>
            </div>
          ))}
          {invitations.length === 0 ? <p className="subtle">No pending invitations.</p> : null}
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Add Friend</h2>
          <span className="subtle">Invite by email</span>
        </div>
        <form className="form-inline" onSubmit={handleAddFriend}>
          <input
            type="email"
            placeholder="friend@email.com"
            value={friendEmail}
            onChange={(event) => setFriendEmail(event.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Name (optional)"
            value={friendName}
            onChange={(event) => setFriendName(event.target.value)}
          />
          <Button variant="primary" type="submit">Add Friend</Button>
        </form>
        {communityError ? <p className="auth-error">{communityError}</p> : null}
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Create Group</h2>
          <span className="subtle">Friends can belong to multiple groups</span>
        </div>
        <form className="form" onSubmit={handleCreateGroup}>
          <div className="form-inline">
            <input
              type="text"
              placeholder="Group name"
              value={groupName}
              onChange={(event) => setGroupName(event.target.value)}
              required
            />
            <input
              type="text"
              placeholder="Purpose"
              value={groupPurpose}
              onChange={(event) => setGroupPurpose(event.target.value)}
            />
            <Button variant="primary" type="submit">Create Group</Button>
          </div>
          <div className="friend-picker">
            {friends.map((friend) => (
              <label key={friend.id} className="friend-pick">
                <input
                  type="checkbox"
                  checked={selectedFriendIds.includes(friend.id)}
                  onChange={() => toggleFriendSelection(friend.id)}
                />
                <span>{friend.name}</span>
              </label>
            ))}
          </div>
        </form>
      </section>

      {actorId ? <AvailabilityCalendar slots={calendarSlots} /> : null}
      <FriendsList friends={friends} />
      <GroupsList groups={groups} friends={friends} />
    </>
  )
}
