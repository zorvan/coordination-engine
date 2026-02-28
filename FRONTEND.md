# FRONTEND DESIGN

## GLOBAL LAYOUT ARCHITECTURE

### 1.1 Layout Structure

Desktop:

```
[ Sidebar ]  [ Top Navigation Bar ]
              [ Main Content Area ]
```

Mobile:

```
[ Top Nav ]
[ Main Content ]
[ Bottom Tab Bar ]
```

### 1.2 Persistent Navigation

Sidebar (Desktop)

Sections:

- Dashboard
- My Gatherings
- Invitations (badge count)
- Create Gathering (+ CTA button)
- Profile
- Settings
- Logout

Collapsed state supported.

#### Top Navigation Bar

Elements:

Left:

- App Logo (click → Dashboard)

Center:

- Global Search (future-ready)

Right:

- Notifications Bell (badge)
- User Avatar (dropdown menu)

Dropdown Menu:

- My Profile
- My Gatherings
- Settings
- Logout

## 2. AUTHENTICATION FLOW

### 2.1 Login Screen

Minimal, centered card.

Elements:

- Logo
- Headline: “Coordinate Better.”
- Email Input
- Password Input
- Login Button
- Divider
- Google Login Button
- Link: Create Account
- Link: Forgot Password

Error Handling:

- Inline error messages
- Disabled button while loading
- Toast on failure

### 2.2 Registration Screen

Fields:

- Name
- Email
- Password
- Confirm Password
- Create Account Button

After success:
→ Onboarding Flow

### 2.3 Onboarding Flow

Step 1:

- Upload avatar
- Select activity interests (multi-select tags)

Step 2:

- Invite 3–5 friends (copy link or email)

Step 3:

- CTA: “Create Your First Gathering”

Skip allowed.

## 3. DASHBOARD

### 3.1 Sections

Upcoming Gatherings

Card grid layout.

Each card shows:

- Title
- Type icon
- Date (if locked)
- Member count
- Status badge
- Viability indicator (if voting)

Invitations

If any:

- Horizontal scroll list
- Accept / Decline inline buttons

Past Gatherings

Collapsed by default.

### 3.2 Gathering Card Component

States:

- Draft (gray badge)
- Voting (blue badge)
- Locked (green badge)
- Cancelled (red badge)

Voting state shows:

- “X% viable”
- Deadline countdown

Click → Gathering Detail Page

## 4. GATHERING DETAIL PAGE

Tabbed layout:

Tabs:

- Overview
- Availability
- Constraints
- Members

Top Section:

- Title
- Type
- Organizer avatar
- Status badge
- Deadline
- Action buttons (if organizer)

### 4.1 Overview Tab

Sections:

Time Options List

Shows:

- Date
- Rank position
- Viability indicator
- Regret score
- Enthusiasm indicator

Expandable:
“How ranking works”

Location Options (if any)
Lock / Extend / Cancel (Organizer Only)

### 4.2 Availability Tab

Core interface.

Grid Matrix:

Rows:

- Member avatars

Columns:

- Time slots

Cell interaction:
Click cycles:
No → Prefer Not → Yes → Strong Yes

Color system:

- No = red 400
- Prefer Not = amber 400
- Yes = green 300
- Strong Yes = green 600

Below grid:

Ranking Panel

Each slot displays:

- ✔ Viable or ⚠ Below threshold

- ⚖ Regret score

- 🔥 Strong Yes count

- Final rank number

Real-time update when inputs change.

Mobile:
Horizontal scroll with sticky member column.

### 4.3 Constraints Tab

Layout:
Member accordion list.

Inside each member section:

Options:

- If X attends → I attend

- If X attends → I prefer not

- Confidence slider (0–100)

Display:
Visual connection lines between avatars (simple graph view)

Conflict indicator:
If mutual exclusion → warning banner.

### 4.4 Members Tab

List view:

Each member shows:

