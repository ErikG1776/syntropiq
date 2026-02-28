# Infra Chain UI

Production-style monitoring dashboard for `infra_chain_results.json`.

## Run

1. Generate demo output (from repo root):

```bash
python3 syntropiq/demo/infra_chain/src/run_infra_chain.py
```

2. Start UI:

```bash
cd syntropiq/demo/infra_chain/ui
npm install
npm run dev
```

The `predev` hook runs `npm run sync-results`, which copies:

- source: `../outputs/infra_chain_results.json`
- target: `public/infra_chain_results.json`

UI fetches `/infra_chain_results.json`.

## Scripts

- `npm run sync-results`: copy latest simulation output into `public/`
- `npm run dev`: start Vite dev server
- `npm run build`: type-check and build
- `npm run preview`: preview production build
