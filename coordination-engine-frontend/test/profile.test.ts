// jest globals are provided at runtime by the test runner.  declare them
// here so TypeScript is happy without needing to resolve additional modules.

declare const describe: any;
declare const it: any;
declare const expect: any;

import { mapActorToProfile } from '../src/presentation/pages/ProfilePage'

// We only export the helper for testing (we will export it below in the file).

describe('mapActorToProfile helper', () => {
  const fallback = {
    name: 'Fallback Name',
    email: 'fallback@example.com',
    phone: '111-2222',
    bio: 'fallback bio',
    location: 'Nowhere',
    website: 'fallback.com',
  }

  it('uses values from actor when provided', () => {
    const actor: any = {
      name: 'Alice',
      email: 'alice@example.com',
      phone: '123',
      bio: 'hello',
      location: 'City',
      website: 'site.com',
    }
    const profile = mapActorToProfile(actor, fallback)
    expect(profile).toEqual(actor)
  })

  it('falls back only when fields are missing or not strings', () => {
    const actor: any = {
      name: null,
      email: undefined,
      // phone omitted entirely
      bio: 42,
    }
    const profile = mapActorToProfile(actor, fallback)
    expect(profile.name).toBe(fallback.name)
    expect(profile.email).toBe(fallback.email)
    expect(profile.phone).toBe(fallback.phone)
    // invalid types leave fallback
    expect(profile.bio).toBe(fallback.bio)
    expect(profile.location).toBe(fallback.location)
    expect(profile.website).toBe(fallback.website)
  })

  it('allows empty strings (clearing) to be returned', () => {
    const actor: any = {
      name: '',
      email: '',
      phone: '',
      bio: '',
      location: '',
      website: '',
    }
    const profile = mapActorToProfile(actor, fallback)
    expect(profile).toEqual(actor) // empties should propagate
  })
})
