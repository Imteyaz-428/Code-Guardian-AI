# Code Guardian AI — Frontend

React + Vite single-page app for Code Guardian AI. Lets you point at a
repository path, triggers a static risk analysis via the backend API, and
displays per-function risk scores with details.

## Stack

- React 19
- Vite
- Plain CSS (theme variables in `src/App.css`)

## Getting started

```bash
npm install
npm run dev
```

The dev server runs on the default Vite port and expects the backend API to
be reachable (see below).

## Configuration

The API base URL defaults to `http://127.0.0.1:8000`. Override it by setting
`VITE_API_URL` in a `.env` file or your environment:

```bash
VITE_API_URL=https://api.example.com npm run dev
```

## Scripts

- `npm run dev` — start the dev server with HMR
- `npm run build` — production build to `dist/`
- `npm run preview` — preview the production build locally
- `npm run lint` — run ESLint

## Project structure

```
src/
  components/   UI components (form, results table, details panel, etc.)
  hooks/        useRepositoryAnalysis — owns request/loading/error state
  services/     api.js — fetch wrapper for the backend /analyze endpoint
  utils/        risk.js — sorting/formatting helpers for findings
```
