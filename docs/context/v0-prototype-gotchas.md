# v0 / Vercel / Next.js Prototype Gotchas

Reference doc capturing lessons learned from building and deploying v0-generated prototypes. Read this before touching any prototype repo.

## v0 Output Patterns

### 1. `ignoreBuildErrors` is intentional
`next.config.mjs` ships with `typescript: { ignoreBuildErrors: true }`. v0 ALWAYS does this. TS errors don't block `next build`, so Vercel deploys succeed even with warnings. **DO NOT remove this.**

### 2. Tailwind v4 (CSS-native config)
v0 uses Tailwind v4 which is CSS-native — no `tailwind.config.js`. Configuration lives in CSS:
```css
@import 'tailwindcss';
@theme inline {
  --font-sans: 'Inter', sans-serif;
  /* ... */
}
```
- Uses `@tailwindcss/postcss` PostCSS plugin (NOT `tailwindcss`)
- Adding a `tailwind.config.js` will CONFLICT with the CSS-based config
- Don't use `@tailwind base/components/utilities` directives — those are Tailwind v3

### 3. Two `globals.css` files
- `app/globals.css` — themed, imported by `layout.tsx`. **This is the real one.**
- `styles/globals.css` — shadcn default scaffold, NOT imported anywhere.
- Only edit `app/globals.css`.

### 4. pnpm lockfile
v0 uses pnpm. Vercel auto-detects the package manager from `pnpm-lock.yaml`. Running `npm install` creates a second lockfile (`package-lock.json`) and causes build conflicts. Either use `pnpm install` or don't install locally at all.

### 5. Font loading (double import trap)
v0 imports `Geist`/`Geist_Mono` via `next/font/google` in `layout.tsx` but assigns them to unused `_geist` variables. The actual font is set in CSS via `@theme inline { --font-sans: 'Inter', ... }`. Don't add duplicate font imports.

### 6. SPA routing, not file-based
`app/page.tsx` is `'use client'` with `useState` for page switching — NOT Next.js App Router file-based routing. URLs don't change on navigate. This is how v0 builds multi-page prototypes.

### 7. shadcn/ui components.json is a scaffold only
v0 generates its own components in `components/shared/` (Button, Card, etc.) — these are NOT shadcn/ui CLI output. The `components.json` file exists for potential future `npx shadcn` additions only.

### 8. React 19 + Next.js 16
Bleeding edge versions. Some peer dependency warnings are expected. `ignoreBuildErrors` handles this gracefully.

### 9. `@vercel/analytics`
Included by default in v0 output. Works automatically in Vercel deployments. May error in non-Vercel environments — this is fine.

### 10. `tw-animate-css`
v0 uses `tw-animate-css` for animations via `@import 'tw-animate-css'` in globals.css. This is different from `tailwindcss-animate` (Tailwind v3 plugin).

## Deployment Rules

### NEVER modify v0's design
Don't change colors, fonts, layout, or component structure. The v0 output is a cohesive design system. Any "improvements" will break visual consistency. The prototype is meant to look like v0 designed it.

### Git author must be `readytogoai <matt@readytogo.ai>`
Vercel requires commit authors with contributing access to the connected repo. Commits by `33prime` don't have deploy access on `readytogo-ai` repos. Always configure the git author before committing:
```bash
git config user.name "readytogoai"
git config user.email "matt@readytogo.ai"
```

### NEVER commit `node_modules`
Ensure `.gitignore` has `node_modules/`. If you clone and run `pnpm install` locally, verify before committing.

### Bridge injection is the ONLY code modification
The only changes we make to v0's output:
1. `public/aios-bridge.js` — the bridge script file
2. One `<Script>` tag in `app/layout.tsx`

Nothing else. No visual changes, no dependency additions, no config modifications.

### Don't remove `ignoreBuildErrors`
v0 relies on this for clean builds despite TS warnings from bleeding-edge React 19 / Next.js 16.

### Iframe embedding requires custom headers
By default, Vercel/Next.js sets `X-Frame-Options: SAMEORIGIN`, which blocks embedding in the workbench iframe. The bridge injector automatically adds these headers to `next.config.mjs`:
```js
async headers() {
  return [{
    source: '/(.*)',
    headers: [
      { key: 'X-Frame-Options', value: 'ALLOWALL' },
      { key: 'Content-Security-Policy', value: 'frame-ancestors *' },
    ],
  }];
}
```
This is injected automatically by `bridge_injector.py`. If you're manually fixing a prototype, add this to the `nextConfig` object.

### Preview deployments require auth (use production)
Vercel preview deployments on private repos require Vercel authentication (401 error). Always deploy to **production** (push to `main` branch) for iframe embedding. Don't try `vercel.json` with `deploymentProtection: { preview: "disabled" }` — it causes build errors.

### Private repo clone needs authenticated URL
The system git is configured as `33prime`, which can't access `readytogo-ai` repos. The ingest endpoint uses an authenticated clone URL with the GitHub PAT: `https://x-access-token:<PAT>@github.com/readytogo-ai/<repo>.git`. This is handled automatically by the ingest endpoint.

### v0 GitHub export may be incomplete
The v0 "Deploy to GitHub" export can miss files that exist in the v0 preview. If the deployed version has build errors from missing files, let v0 fix itself — it will create a PR on the repo. Use v0's fix branch, don't try to manually reconstruct missing files.

## Bridge Injection Details

**Target file:** `app/layout.tsx`

**Steps:**
1. Add `import Script from 'next/script'` after the last import line
2. Add `<Script src="/aios-bridge.js" strategy="afterInteractive" />` before `</body>`
3. The v0 layout typically has `<Analytics />` before `</body>` — inject AFTER Analytics
4. Bridge file goes to `public/aios-bridge.js`

**Example layout.tsx diff:**
```diff
 import { Analytics } from "@vercel/analytics/react"
+import Script from 'next/script'

 // ...

       {children}
       <Analytics />
+      <Script src="/aios-bridge.js" strategy="afterInteractive" />
     </body>
```
