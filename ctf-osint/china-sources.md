# China-Specific OSINT Sources / 中国区情报源

Chinese-language challenges and challenges whose clues point at mainland-China platforms need a
different toolkit from the English-language default. This file covers that gap.

> **Verification status — read this first.** Everything marked **[WP-verified]** was read out of a
> published Chinese-CTF writeup and reflects what solvers actually did. Everything marked
> **[unverified]** is a pointer to a public resource that **could not be exercised from this
> offline environment** (no access to mainland sites). Per-platform anti-bot behaviour and login
> walls change fast — treat **[unverified]** entries as leads to confirm live, not as tested fact.

## Table of Contents

- [Flag Format Convention](#flag-format-convention)
- [When the Clue Points at China](#when-the-clue-points-at-china)
- [Map Platforms: Amap Beats Google](#map-platforms-amap-beats-google)
- [Zhihu as an Intelligence Source](#zhihu-as-an-intelligence-source)
- [Cropped Region Search on Chinese Scenes](#cropped-region-search-on-chinese-scenes)
- [Baidu Reverse Image Search](#baidu-reverse-image-search)
- [Corporate and ICP Records](#corporate-and-icp-records)
- [Post-2015 Platform Reality Check](#post-2015-platform-reality-check)
- [Reference Lists (External)](#reference-lists-external)

---

## Answer Format for Chinese Geolocation Tasks

> **The flag format always comes from the challenge, never from convention.** The wrapper
> (`SICTF{...}`, `flag{...}`, plaintext), the field order and the separators are all whatever the
> challenge description or the event rules declare — see `ctf-routing/routing/triage.md`, which is
> authoritative. Nothing below overrides a challenge statement.

With that understood, what follows is an **observed pattern in past events**, useful for knowing
what the answer text generally looks like once the format is known:

**[WP-verified]** Chinese geolocation challenges have commonly accepted an
**administrative-division path** as the answer text — big-to-small, underscore-separated, in
Chinese — i.e. `省_市_区_地点` *inside* whatever wrapper the challenge specifies.

Observed SICTF answers:

| Clue | Accepted flag |
|---|---|
| Park with a lake, Hainan | `SICTF{海南省_海口市_琼山区_红城湖公园}` |
| Mall with a Ferris wheel behind it | `SICTF{广东省_珠海市_斗门区_大信新都汇}` |
| Sports centre, Sichuan | `SICTF{四川省_达州市_通川区_凤凰大道376号_达州市体育中心}` |

How to use this:

- **Read the challenge's stated format first**, then use the pattern above only to decide what to
  put *inside* the wrapper. If the challenge asks for a coordinate, a landmark name, or a
  different field order, follow the challenge.
- **When the challenge is silent on format**, the administrative path is the highest-probability
  answer text for a Chinese geolocation task — including the province, since one SICTF task
  explicitly required a `__省` field after a wrong city-only guess.
- **Depth is not fixed.** The deepest field is not always 区; one answer carried an extra
  street-address field (`凤凰大道376号`). Match the level of detail the clues support.
- **Write place names in Chinese**, not pinyin or English (`广东省`, not `Guangdong`), unless the
  challenge states otherwise.
- Submit through `ctf-match-ops` discipline: trim whitespace, confirm the wrapper, and do not
  spend limited attempts on a format the challenge did not ask for.

## When the Clue Points at China

**[WP-verified]** Visual cues that narrow a scene to mainland China before any search:

- **Simplified Chinese** signage (vs. traditional for HK/Macau/Taiwan).
- **Blue license plates** — mainland civilian plates. (Green = new-energy vehicles; yellow =
  large/commercial vehicles; black = foreign/embassy.)
- **Menlou (门楼) gate architecture**, Chinese-style park and campus entrances.
- Mobile-payment QR codes, shared-bike clusters, Chinese telecom branding.

## Map Platforms: Amap Beats Google

**[WP-verified]** Do not assume Google Earth is authoritative for Chinese POIs. In a documented
SICTF case, Google Earth identified the site as a school (第八中学) and the answer was rejected;
switching to **Amap (高德地图)** produced the correct answer, `达州市体育中心`.

Working rule: use Google for the coarse fix (which city), then **confirm the exact POI on
Amap/Baidu Maps**, because mainland POI databases are denser and more current than Google's for
China. Chinese map platforms also label with local names that match the flag's expected spelling.

- Amap (高德地图) — POI detail, street-level browsing.
- Baidu Maps (百度地图) — alternative POI and panoramic coverage.

**[unverified]** Both are mainland-hosted; expect to need a browser session. There is no reliable
offline path.

## Zhihu as an Intelligence Source

**[WP-verified]** When reverse image search fails, **search the descriptive Chinese phrase on
Zhihu (知乎)** rather than only on Google. A documented SICTF case was solved by describing the
scene's two salient features in Chinese — a mall with a Ferris wheel behind it — which surfaced a
Zhihu answer naming the location (珠海 大信新都汇). The writeup's own summary flags this as
unexpected but effective.

This works because Chinese-language users post landmark-identification threads on Zhihu that never
appear in Western image-search indexes. Treat it as a **first-class fallback**, not a last resort:

```
「<landmark feature 1> <landmark feature 2> 在哪」    e.g. 商场 摩天轮 在哪
```

Other Chinese-language text sources worth the same treatment: 百度知道, 小红书, 微博, 贴吧,
and Bilibili comment sections.

## Cropped Region Search on Chinese Scenes

**[WP-verified]** Full-frame reverse image search frequently fails on Chinese scenes. The
documented fix is to crop **aggressively** to one distinctive object:

- One SICTF task failed completely when the whole image was framed on Google, and succeeded once
  the solver isolated **just the Spider-Man and spider-web artwork** on a building facade, then
  searched that crop.
- The general rule already in `geolocation-and-media.md` (Google Lens crop-to-region) applies, but
  Chinese scenes reward **smaller crops** — isolate shop signs, storefront names, or single murals.

Once a crop yields a hit, walk the street in Amap/Google Earth to find the exact camera position.
Note that the **camera position and the landmark need not share an address** — in that same case
the shot was taken on a cross street (`Strand Str`), not on the street the landmark is named for
(`Loop Str`).

## Baidu Reverse Image Search

**[WP-verified]** Baidu Images / `graph.baidu.com` is the correct first choice when the visual
cues indicate China. It indexes mainland content that Google and TinEye miss. Use it **before**,
not after, Google for mainland scenes.

## Corporate and ICP Records

**[unverified]** For "domain → owning entity → other assets" pivots, the mainland equivalent of
WHOIS-plus-corporate-registry is:

| Source | What it gives |
|---|---|
| 工信部 ICP 备案查询 (beian.miit.gov.cn) | Which entity a domain is filed under, and the filing number |
| 天眼查 / 企查查 | Company registration, subsidiaries, shareholders, affiliated domains and apps |
| 国家企业信用信息公示系统 | Official company registration records |
| ENScan_GO (tool, see below) | Automates aggregation of 控股公司 / ICP / APP / 小程序 / 微信公众号 |

Chinese WHOIS is typically privacy-redacted far more aggressively than gTLD WHOIS, so the **ICP
filing record is usually the higher-yield pivot** — that is the structural difference from the
Western workflow in `web-and-dns.md`.

## Post-2015 Platform Reality Check

**[WP-verified, negative]** Do **not** rely on Twitter/X, Tumblr or BlueSky reaching Chinese
targets. Accounts and content relevant to a Chinese challenge live on mainland platforms, and
**Weibo / WeChat public accounts / Douyin / Xiaohongshu / Zhihu / Bilibili / Tieba** are where the
trail actually is. The `social-media.md` playbook (Snowflake IDs, Nitter, Wayback CDX, homoglyph
stego) simply has no coverage here.

Conversely, mainland platforms are far more hostile to automated collection: login walls, signed
requests, and per-account rate limits are the norm. If a challenge hinges on scraping one, budget
for manual browsing.

## Reference Lists (External)

**[unverified]** — these are pointers to public collections. They are maintained by third parties
for journalism / fact-checking rather than for CTF, and their contents were **not** reviewed from
this environment (the GitHub pages returned only navigation chrome to the fetch tool).

| Resource | Description |
|---|---|
| [OSINT-Tools-China](https://github.com/paulpogoda/OSINT-Tools-China) | Curated list of China OSINT tools, aimed at profilers and fact-checkers |
| [chinese_osint_search_dorks](https://github.com/ArgeliusLabs/chinese_osint_search_dorks) | Bilingual field guide: Baidu, Chinese-language query pivots, public records, verification |
| [OSINT-CSE](https://github.com/paulpogoda/osint-cse) | Custom search engines for OSINT |
| [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) | Collector for 小红书/抖音/微博/B站/知乎/快手/贴吧 |
| [ENScan_GO](https://github.com/wgpsec/ENScan_GO) | Corporate/ICP/APP/小程序/公众号 aggregation |
| 中国事实核查手册 (chinafactcheck.com) | Chinese fact-checking manual; its verification methodology transfers to geolocation work |

**Caveat on tooling**: automated collectors for mainland platforms sit in a legal and ethical grey
zone and their APIs break frequently. For CTF purposes, prefer manual browsing plus the
text-search pivots above; do not build a solution that depends on a scraper staying functional.

## Sources

The **[WP-verified]** material above comes from published Chinese-CTF writeups:

- SICTF OSINT writeup (5 tasks, geolocation): <https://blog.csdn.net/2301_80100022/article/details/136179346>
- HNCTF 2022 "线下单杀出题人" (OSINT): <https://www.nssctf.cn/note/set/13220>
- Social engineering in CTF-MISC, incl. GitHub-avatar tracing and Weibo pivots:
  <https://blog.csdn.net/stem5/article/details/155693054>

Treat these as *evidence of what worked in one event*, not as universal rules.
