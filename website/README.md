# NigraniAI website (static)

The public NigraniAI website: plain HTML, CSS and JavaScript. No build step, nothing to install.

| File | What it is |
|---|---|
| `index.html` | Home: hero with a live product illustration, the problem, all 11 tools (filterable), three spotlights (explainable anomalies, tamper-evident evidence, layered PII detection), how it works, the DPDP Act explained (roles, duties → tools, breach clocks, penalties, countdown to 13 May 2027, FAQ), pricing (setup · hosted · self-hosted, plan tiers without prices), demo booking |
| `company.html` | Company: mission, vision, story, principles, contact (email, phone, office) |
| `css/style.css` | Brand system and every section, responsive down to phones, respects reduced motion |
| `js/main.js` | Navigation, scroll reveals, tool filter, hero animation, countdown, cookie banner, booking form |
| `js/config.js` | Supabase URL and **anon** key for demo bookings |
| `assets/` | Full logo, transparent eye mark (300 px and 900 px), round mark (app icon), favicon |

## Run locally

```bash
cd website
python3 -m http.server 3011
# open http://localhost:3011
```

## Demo bookings (Supabase)

The form posts straight to the Supabase REST API, table `demo_bookings` (schema in `supabase/schema.sql`; run it once in the Supabase SQL editor).
Row Level Security allows the anon key to **insert** a booking and nothing else, so the key is safe in
the browser. A hidden field stops simple bots. Bookings appear in Supabase → Table editor → `demo_bookings`.

## Deploy

Live on **Vercel**: https://nigrani-ai.vercel.app (project `nigrani-ai`, connected to the GitHub repo,
Root Directory `website`). Every push to `main` redeploys it automatically. `vercel.json` marks it as a
plain static site (no install or build), turns on clean URLs (`/company`) and adds security headers.
Any other static host works too: upload this folder.

## Making changes

1. Edit the HTML, CSS or JS directly and check the page locally (desktop and phone width, browser
   console with no errors).
2. Open a pull request (see the main [README](../README.md#8-working-together-forks-branches-and-pull-requests)).
3. Once it is merged into `main`, Vercel publishes it within about a minute.