- Avatar
- Name
- Activity reliability badge
- Participation rate %
- Response speed indicator

Organizer sees:

- Remove member option
- Transfer organizer (future-ready placeholder)

## 5. CREATE GATHERING FLOW

Modal-based wizard.

Step 1 – Basic Info

- Title

- Type selector (icon grid)

- Description (optional)

- Deadline picker

Step 2 – Invite Members

- Search bar

- Friend list

- Invite via link button

Step 3 – Add Time Options

- Add date picker

- Add time range

- Add multiple options

Step 4 – Review & Create

After creation:
Status = Voting
Redirect to detail page.

## 6. PROFILE PAGE

Sections:

### 6.1 Header

- Avatar

- Name

- Edit Profile button

### 6.2 Activity Context Section

Displays:

- Reliability score per activity

- Attendance rate %

- Expertise tag (Beginner / Casual / Skilled / Pro)

### 6.3 Gatherings History

List of past gatherings with:

- Status

- Attendance result

### 6.4 Edit Profile Modal

Editable:

- Name

- Avatar

- Activity interests

Not editable:

- Reputation metrics

## 7. GROUP / CIRCLE MEMBERSHIP VIEW

Accessible via Profile or Sidebar.

Shows:

- Circles list

- Members inside each circle

- Shared gatherings

Future-ready:
Add circle (disabled in V1 if not implemented backend-side).

## 8. NOTIFICATION SYSTEM

### 8.1 Notification Bell

Dropdown list:

Each notification:

- Icon

- Message

- Timestamp

- Click → deep link

Types:

- Invitation received

- Deadline approaching

- Ranking updated

- Constraint affecting you

- Slot locked

- Gathering cancelled

Unread indicator:
Blue dot.

Mark as read on click.

## 9. STATE MANAGEMENT

### 9.1 Global State (Zustand)

- Auth state

- Sidebar collapse state

- Modal visibility

- Toast queue

### 9.2 Server State (React Query)

- Gatherings

- Invitations

- Notifications

- Profile data

Real-time sync:
WebSocket or Firebase listeners.

## 10. ERROR & EDGE STATES

Must design UI for:

- No gatherings yet → Empty state illustration

- No invitations

- No viable slots → Warning card

- All slots below threshold → Suggest adding more options

- Member left gathering → System notice banner

- Deadline passed without lock → Organizer alert banner

## 11. ACCESS CONTROL (Frontend)

UI visibility rules:

Organizer sees:

- Lock button

- Extend deadline

- Cancel gathering

- Remove members

Members see:

- Availability input

- Constraint editor (self only)

Guests (invited but not accepted):

- Limited view

- Accept / Decline only

## 12. RESPONSIVENESS

Breakpoints:

Mobile:
Single column
Sticky bottom action bar

Tablet:
2-column layout for matrix

Desktop:
Full matrix visible

Matrix must support:

- Horizontal scroll

- Sticky first column (members)

## 13. DESIGN SYSTEM RULES

Visual tone:
Clean, neutral, calm.

Primary color:
Blue for coordination actions.

Success:
Green.

Warning:
Amber.

Danger:
Red.

Rounded corners:
2xl

Shadow:
Soft only.

No heavy gradients.
No gamification UI.

## 14. PERFORMANCE REQUIREMENTS

- Optimistic UI for availability input

- Debounced updates (300ms)

- Skeleton loaders for data fetch

- No full-page reload transitions

- Route-level code splitting

## 15. FUTURE-READY HOOKS (But Hidden)

Frontend structure must allow:

- Payment modal insertion

- Commitment tier badges

- Auto-assignment AI suggestions

- Calendar sync indicator

Do not expose in UI yet.

## FINAL FRONTEND OBJECTIVE

The interface must:

- Make coordination feel structured

- Make ranking feel fair

- Make decision reasoning visible

- Avoid algorithm opacity

- Avoid visual complexity

The UI is not decorative.

It is social infrastructure.
