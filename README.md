# Coach Studio

A web app that lets a coach send session plans and feedback to individual athletes and track their progress across training blocks, replacing the group chats and paper notes most clubs run on.

I built this because I coach badminton, and the coordination problem is real: plans get buried in chat threads, feedback isn't tied to the session it came from, and nobody can see whether a player has actually improved over a training block. The app puts sessions, feedback, and athletes into one data model so that history is queryable instead of scrolled for.

**Stack:** HTML · CSS · JavaScript · Python (FastAPI) · PostgreSQL

---

## Features

- **Session plans** — a coach creates a session, attaches drills and notes, and assigns it to one or more athletes.
- **Structured feedback** — feedback is written against a specific session rather than as free-floating messages, so every comment keeps its context.
- **Progress across training blocks** — sessions group into blocks, letting a coach see an athlete's history in order instead of as a flat list.
- **Athlete view** — each athlete sees only their own plans and feedback.
- **Responsive layout** — usable on a phone at the side of a court, which is where coaches actually enter feedback.

---

## Architecture

The browser layer handles form input, rendering, and client-side validation in plain HTML, CSS, and JavaScript, with no framework. Below it, a Python (FastAPI) application layer holds the domain logic and the relationships between the three core entities.

| Entity | Holds | Relationships |
| `Athlete` | name, contact, training group | has many sessions, has many feedback entries |
| `Session` | date, drills, plan notes, training block | belongs to a coach, assigned to athletes |
| `Feedback` | body, rating, timestamp | belongs to one session and one athlete |

Modelling feedback as a child of both a session and an athlete — rather than as a message with a sender and a recipient — is the decision the whole app rests on. It's what makes "show me everything I've told this player about their net play this block" a query rather than a search.

---

## What I'd build next

- Deploy it so coaches can use it without running anything locally.
- Rebuild the front end in React with TypeScript — the current vanilla JS rendering is the part that gets hardest to extend as views multiply.
- Email notifications when a coach publishes feedback.

---

## Notes on the code

The interface was built from scratch in HTML, CSS, and JavaScript, including the responsive breakpoints and the form validation. Python (FastAPI) handles the domain logic and the relationships between athletes, sessions, and feedback. The project was built incrementally, so the commit history reflects how it actually came together rather than arriving in one drop.

Questions or suggestions are welcome via issues.
