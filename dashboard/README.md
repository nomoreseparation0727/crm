# dashboard

Next.js app reading the Burgundy tracker's Postgres database. See the repo
root [`README.md`](../README.md) for the full architecture, local setup, and
Railway deploy steps.

Quick start (assumes `DATABASE_URL` already points at a migrated DB):

```bash
npm install
cp .env.local.example .env.local
npm run dev
```
