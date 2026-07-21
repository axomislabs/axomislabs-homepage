# Axomis Labs — Homepage

Static one-page site for Axomis Labs at **axomislabs.com**. No build step, no
dependencies, no third-party requests at runtime — plain HTML and CSS, deployed to
GitHub Pages.

```
site/                    ← everything here is published
  index.html
  styles.css
  CNAME                    custom domain, read by GitHub Pages at deploy time
  robots.txt
  sitemap.xml
  assets/
    logo-full.svg          full lockup (traced vector)
    logo-full-light.svg    light variant for dark backgrounds
    logo-mark.svg          A/X mark only
    logo-mark-light.svg    light variant of the mark
    favicon.svg            inverts itself on dark browser chrome
    favicon-32/180/512.png raster fallback for older Safari/iOS
    og-image.png           1200×630 social share card (must stay raster)
    logo-*.png             raster masters, kept for non-web use
    fonts.css              @font-face declarations
    fonts/                 Inter + Manrope, latin subsets (OFL 1.1)
tools/
  build-logo-assets.py   regenerates every asset above from the master image
Branding/                ← source material, deliberately NOT published
.github/workflows/deploy.yml
```

## Local preview

```bash
python3 -m http.server 8000 --directory site
# → http://localhost:8000
```

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`, which publishes `./site`
to GitHub Pages. Only that folder is uploaded, so `Branding/` stays out of the
published site.

One-time setup:

1. **Settings → Pages → Build and deployment → Source**: select **GitHub Actions**.
2. Add the DNS records below at Porkbun.
3. **Settings → Pages → Custom domain**: enter `axomislabs.com` and save.
4. Tick **Enforce HTTPS** once the certificate is issued.

Because this deploys through a custom Actions workflow rather than from a branch,
GitHub does *not* write a `CNAME` file into the repo — `site/CNAME` is committed
here instead, and the workflow ships it with the artifact. Keep it.

> **Note:** GitHub Pages on a private repository requires a paid plan (Pro/Team/
> Enterprise). On the free tier the repository must be public, which also makes
> `Branding/` publicly readable.

### DNS records at Porkbun

Delete Porkbun's default parking records first (an `A` record on the root and an
`ALIAS`/`CNAME` on `www`), then add:

| Type  | Host  | Answer                          |
|-------|-------|---------------------------------|
| A     | *(blank)* | `185.199.108.153`           |
| A     | *(blank)* | `185.199.109.153`           |
| A     | *(blank)* | `185.199.110.153`           |
| A     | *(blank)* | `185.199.111.153`           |
| CNAME | `www` | `axomislabs.github.io`           |

Optionally add `AAAA` records on the root for IPv6: `2606:50c0:8000::153`,
`2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`.

## Brand reference

Values are defined once as CSS custom properties at the top of `site/styles.css`.

| Role       | Colour       | Hex       |
|------------|--------------|-----------|
| Primary    | Charcoal     | `#2E3133` |
| Accent     | Burnt Copper | `#B66A3C` |
| Secondary  | Olive Sage   | `#68724D` |
| Neutral    | Stone        | `#D7CFC3` |
| Background | Ivory        | `#F7F5F0` |

Headings are Manrope; body text is Inter. Both are self-hosted from `site/assets/fonts/`
so the site makes no requests to Google — relevant for GDPR compliance in the EU.

Copper at full strength measures 3.7:1 against ivory, which is below the WCAG AA
threshold for small text. `--accent-ink` (`#8F4F28`, 5.8:1) carries small labels and
links; full copper is reserved for display type, rules, and decorative elements.

## Regenerating the logo assets

The only true source is `Branding/Axomislabs - Logo.png` — a flat RGB render on a
white plate. Everything in `site/assets/` is derived from it:

```bash
brew install potrace
python3 tools/build-logo-assets.py
```

The script converts the white plate to alpha, splits the lockup into its three brand
inks by colour, and traces each ink separately so the result keeps its own fill. It
is deterministic: re-running reproduces the committed files byte for byte.

Two constants in that script were tuned against this specific image and are worth
understanding before changing:

- `BLUR = 2` smooths scan texture that would otherwise become visible wobble along
  straight strokes. Above 2, the hairline rules beside the tagline erode away.
- `TURDSIZE = 400` discards speckles from the render's texture. The real glyphs are
  300px+ in area while the noise is under 40px, so the threshold sits in a wide gap.

If a genuine vector original of the logo ever turns up, prefer it over this trace.
