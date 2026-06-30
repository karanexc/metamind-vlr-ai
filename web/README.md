# VLR Analytics Web

Next.js frontend for the VLR Analytics product.

## Setup

```bash
# Install deps (first time)
npm install

# Copy env template
cp .env.local.example .env.local
```

The default `.env.local` points at `http://localhost:8000`. Make sure your
FastAPI backend is running there.

## Development

```bash
# Backend (in another terminal, from project root)
cd ..
./scripts/run_api.sh

# Frontend (this directory)
npm run dev
```

Open http://localhost:3000.

## Stack

- Next.js 14 (App Router)
- Tailwind CSS
- Framer Motion (animations)
- Lucide React (icons)
- Recharts (charts)

## Pages

- `/` — Home with stats, recent matches, top performers
- `/predict` — Match prediction (the headline feature)
- `/match-analysis` — AI-generated match breakdown
- `/fantasy` — Custom roster simulation
- `/teams` — Team explorer
- `/players` — Player explorer
