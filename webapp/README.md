# QuizUzup — web portal

React + Vite + Tailwind frontend for the Quiz Bot's web portal. Pro users
get a login (issued by the bot via `/webportal`) to take any quiz and
review/retry a personal "Mistakes" list.

See the root [`README.md`](../README.md) for how this fits together with
the bot and the FastAPI backend (`../webapi/`).

## Dev

```bash
cp .env.example .env   # VITE_API_URL -> the backend's URL
npm install
npm run dev
```

## Build

```bash
npm run build   # -> dist/, deploy as a static site (Vercel, Netlify, etc.)
```
