# Hospital Readmission Governance UI

Investor-facing replay dashboard for `readmission_results.json`.

## 1) Generate replay output

From repo root:

```bash
python3 -m syntropiq.demo.readmission.run
```

This writes:

- `syntropiq/demo/readmission/outputs/readmission_results.json`

## 2) Run UI

```bash
cd syntropiq/demo/readmission/ui
npm install
npm run dev
```

UI runs at:

- `http://localhost:5174`

`predev` automatically executes `npm run sync-results` to copy latest JSON into:

- `ui/public/readmission_results.json`

## Scripts

- `npm run sync-results` copy latest backend results into `public`
- `npm run dev` start dev server
- `npm run build` type-check + build
- `npm run preview` preview production build
