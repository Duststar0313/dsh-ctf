# CTF OSINT — Public Intelligence

Scope: obtaining information from **public sources** alone — social platform accounts and posts, images and metadata, geolocation, domains and DNS, public records (WHOIS/FEC/Tor), code hosting and bots, and identifying unknown data.

Out of scope: extracting from local files and traffic captures (pivot to `ctf-forensics`); active exploitation of online services (pivot to `ctf-web`); analysis after finding a sample/trojan (pivot to `ctf-malware`).

> This file is the **local decision layer**: it references only **filenames** under the `ctf-osint` skill and does not duplicate their contents.
> Usage: first determine the **form of the clue** (account / image / domain / record / port), then read only that one corresponding file.
>
> **Timeliness:** much OSINT content is attributed to a specific event year, and third-party
> endpoints (X/Twitter, Tumblr, BlueSky, Tor Metrics, image-search frontends) drift over time. A
> documented command failing is usually API drift, not a wrong technique — re-derive the request
> from the platform's current UI.

## File Index

| File | Contents | When to read |
|---|---|---|
| `social-media.md` | Twitter/X (numeric User ID, Snowflake timestamps, Nitter, memory.lol, Wayback CDX), Tumblr, BlueSky search and API, Unicode homoglyph steganography, Discord API, username OSINT (namechk, whatsmyname, Osint Industries), username metadata mining (postal codes), platform false positives, multi-platform chaining, Strava routes | The clue is an account, username, or social post |
| `geolocation-and-media.md` | Image analysis, reverse image search (including Baidu), **AI-media / deepfake & voice-clone recognition**, Google Lens crop-region search, mirrored-text reading, geolocation (railway signs, infrastructure maps, MGRS, **satellite/aerial imagery**), Google Plus Codes, EXIF/metadata, hardware identification, newspaper archives, IP geolocation, Street View panorama matching, What3Words micro-landmark matching, crowdsourced map photo verification, Overpass Turbo spatial queries | Given a photo/video, need to pin down the location, read metadata, match a streetscape, **an image/audio that may be AI-generated (deepfake / voice clone)**, or an overhead satellite/aerial view |
| `web-and-dns.md` | Google dorking (including TBS image filtering), Google Docs/Sheets enumeration, DNS reconnaissance (TXT, zone transfer), Wayback Machine, FEC political donations, Tor relay lookups, GitHub repository analysis, Telegram bot investigation, WHOIS (reverse/historical/IP-ASN), nmap fingerprinting of fake service banners | The clue is a domain, DNS, repository, public record, or suspicious port |
| `china-sources.md` | Mainland-China sources: `省_市_区_地点` flag convention, China visual cues (blue plates, simplified text, menlou), Amap/Baidu Maps over Google for POIs, Zhihu and Chinese-language text pivots, Baidu reverse image search, 工信部 ICP / 天眼查 corporate records, why Twitter/Tumblr/BlueSky do not reach Chinese targets | The challenge or its clues point at mainland China — Chinese text, Chinese platforms, or a scene that reverse image search only resolves on Baidu |

## Decision Tree

