# Comms
A Website and App bridging the gap in communication and organization for coaches and athletes.

## Running locally

The app is a FastAPI backend (Python) that serves the frontend and persists data in PostgreSQL. `Back.java` is an earlier, unrelated prototype left in the repo unused.

1. Start Postgres: `docker compose up -d`
2. Set up the backend:
   ```
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   alembic upgrade head
   ```
3. Run the server: `uvicorn app.main:app --reload --port 8000`
4. Open `http://localhost:8000/` and sign up for an account.
