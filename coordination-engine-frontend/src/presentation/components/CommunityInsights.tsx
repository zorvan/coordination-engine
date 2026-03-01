import React from 'react'

export type CommitmentDegree = 'soft' | 'moderate' | 'firm' | 'locked'

export type AvailabilitySlot = {
  day: string
  period: string
  status: 'free' | 'busy'
  matchState?: 'proposed' | 'confirmed' | 'completed'
  probability: number
  commitment: CommitmentDegree
  eventTitle?: string
}

export type Friend = {
  id: string
  email: string
  name: string
  relationship: string
  trustScore: number
  reliability: number
  lastInteraction: string
  groupIds: string[]
}

export type GroupMember = {
  friendId: string
  role: string
  historyReliability: number
  commitmentConsistency: number
  responsePace: number
}

export type Group = {
  id: string
  name: string
  purpose: string
  members: GroupMember[]
}

type AvailabilityCalendarProps = {
  slots: AvailabilitySlot[]
}

export function AvailabilityCalendar({ slots }: AvailabilityCalendarProps) {
  const periods = Array.from(new Set(slots.map((slot) => slot.period)))
  const days = Array.from(new Set(slots.map((slot) => slot.day)))

  const byKey = new Map<string, AvailabilitySlot>()
  for (const slot of slots) {
    byKey.set(`${slot.period}-${slot.day}`, slot)
  }

  return (
    <section className="panel">
      <div className="section-head">
        <h2>Availability Calendar</h2>
        <span className="subtle">Free/busy + confidence + commitment degree</span>
      </div>
      <div className="availability-calendar">
        <div className="availability-row availability-header">
          <div className="availability-cell period">Time Slot</div>
          {days.map((day) => (
            <div key={day} className="availability-cell day">
              {day}
            </div>
          ))}
        </div>

        {periods.map((period) => (
          <div key={period} className="availability-row">
            <div className="availability-cell period">{period}</div>
            {days.map((day) => {
              const slot = byKey.get(`${period}-${day}`)
              if (!slot) {
                return (
                  <div key={`${period}-${day}`} className="availability-cell slot">
                    -
                  </div>
                )
              }

              return (
                <div
                  key={`${period}-${day}`}
                  className={`availability-cell slot ${slot.status} commitment-${slot.commitment} ${slot.matchState ? `state-${slot.matchState}` : ''}`}
                >
                  <strong>{slot.status === 'busy' ? 'Busy' : 'Free'}</strong>
                  {slot.matchState ? <span>{slot.matchState}</span> : null}
                  <span>{slot.probability}% probability</span>
                  <span>{slot.commitment} commitment</span>
                  {slot.eventTitle ? <em>{slot.eventTitle}</em> : null}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </section>
  )
}

type FriendsListProps = {
  friends: Friend[]
}

export function FriendsList({ friends }: FriendsListProps) {
  return (
    <section className="panel">
      <div className="section-head">
        <h2>Friends</h2>
        <span className="subtle">{friends.length} individuals</span>
      </div>
      <div className="friend-list">
        {friends.map((friend) => (
          <article key={friend.id} className="friend-card">
            <div className="friend-main">
              <strong>{friend.name}</strong>
              <span className="subtle">{friend.relationship}</span>
            </div>
            <p className="subtle">{friend.email}</p>
            <div className="metric-row">
              <span>Trust</span>
              <progress max={100} value={friend.trustScore} />
              <span>{friend.trustScore}</span>
            </div>
            <div className="metric-row">
              <span>Reliability</span>
              <progress max={100} value={friend.reliability} />
              <span>{friend.reliability}</span>
            </div>
            <p className="subtle">Last interaction: {friend.lastInteraction}</p>
            <p className="subtle">Groups: {friend.groupIds.length}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

type GroupsListProps = {
  groups: Group[]
  friends: Friend[]
}

export function GroupsList({ groups, friends }: GroupsListProps) {
  const friendNameById = new Map(friends.map((friend) => [friend.id, friend.name]))

  return (
    <section className="panel">
      <div className="section-head">
        <h2>Groups</h2>
        <span className="subtle">{groups.length} memberships</span>
      </div>
      <div className="group-list">
        {groups.map((group) => (
          <article key={group.id} className="group-card">
            <div className="group-head">
              <div>
                <h3>{group.name}</h3>
                <p className="subtle">{group.purpose}</p>
              </div>
              <span className="state draft">{group.members.length} members</span>
            </div>
            <div className="group-member-table">
              <div className="group-member-row header">
                <span>Member</span>
                <span>Role</span>
                <span>History</span>
                <span>Commitment</span>
                <span>Response</span>
              </div>
              {group.members.map((member) => (
                <div key={`${group.id}-${member.friendId}`} className="group-member-row">
                  <span>{friendNameById.get(member.friendId) || member.friendId}</span>
                  <span>{member.role}</span>
                  <span>{member.historyReliability}</span>
                  <span>{member.commitmentConsistency}</span>
                  <span>{member.responsePace}</span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