- Given an image/video → first read metadata and EXIF with `exiftool` / `identify -verbose`, then reverse image search → `geolocation-and-media.md`
- **Clue suggests mainland China** (simplified Chinese text, blue license plates, menlou gates, `.cn` domain, mainland platform) → do **not** default to the English-language playbook: use Baidu image search, confirm POIs on Amap, and fall back to Zhihu text search → `china-sources.md`
- **Answer must be a place and the challenge is a Chinese event** → the flag format still comes from the challenge; when it is unstated, Chinese geolocation answers commonly use the `省_市_区_地点` administrative path → `china-sources.md`
- **Domain → owning entity** on a `.cn`/mainland target → ICP filing record (工信部) and 天眼查/企查查, since Chinese WHOIS is heavily redacted → `china-sources.md`
- Reverse image search performs poorly → use **Google Lens crop** to a distinctive region (signage, building facade) and search again → `geolocation-and-media.md`
- Text in an image is mirrored/reflected → flip horizontally, then search quoted fragments → `geolocation-and-media.md`
- Need to pin down a location → railway signs / street sign OCR / building and brand style / lane direction → `geolocation-and-media.md`
- Coordinates are a grid or short code → MGRS `4V FH 246 677` or Plus Code `XXXX+XXX` → `geolocation-and-media.md`
- Suspected Street View crop → panorama matching (feature extraction + multi-metric ranking) → `geolocation-and-media.md`
- Reverse image search returns nothing plausible (or results look hallucinated) **and the image shows AI tells** (distorted text, malformed hands, no EXIF, generator watermark) → treat it as AI-generated: recognition only, then pivot to prompt/metadata/filename clues and continue the OSINT chain → `geolocation-and-media.md`; media **forensics** (ELA, C2PA) → `ctf-forensics/ai-media-forensics.md`
- Clue is an audio clip possibly cloned from a known person (deepfake voice) → light listening + comparison against the target's public audio to identify the real speaker/source → `geolocation-and-media.md` (spectral/waveform analysis is forensics)
- Clue is a satellite/aerial top-down image (coastline, fields, runway visible, no street-level detail) → identify terrain features and timeline-compare, then output coordinates → `geolocation-and-media.md`
- Clue is a username → check cross-platform with whatsmyname / namechk; **watch for platform false positives** → `social-media.md`
- Clue is X/Twitter → numeric User ID (still valid after rename), reverse the timestamp from the Snowflake, pull history via Nitter/Wayback → `social-media.md`
- A social post looks normal but may hide data → Unicode homoglyph steganography (ASCII=0, homoglyph=1) → `social-media.md`
- Clue is a domain → `dig -t any` / `-t txt`, try a zone transfer `axfr`, `whois` (including reverse and historical) → `web-and-dns.md`
- Clue is a code repository → use `gh api` to inspect issue comments, PR reviews, commit messages, wiki edits → `web-and-dns.md`
- Looking for public documents/leaked spreadsheets → dorking syntax; for Google Docs/Sheets try `/export?format=csv`, `/gviz/tq?tqx=out:csv`, `/htmlview` → `web-and-dns.md`
- Port is open but behavior is wrong → `nmap -sV` fingerprinting; fake service banners often contain the flag directly → `web-and-dns.md`
- Got a 40-character hex string → SHA-1 (Tor fingerprint), look up the relay family on Tor metrics → `web-and-dns.md`
- Political donation clue → check committee receipts on FEC.gov; note that 501(c)(4) masks the original funders → `web-and-dns.md`

## Common Entry Points

- `exiftool image.jpg` to read EXIF → `geolocation-and-media.md`
- Google Lens crop-region search → `geolocation-and-media.md`
- Cross-platform username enumeration (whatsmyname) → `social-media.md`
- Twitter Snowflake timestamp: `(id >> 22) + 1288834974657` → `social-media.md`
- Unicode homoglyph steganography → `social-media.md`
- `dig axfr` zone transfer → `web-and-dns.md`
- Wayback CDX to pull historical snapshots → `web-and-dns.md`
- `gh api` to dig up hidden clues in a repository → `web-and-dns.md`
- Shodan search for servers by SSH host key fingerprint → `web-and-dns.md`
- nmap fingerprinting of fake service banners → `web-and-dns.md`
- China / Chinese-language scene: Baidu reverse image, Amap POI confirmation, Zhihu phrasing → `china-sources.md`
- Chinese CTF geolocation answers commonly use `省_市_区_地点` (Chinese characters, province included) — but always follow the format the challenge states → `china-sources.md`

## Related Directions

- Local files/traffic captures already in hand and extraction or carving is needed → `ctf-forensics`
- Provenance/authenticity **forensics** of AI media (ELA, C2PA field-level checks, deepfake detection models on frames) → `ctf-forensics/ai-media-forensics.md`; the osint direction only recognizes "AI-generated" as a fact and continues the chain
- Pivot to active exploitation of an online HTTP service → `ctf-web`
- Malicious samples, beacons, or suspicious binaries found during intelligence gathering → `ctf-malware`

## Maintenance

- Linked to the `ctf-osint` skill via the identically named directory; after files are added or removed upstream, the `## File Index` table in this file must be updated in sync.
- After changing the `SKILL.md` frontmatter, verify the YAML is valid: invalid frontmatter makes dsh **silently ignore the entire skill**.
