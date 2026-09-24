# Sentinel frontend

Vite + React dashboard. Deploys to Vercel (Root Directory = `frontend`).

## Dev
```bash
npm install
cp .env.example .env        # set VITE_API_URL to your backend
npm run dev                 # http://localhost:5173
```

## Deploy to Vercel
1. Import repo at vercel.com/new.
2. Root Directory = `frontend`, Framework = Vite, Output = `dist`.
3. Env var: `VITE_API_URL` = your Railway backend URL.
