# Geolocation and Media Analysis

## Table of Contents

- [Image Analysis](#image-analysis)
- [Reverse Image Search](#reverse-image-search)
- [Geolocation Techniques](#geolocation-techniques)
- [MGRS (Military Grid Reference System)](#mgrs-military-grid-reference-system)
- [Google Plus Codes / Open Location Codes (MidnightCTF 2026)](#google-plus-codes--open-location-codes-midnightctf-2026)
- [Metadata Extraction](#metadata-extraction)
- [Hardware/Product Identification](#hardwareproduct-identification)
- [Newspaper Archives and Historical Research](#newspaper-archives-and-historical-research)
- [Google Street View Panorama Matching (EHAX 2026)](#google-street-view-panorama-matching-ehax-2026)
- [Road Sign Language and Driving Side Analysis (EHAX 2026)](#road-sign-language-and-driving-side-analysis-ehax-2026)
- [Post-Soviet Architecture and Brand Identification (EHAX 2026)](#post-soviet-architecture-and-brand-identification-ehax-2026)
- [IP Geolocation and Attribution](#ip-geolocation-and-attribution)
- [Google Lens Cropped Region Search (UTCTF 2026)](#google-lens-cropped-region-search-utctf-2026)
- [Reflected and Mirrored Text Reading (UTCTF 2026)](#reflected-and-mirrored-text-reading-utctf-2026)
- [What3Words (W3W) Geolocation (UTCTF 2026)](#what3words-w3w-geolocation-utctf-2026)
- [Monumental Letters / Letreiro Identification (UTCTF 2026)](#monumental-letters--letreiro-identification-utctf-2026)
- [Google Maps Crowd-Sourced Photo Verification (MidnightCTF 2026)](#google-maps-crowd-sourced-photo-verification-midnightctf-2026)
- [Overpass Turbo Spatial Queries (LAB'OSINT 2025)](#overpass-turbo-spatial-queries-labosint-2025)
- [Music-Themed Landmark Geolocation with Key Encoding (BSidesSF 2026)](#music-themed-landmark-geolocation-with-key-encoding-bsidessf-2026)
- [AI Media in OSINT — Deepfake / Voice Clone Detection](#ai-media-in-osint--deepfake--voice-clone-detection)
- [Satellite / Aerial Imagery OSINT](#satellite--aerial-imagery-osint)

---

## Image Analysis

- Discord avatars: Screenshot and reverse image search
- Identify objects in images (weapons, equipment) -> find character/faction
- No EXIF? Use visual features (buildings, signs, landmarks)
- **Visual steganography**: Flags hidden as tiny/low-contrast text in images (not binary stego)
  - Always view images at full resolution and check ALL corners/edges
  - Black-on-dark or white-on-light text, progressively smaller fonts
  - Profile pictures/avatars are common hiding spots
- **Twitter strips EXIF** on upload - don't waste time on stego for Twitter-served images
- **Tumblr preserves more metadata** in avatars than in post images

## Reverse Image Search

- Google Lens (crop to specific region, best for identifying landmarks/shops/signs)
- Google Images (most comprehensive)
- TinEye (exact match)
- Yandex (good for faces, Eastern Europe)
- Baidu Images / `graph.baidu.com` (best for Chinese locations — use when visual cues suggest China: blue license plates, simplified Chinese text, menlou gate architecture)
- Bing Visual Search

## Geolocation Techniques

- Railroad crossing signs: white X with red border = Canada
- Use infrastructure maps:
  - [Open Infrastructure Map](https://openinframap.org) - power lines
  - [OpenRailwayMap](https://www.openrailwaymap.org/) - rail tracks
  - High-voltage transmission line maps
- Process of elimination: narrow by country first, then region
- Cross-reference multiple features (rail + power lines + mountains)
- MGRS coordinates: grid-based military system (e.g., "4V FH 246 677") -> convert online

## MGRS (Military Grid Reference System)

**Pattern (On The Grid):** Encoded coordinates like "4V FH 246 677".

**Identification:** Challenge title mentions "grid", code format matches MGRS pattern.

**Conversion:** Use online MGRS converter -> lat/long -> Google Maps for location name.

## Google Plus Codes / Open Location Codes (MidnightCTF 2026)

**Pattern (Chine Zhao):** Flag format requires a Google Plus Code (e.g., `H9G2+47X`) instead of coordinates or W3W. Plus Codes are Google's open-source alternative to street addresses.

**Format:** `XXXX+XX` (short/local) or `8FVC9G8F+6W` (full/global). Characters from the set `23456789CFGHJMPQRVWX`. The `+` separator is always present.

**Generating a Plus Code:**
1. Find the exact location on Google Maps
2. Click the map to drop a pin at the precise spot
3. The Plus Code appears in the location details panel (e.g., `H9G2+47X Handan, Hebei, China`)
4. Or enter coordinates in the Google Maps search bar — the Plus Code shows in results

**Precision:** Standard Plus Codes resolve to ~14m x 14m areas (vs. W3W's 3m x 3m). Adding extra characters increases precision. Meter-level position changes can alter the code.

**Key insight:** Unlike W3W (proprietary, requires API key), Plus Codes are free and built into Google Maps. When a flag format shows `{XXXX+XXX}`, recognize it as a Plus Code. Position the Street View camera at the exact photo capture location, then read the Plus Code from the map pin.

**Reference:** https://maps.google.com/pluscodes/

---

## Metadata Extraction

```bash
exiftool image.jpg           # EXIF data
pdfinfo document.pdf         # PDF metadata
mediainfo video.mp4          # Video metadata
```

## Hardware/Product Identification

**Pattern (Computneter, VuwCTF 2025):** Battery specifications -> manufacturer identification. Cross-reference specs (voltage, capacity, form factor) with manufacturer databases.

## Newspaper Archives and Historical Research

- Scout Life magazine archive: https://scoutlife.org/wayback/
- Library of Congress: https://www.loc.gov/ (newspaper search)
- Use advanced search with date ranges

**Pattern (It's News, VuwCTF 2025):** Combine newspaper archive date search with EXIF GPS coordinates for location-specific identification.

**Tools:** Library of Congress newspaper archive, Google Maps for GPS coordinate lookup.

## Google Street View Panorama Matching (EHAX 2026)

**Pattern (amnothappyanymore):** Challenge image is a cropped section of a Google Street View panorama. Must identify the exact panorama ID and coordinates.

**Approach:**
1. **Extract visual features:** Identify distinctive landmarks (road type, vehicles, containers, mountain shapes, building styles, vegetation)
2. **Narrow the region:** Use visual clues to identify country/region (e.g., Greenland landscape, specific road infrastructure)
3. **Compile candidate panoramas:** Use Google Street View coverage maps to find panoramas in the identified region
4. **Feature matching:** Compare challenge image features against candidate panoramas:
   ```python
   import cv2
   import numpy as np

   # Load challenge image and candidate panorama
   challenge = cv2.imread('challenge.jpg')
   candidate = cv2.imread('panorama.jpg')

   # ORB feature detection and matching
   orb = cv2.ORB_create(nfeatures=5000)
   kp1, des1 = orb.detectAndCompute(challenge, None)
   kp2, des2 = orb.detectAndCompute(candidate, None)

   bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
   matches = bf.match(des1, des2)
   score = sum(1 for m in matches if m.distance < 50)
   ```
5. **Ranking systems:** Use multiple scoring methods (global feature match, local patch comparison, color histogram analysis) and combine rankings
6. **API submission:** Submit panorama ID with coordinates in required format (e.g., `lat/lng/sessionId/nonce`)

**Google Street View API patterns:**
```python
# Street View metadata API (check if coverage exists)
# GET https://maps.googleapis.com/maps/api/streetview/metadata?location=LAT,LNG&key=KEY

# Street View image API
# GET https://maps.googleapis.com/maps/api/streetview?size=640x480&location=LAT,LNG&heading=90&key=KEY

# Panorama ID from page source (parsed from JavaScript):
# Look for panoId in page data structures
```

**Key insights:**
- Challenge images are often crops of panoramas — the crop region may not include horizon or sky, making geolocation harder
- Distinctive elements: road surface type, vehicle makes, signage language, utility poles, container colors
- Greenland, Iceland, Faroe Islands have limited Street View coverage — enumerate all panoramas in the region
- Image similarity ranking with multiple metrics (feature matching + color analysis + patch comparison) is more robust than any single method

---

## Road Sign Language and Driving Side Analysis (EHAX 2026)

**Pattern (date_spot):** Street view image of a coastal location. Identify exact coordinates from road infrastructure.

**Systematic approach:**
1. **Driving side:** Left-hand traffic → right-hand drive countries (Japan, UK, Australia, etc.)
2. **Sign language/script:** Kanji → Japan; Cyrillic → Russia/CIS; Arabic → Middle East/North Africa
3. **Road sign style:** Blue directional signs with white text and route numbers → Japanese expressways
4. **Sign OCR:** Extract text from directional signs to identify town/city names and route designations
5. **Route tracing:** Search identified route number + town names to find the road corridor
6. **Terrain matching:** Match coastline, harbors, lighthouses, bridges against satellite view

**Japanese infrastructure clues:**
- Blue highway signs with white Kanji + route numbers (e.g., E59)
- Distinctive guardrail style (galvanized steel, wavy profile)
- Concrete seawalls on coastal roads
- Small fishing harbors with white lighthouse structures

**General country identification shortcuts:**
| Feature | Country/Region |
|---------|---------------|
| Kanji + blue highway signs | Japan |
| Cyrillic + wide boulevards | Russia/CIS |
| White X-shape crossing signs | Canada |
| Yellow diamond warning signs | USA/Canada |
| Green autobahn signs | Germany |
| Brown tourist signs | France |
| Bollards with red reflectors | Netherlands |

---

## Post-Soviet Architecture and Brand Identification (EHAX 2026)

**Pattern (idinahui):** Coastal parking lot image. Identify location from architectural style, vehicle types, signage, and local brands.

**Recognition chain:**
1. **Architecture:** Brutalist concrete buildings → post-Soviet region
2. **Vehicles:** Reverse image search vehicle models to narrow to Russian/CIS market cars
3. **Script:** Cyrillic signage confirms Russian-language region
4. **Flags:** Regional government flags alongside national tricolor → identify specific federal subject
5. **Brands:** Named restaurants/chains (e.g., "Mimino" — Georgian-themed chain popular across Russia) → search for geographic distribution
6. **Coastal features:** Caspian Sea coastline + North Caucasus architecture → Dagestan/Makhachkala

**Key technique — restaurant/brand geolocation:**
- Identify any readable business name or brand logo
- Search for that business + "locations" or "branches"
- Cross-reference with other visual clues (coastline, terrain) to pinpoint exact branch
- Google Maps business search is highly effective for named establishments

**Post-Soviet visual markers:**
- Panel apartment blocks (khrushchyovka/brezhnevka)
- Wide boulevards with central medians
- Concrete bus stops
- Distinctive utility pole designs
- Soviet-era monuments and mosaics

---

## IP Geolocation and Attribution

**Free geolocation services:**
```bash
# IP-API (no key required)
curl "http://ip-api.com/json/103.150.68.150"

# ipinfo.io
curl "https://ipinfo.io/103.150.68.150/json"
```

**Bangladesh IP ranges (common in KCTF):**
- `103.150.x.x` - Bangladesh ISPs
- Mobile prefixes: +880 13/14/15/16/17/18/19

**Correlating location with evidence:**
- Windows telemetry (imprbeacons.dat) contains `CIP` field
- Login history APIs may show IP + OS correlation
- VPN/proxy detection via ASN lookup

---

## Google Lens Cropped Region Search (UTCTF 2026)

**Pattern (W3W1/W3W2):** Challenge image contains multiple elements but only one is useful for identification. Crop to just the relevant portion before searching.

**Technique:**
1. Identify the most distinctive element in the image (shop sign, building facade, landmark)
2. Crop the image to isolate that element — remove surrounding context that adds noise
3. Search the cropped region using Google Lens (`lens.google.com` or right-click → "Search image with Google Lens" in Chrome)
4. Review visually similar results to identify the specific location or business

**When to crop:**
- Shop fronts: crop to just the storefront and signage
- Landmarks: crop to the distinctive architectural feature
- Signs: crop to just the sign text
- Churches/buildings: crop to the unique facade

**Key insight:** Google Lens performs significantly better on cropped regions than full scene images. A full scene may return generic landscape results, while a cropped shop sign returns the exact business with its address.

**Example workflow (W3W2):**
1. Challenge image shows a street scene with a shop
2. Crop to just the shop portion
3. Google Lens identifies the shop and its location
4. Verify on Google Maps Street View
5. Convert coordinates to What3Words

---

## Reflected and Mirrored Text Reading (UTCTF 2026)

**Pattern (W3W3):** Text visible in the image is reflected/mirrored (e.g., sign reflected in water or glass). Must read the text in reverse to identify the location.

**Technique:**
1. Identify reflected text in the image (common in water reflections, glass surfaces, mirrors)
2. Flip the image horizontally to read the text normally
3. If text is partially obscured, search for the readable portion as a prefix/suffix:
   - "Aguas de Lind..." → search `"Aguas de Lind"` → find "Aguas de Lindoia"
4. Use the identified text to locate the place on Google Maps

**Partial text search strategies:**
```text
# Search with wildcards/partial terms
"Aguas de Lind"           # Quoted partial match
"Aguas de Lind" city      # Add context keyword
"Aguas de Lind*" brazil   # Add country if identifiable from image
```

**Image flipping for reflected text:**
```bash
# Flip image horizontally with ImageMagick
convert input.jpg -flop flipped.jpg

# Or with Python/PIL
python3 -c "
from PIL import Image
img = Image.open('input.jpg')
img.transpose(Image.FLIP_LEFT_RIGHT).save('flipped.jpg')
"
```

**Key insight:** When a letter in reflected text is ambiguous (e.g., "T" vs "I"), try both variants as separate searches. Partial text searches with quoted strings are effective for identifying place names even with only 60-70% of the text readable.

---

## What3Words (W3W) Geolocation (UTCTF 2026)

**Pattern (W3W1/W3W2/W3W3):** Photo of a location. Find the exact What3Words address (3-meter precision grid). Flag format: `utflag{word1.word2.word3}`.

**What3Words basics:**
- Divides entire world into 3m x 3m squares, each with a unique 3-word address
- Words are in a SPECIFIC language (English by default)
- Adjacent squares have COMPLETELY different addresses (no spatial correlation)
- Website: https://what3words.com/

**Workflow:**
1. **Identify the location** using standard geolocation techniques (reverse image search, landmarks, signs, architecture)
2. **Get precise GPS coordinates** from Google Maps satellite view
3. **Convert coordinates to W3W** using the website (enter coordinates in search bar)
4. **Fine-tune:** The exact 3m square matters — shift coordinates by small amounts to check adjacent squares

**Coordinate-to-W3W conversion:**
```text
# Navigate to what3words.com and enter coordinates:
# Format: latitude, longitude (e.g., 30.2870, -97.7415)
# Or click on the map at the exact location

# The W3W API requires an API key (not always available in CTF):
# GET https://api.what3words.com/v3/convert-to-3wa?coordinates=30.2870,-97.7415&key=API_KEY
```

**Common pitfalls:**
- **3m precision matters:** A building entrance vs. its parking lot may have different W3W addresses. Match the EXACT viewpoint of the photo.
- **Camera position vs. subject:** The W3W address may refer to where the camera IS, not what it's pointed at.
- **Satellite vs. street-level:** Google Maps pin may not perfectly align with the actual W3W grid.
- **Multiple buildings nearby:** Churches, shops, and landmarks may have several candidate squares.

**Tips for accurate pinpointing:**
- Use Google Street View to match the exact camera angle
- Cross-reference with OpenStreetMap (OSM) for precise building footprints
- Try 5-10 adjacent W3W addresses around your best guess
- The challenge image often shows a specific feature (entrance, sign, landmark) — find THAT exact spot
- **Micro-landmark matching:** Identify small distinctive features in the challenge image (utility poles, pathway rocks, bollards, planters) and locate the same features in Street View to pinpoint the exact 3m square
- **Background building triangulation:** Match buildings visible in the background from the challenge image angle. Find those same buildings in Street View, then determine where the camera must be positioned to produce the same perspective
- **Geographic feature narrowing:** When you know the city but not the exact spot, use distinctive geographic features (lakes, rivers, coastline) visible in the image to narrow the search area before switching to Street View

---

## Monumental Letters / Letreiro Identification (UTCTF 2026)

**Pattern (W3W3):** Photo of large 3D letters spelling a city/location name, often reflected in a pool of water. Common in Latin American cities as tourist landmarks.

**Identification clues:**
- Large colorful 3D block letters
- Often located in main plaza (praça) or tourist area
- May include city name in local language
- Reflection in decorative water pool is a common design

**Search strategy:**
- Google: `"letras monumentales" [city name]` or `"letreiro turístico" [city]`
- OpenStreetMap: search for nodes tagged as `tourism=attraction` near the city center
- Google Maps: search `[city name] sign` or `[city name] letters` and check photos

**Key insight:** These monumental letter installations ("letras monumentales" in Spanish, "letreiro turístico" in Portuguese) are extremely common in Latin American cities. The exact GPS coordinates of the installation can be found on OpenStreetMap or Google Maps photo pins.

---

## Google Maps Crowd-Sourced Photo Verification (MidnightCTF 2026)

**Pattern (Where was Chine):** Verify a candidate location by matching a challenge image against user-submitted Google Maps photos for that place.

**Workflow:**
1. Identify a candidate location name from other OSINT clues (Strava GPS routes, address research, social media posts)
2. Search the location name on Google Maps
3. Click the location pin and browse the **Photos** tab (user-submitted images)
4. Compare scene elements (buildings, trees, paths, water features, signage) against the challenge image
5. Match confirms the location — the place name is typically the flag

**When to use:** After narrowing to a candidate location through non-visual OSINT (fitness routes, addresses, social connections), use Google Maps photos as final visual confirmation. Especially useful for parks, plazas, and landmarks where many tourists upload photos.

**Key insight:** Google Maps aggregates crowd-sourced photos tagged to specific locations. Even when reverse image search fails (because the challenge image is original, not scraped), the same physical scene appears in tourist photos. Search by place name, not by image.

---

## Overpass Turbo Spatial Queries (LAB'OSINT 2025)

**Pattern (Portrait robot):** Find a specific business (newsagent) near a metro entrance in a known city. Overpass Turbo queries OpenStreetMap data to locate POIs by type within a radius of other POIs.

**Tool:** https://overpass-turbo.eu/

**Example — find newsagents within 10m of metro entrances in Barcelona:**
```text
[out:json][timeout:25];
{{geocodeArea:Barcelona}}->.searchArea;

(
  node["railway"="subway_entrance"](area.searchArea);
)->.metros;

(
  node(around.metros:10)["shop"~"newsagent|kiosk"];
  way(around.metros:10)["shop"~"newsagent|kiosk"];
);

out body;
>;
out skel qt;
```

**Common query patterns for OSINT:**
```text
# All cafes near train stations in a city
{{geocodeArea:CityName}}->.a;
node["railway"="station"](area.a)->.stations;
node(around.stations:50)["amenity"="cafe"];

# All ATMs in a neighborhood
node["amenity"="atm"]({{bbox}});

# Hotels near a specific coordinate (lat,lon)
node(around:200,48.8566,2.3522)["tourism"="hotel"];
```

**Key OSM tags for OSINT challenges:**

| Tag | Values |
|-----|--------|
| `shop` | `newsagent`, `kiosk`, `bakery`, `supermarket` |
| `amenity` | `cafe`, `restaurant`, `bank`, `atm`, `pharmacy` |
| `tourism` | `hotel`, `attraction`, `museum`, `viewpoint` |
| `railway` | `station`, `subway_entrance`, `halt` |

**Key insight:** When a challenge image shows a business near a transit stop in a known city, Overpass Turbo can narrow candidates to a handful of locations by querying for the business type within a small radius of transit nodes. Verify each result with Google Street View. The `around` operator (proximity filter) is the most useful feature — it replaces hours of manual map browsing.

---

## Music-Themed Landmark Geolocation with Key Encoding (BSidesSF 2026)

**Pattern (strike-a-coord):** 14 images of music-themed landmarks worldwide. For each location:
1. Identify the landmark via visual clues (signage, architecture, flags, distinctive features)
2. Each landmark has a musical connection (composer birthplace, concert hall, music museum)
3. A visual element at each location maps to a specific piano key number
4. The sequence of piano key numbers encodes the flag

Geolocation techniques used:
- **Signage/text:** Readable signs narrow to city/country (e.g., "BTHVN" = Beethoven birthplace in Bonn)
- **Architecture style:** Building materials, roof shapes, window designs identify regions
- **National flags/emblems:** Visible flags or government buildings identify country
- **Google Lens/reverse image search:** Match distinctive building facades
- **Street View confirmation:** Verify candidate locations via Google Street View

```python
# Piano key encoding: each landmark yields a key number (1-88)
# Key numbers map to characters
piano_keys = [35, 67, 42, ...]  # Recovered from each landmark

# Common encodings: direct ASCII, MIDI note numbers, or custom mapping
flag = ""
for key in piano_keys:
    # If keys map to ASCII: key + offset
    flag += chr(key + 32)  # Example offset
print(flag)
```

**Key insight:** Multi-location OSINT challenges combine traditional geolocation (landmark identification) with a secondary encoding layer. The "piano key" or "musical note" at each location extracts one character of the flag. Solve strategy: identify all locations first (the easier part), then determine the encoding scheme from the per-location data points.

**When to recognize:** Challenge provides multiple images with a musical or thematic thread. Each image requires individual geolocation. The flag isn't at any single location — it's encoded across all of them.

**References:** BSidesSF 2026 "strike-a-coord"

---

## AI Media in OSINT — Deepfake / Voice Clone Detection

**定位：识别"这是 AI 生成的"，然后继续 OSINT 链 — 不是媒体取证。** 当题目素材（图片/音频）是 AI 生成时，OSINT 侧只做两件事：① 用轻量信号确认"AI 生成"这个事实；② 据此改写后续搜索策略。真正的**取证**（ELA 错误级别分析、C2PA/内容凭证逐字段核验、DeepFake 检测模型逐帧跑）属于 `ctf-forensics/ai-media-forensics.md`，本文件只给 OSINT 视角的判断与行为。

**为什么必须先识别：** AI 生成图中的地标/物体是模型合成出来的（不存在真实对应物），Google Lens / TinEye 反查没有真实来源，反向地理搜索必然失败或返回幻觉结果 — 这是"该换思路"的关键信号。

**判断原则：** 单个信号不可靠 — 无 EXIF 也可能只是上传/截图剥离，畸形手也可能是低分辨率压缩伪影。至少**两个独立信号**叠加，才判定"AI 生成"。

**轻量检测速查（OSINT 视角信号，不是取证结论）：**
- 图片：文字扭曲/乱码（AI 写字常坏）、手指/手畸形、过多牙齿、皮肤头发过度平滑、左右不对称
- 无 EXIF：生成平台通常不写相机元数据（注意：上传/截图也会剥离 EXIF，单独用不可靠）
- 平台痕迹：Midjourney 右下角水印（早期版本）/ 生成图内嵌隐形水印与 C2PA 元数据（Stability AI 的 Stable Diffusion WebUI 输出带 C2PA，Chrome 图片详情可查；平台/版本相关，不确定时按线索处理）；第三方检测站（AI or Not、Sightengine、Hive Moderation、illuminarty）可作辅助线索 — 准确率有限、会限流漂移，**不能当判定依据**（不确定项）
- 音频（语音克隆）：听感异常 — 呼吸/停顿位置不自然、口吻连贯性差、共鸣与口音不稳；语音克隆常用 ElevenLabs / RVC / GPT-SoVITS 等（工具在变，确认具体样本时按线索走）
- 若素材是**视频**（DeepFake 换脸）：口型与音频错位、眨眼频率异常、面部光影闪烁 — OSINT 抓到"疑似合成"即可转向，逐帧判定归取证

**行为链（OSINT 侧）：**
1. 反查无结果或结果异常 → 怀疑 AI 生成
2. 叠加重检测信号（文字/手/无 EXIF/水印）确认
3. 分叉：
   - 题目问"哪些是假的" → 逐素材标注，用速查信号给出理由；flag 常藏在"唯一真图 / 唯一假图"的选取里
   - 题目给 AI 图要信息 → 图内景物是合成的，改挖**图外**线索：提示词/prompt、元数据、文件名、题目描述文本
4. 对 AI 图**不要**继续做街景/地标匹配 — 景物不对应任何真实位置

**语音克隆的 OSINT 应用：** 题目给"伪造的语音/音频"时，用它反查**真实来源**：找目标人物（话主）的公开音频（采访、演讲、发布会）做对照确定是谁，再定位原始发布渠道 — 真实来源通常埋着 flag 线索。频谱/波形级比对属取证的活，OSINT 用听感 + 来源检索即可。

**落地动作：** 把"反查了什么、结果如何"记进解题日志 — 反查失败本身是证据，帮助在 writeup 中区分"平台 API 漂移"与"素材真的是 AI 生成"。

---

## Satellite / Aerial Imagery OSINT

**定位：** 题目给俯视影像（卫星图/航拍图）求位置。先分清视角：Google Maps 的**卫星视图**是俯视照片，**街景**是地面 360° 视角 — 题目是俯视图就别拿街景匹配。

**平台（真实可用）：**
- Google Earth 历史影像（时间线对比）
- Sentinel Hub EO Browser — https://apps.sentinel-hub.com/eo-browser/ （免费，Sentinel-2 ~10m 分辨率，可逐日期查看）
- USGS EarthExplorer — https://earthexplorer.usgs.gov/ （Landsat 归档，需注册）
- NASA Worldview — https://worldview.earthdata.nasa.gov/ （每日影像、夜间灯光等图层）
- Esri World Imagery（作为底图参照，最新拼接）

**无坐标卫星图的定位特征：**
- 海岸线/岛屿轮廓形状 → 与 Google/OSM 地图轮廓比对（找"形状相同"的候选区域）
- 耕地纹理（几何地块、灌溉圈）→ 农业区特征；地块方向格网也有地域性
- 跑道方向与长度 → 机场，对照机场数据库缩到城市级
- 水体颜色、街区网格样式、屋顶/植被色调

**时间线对比：** 同一地区不同日期的影像（Google Earth 历史 / Sentinel 时间序列）找变化 — 新建建筑、植被变化、水域差异；配合题目给出的时间戳锁定考察时点。

**Metadata 先做：** EXIF GPS（`exiftool`）、文件属性、文件名、附带文档中的坐标 — 俯视图载体常自带坐标（衔接 [Metadata Extraction](#metadata-extraction)）。

**衔接：** 地面细节推理见 [Geolocation Techniques](#geolocation-techniques)；输出坐标时用 [MGRS](#mgrs-military-grid-reference-system) 或 Plus Code（`XXXX+XX`）。CTF 常见问法：给定只有地形/海岸的俯视图 → 判区域 → 逐级缩到地物 → 落坐标 → 按题目要求转 MGRS / Plus Code / W3W。
