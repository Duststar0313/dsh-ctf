# CTF Forensics — Forensics, Steganography and Signals

Scope: recovering information from **existing artifacts** — disk images, memory dumps, PCAP, logs and browser traces, image/audio/video steganography, USB and peripheral traffic, hardware signal decoding, 3D printing files.

Out of scope: open-source intelligence (go to `ctf-osint`); active exploitation of an online service (go to `ctf-web`); analyzing the malicious behavior of a sample (go to `ctf-malware`); reversing firmware/drivers (go to `ctf-reverse`).

> This file is the **local decision layer**: it references only **filenames** under the `ctf-forensics` skill and does not duplicate their contents.
> Usage: **identify the carrier type first** (disk/memory, network, image, audio/video, peripheral, signal, host artifacts), then read only the one corresponding file.

## File Index

| File | Contents | When to read |
|---|---|---|
| `disk-and-memory.md` | Disk/memory core: Volatility, mounting and carving, VM/OVA/VMDK, VMware snapshots, GIMP raw memory visualization, coredump, Windows KAPE, PowerShell ransomware, Android, **iOS backup forensics**, Docker containers, **Kubernetes/cloud-native (etcd, kubeconfig, image layers), JVM heap dump (.hprof)**, cloud storage, BSON reconstruction, TrueCrypt/VeraCrypt mounting | Given a disk image, memory dump or coredump; **a kubeconfig / etcd snapshot / container image tar (OCI layout); a `.hprof` heap dump**; mobile backup |
| `disk-advanced.md` | Advanced disk/memory: deleted partitions, ZFS, GPT GUID encoding, VMDK sparse parsing, memory string carving, ransomware key recovery, WordPerfect macro XOR, minidump ISO9660 recovery, APFS snapshots, RAID 5 XOR recovery, HFS+ resource forks, Kyoto Cabinet hash database, SQLite edit-history reconstruction | Basic mounting/carving is not enough; filesystem or RAID layer anomalies |
| `disk-recovery.md` | Recovery and extraction: LUKS master key recovery, PRNG timestamp seed brute force, VBA macro binary recovery, FemtoZip decompression, XFS reconstruction, tar duplicate entries, nested filesystems, null-byte interleaved anti-carving, BTRFS subvolumes/snapshots, FAT16 free space and deleted file recovery (fls/icat), ext2 orphan inodes via fsck, corrupted ZIP header repair, **SQLite WAL/deleted page recovery** | Files were deleted/encrypted/hidden and must be recovered |
| `network.md` | Network basics: tcpdump, TLS/SSL keylog decryption, extracting TLS master key from coredump, Wireshark, PCAP, port scanning, SMB3 decryption, 5G/NR, WordPress reconnaissance, credentials, USB HID steganography, BCD encoding, HTTP upload exfiltration, reordering split archives by timestamp | Given a PCAP, using conventional protocol analysis |
| `network-advanced.md` | Advanced network: packet-interval timing encoding, NTLMv2 cracking, TCP flag covert channel, DNS last-byte steganography and tail-byte binary encoding, multi-layer PCAP (XOR+ZIP+mDNS key), Brotli decompression bomb seam, SMB RID reuse (LSARPC), Timeroasting (MS-SNTP), dnscat2 reassembly, RADIUS shared secret brute force, RC4 stream identification, ICMP payload rotation, ICMP delay covert channel | Traffic looks normal but hides data, or the protocol is obscure |
| `peripheral-capture.md` | USB/HID/Bluetooth peripheral traffic reconstruction: USB HID mouse/drawing-pen trajectory recovery, keyboard capture decoding, keyboard LED Morse exfiltration, arrow-key navigation trajectory, Bluetooth RFCOMM packet reassembly | Given a USB/Bluetooth capture |
| `steganography.md` | General steganography: binary border steganography, PDF multi-layer, SVG keyframes, PNG permutation, file overlays, GIF frame-difference Morse, GZSteg+spammimic, table frequency recovery, Kitty terminal graphics protocol, ANSI escape sequences, autostereograms, byte+row two-layer interleaving, multi-stream video containers, progressive PNG layer XOR, curved-surface reflection QR reconstruction | The steganographic carrier is a PDF/SVG/GIF/container/text rather than an ordinary image |
| `stego-image.md` | Image steganography: JPEG unused DQT table LSB, BMP bit-plane QR, image puzzle rearrangement, F5 DCT ratio detection, PNG unused palette entries, QR block reconstruction, seeded pixel permutation + multi-bit-plane QR, JPEG thumbnail pixel mapping, conditional LSB with pixel filtering, JPEG slack space, nearest-neighbor interpolation steganography, RGB parity steganography | The carrier is an image |
| `stego-advanced.md` | Advanced steganography part 1 (audio and signals): FFT frequency domain, DTMF, SSTV+LSB, DotCode barcode, custom dual-tone keyboard, multi-track differential subtraction, cross-channel multi-bit LSB, audio FFT notes, audio metadata octal, nested tar whitespace encoding, DeepSound with password, waveform binary encoding, QR hidden in spectrogram | The carrier is audio, or frequency-domain analysis is needed |
| `stego-advanced-2.md` | Advanced steganography part 2 (video and image transforms, format-specific): video frame accumulation, reversed audio, frame averaging, JPEG XL TOC permutation, Arnold cat map restoration, high-resolution SSTV custom FM demodulation, MJPEG trailing-byte steganography, EXIF zlib+Stegano pixel pattern, PDF xref covert channel, ANSI escapes, pixel-level ECB deduplication | The carrier is video, or image-transform restoration is needed |
| `linux-forensics.md` | Linux/application forensics: log analysis, **Log4j/Log4Shell trace analysis**, Docker images, attack chains, browser credentials, Firefox history, TFTP, weak TLS RSA, USB audio, Git directory recovery, KeePass v4 brute force, Git reflog/fsck recovery, browser traces (Chrome/Chromium/Firefox history, cookies, downloads, localStorage, session restore), corrupted git blob byte brute-force repair, VBA macro cell restoration to ELF, Python memory source recovery via pyrasite | The carrier is logs (incl. **Log4Shell/JNDI lookup strings**), a browser directory, a Git repository or application data |
| `windows.md` | Windows forensics: registry, SAM, event logs, Recycle Bin, NTFS alternate data streams, USN journal, PowerShell history, Defender MPLog, WMI persistence, Amcache | The carrier is Windows host artifacts |
| `signals-and-hardware.md` | Hardware signal decoding (including decoding code): VGA frame parsing, HDMI TMDS symbol decoding, DisplayPort 8b/10b + LFSR descrambling, Voyager Golden Record audio, Saleae Logic 2 UART decoding, Flipper Zero `.sub`, side-channel power analysis (DPA), keyboard acoustic side channel, CD audio image steganography (CIRC deinterleaving + spiral rendering), Caps Lock LED Morse in video, Linux `input_event` keylogger dump, serial UART in WAV, USB MIDI Launchpad grid reconstruction | The carrier is logic-analyzer/oscilloscope data, hardware signals or a side channel |
| `3d-printing.md` | 3D printing forensics (PrusaSlicer binary G-code, QOIF, heatshrink) | The carrier is a 3D printing file/G-code |
| `blockchain.md` | Blockchain/EVM on-chain forensics: calldata decoding, storage slots, event logs, transaction trace/call replay, Bitcoin UTXO peel chain | The evidence is on-chain or includes a transaction hash/contract address |
| `email.md` | Email/mailbox forensics: EML/MBOX/Maildir parsing, RFC 2047 encoded headers, attachment extraction, Outlook PST/OST | The artifact is an email message, mailbox or PST/OST file |
| `ai-media-forensics.md` | AI-generated media forensics: image (ELA limitations, GAN/diffusion fingerprints, FFT/noise statistics, over-smoothing), audio (spectrogram smoothness, missing silences, TTS/vocoder artifacts), provenance (C2PA manifests via `c2patool`, latent watermarks, prompt/seed traceback from PNG tEXt chunks) | Image/audio/video is suspected AI-generated or a deepfake; "which one is AI"; need C2PA/watermark/provenance checks |

## Decision Tree

- **Identify the carrier first**, then choose a file; the table below gives entry points by carrier
- Disk image / memory dump / coredump → `disk-and-memory.md`; filesystem-layer or RAID anomalies → `disk-advanced.md`; files deleted/encrypted that need recovery → `disk-recovery.md`
- Kubernetes/cloud-native (kubeconfig, etcd snapshot, container image tar / OCI layout) or a JVM `.hprof` heap dump → `disk-and-memory.md`
- Full-disk encryption (LUKS/VeraCrypt/TrueCrypt) → for master key recovery see `disk-recovery.md`, for mounting see `disk-and-memory.md`
- PCAP, conventional protocols → `network.md`; with a keylog or coredump → decrypt TLS first, still in `network.md`
- PCAP content looks normal but may hide data (timing, flags, DNS last byte, ICMP) → `network-advanced.md`
- USB/Bluetooth capture → `peripheral-capture.md`
- Image → `stego-image.md`
- Audio/signal (FFT, DTMF, SSTV, spectrum) → `stego-advanced.md`
- Video, or need frame accumulation/averaging/transform restoration → `stego-advanced-2.md`
- Image/audio/video suspected AI-generated (deepfake, "which one is AI", C2PA/watermark checks) → `ai-media-forensics.md`; but if the goal is to reverse-search a (possibly AI-looking) image back to a real source, that is OSINT → `ctf-osint`
- PDF / SVG / GIF / container / text steganography → `steganography.md`
- Windows host artifacts (registry, SAM, USN, Amcache) → `windows.md`
- Linux/application artifacts (logs incl. **Log4Shell/JNDI lookup strings**, browser, Git, Docker, KeePass) → `linux-forensics.md`
- Hardware signals, logic analyzer, side channel → `signals-and-hardware.md`
- Email message, mailbox, PST/OST → `email.md`
- Blockchain/EVM transaction, contract storage, event logs, UTXO peel chain → `blockchain.md`
- 3D printing / G-code → `3d-printing.md`
- Unsure of the carrier → run `file` on the artifact and check the file header, then return to this decision tree

## Common Entry Points

- TLS decryption: keylog file, or extract master key from coredump → `network.md`
- USB HID keyboard/mouse trajectory recovery → `peripheral-capture.md`
- Memory dump string carving → `disk-and-memory.md`, `disk-advanced.md`
- Deleted file recovery (FAT16 `fls`/`icat`, ext2 orphan inode `fsck`) → `disk-recovery.md`
- Image bit-plane/LSB extraction of QR → `stego-image.md`
- Audio FFT / DTMF / SSTV → `stego-advanced.md`
- Video frame accumulation/differencing → `stego-advanced-2.md`
- Registry / SAM / event logs → `windows.md`
- Browser history and credentials → `linux-forensics.md`
- Logic analyzer UART/SPI decoding → `signals-and-hardware.md`
- Packet-interval timing / ICMP delay covert channel → `network-advanced.md`

## Related Directions

- Clues are in public sources rather than local artifacts → `ctf-osint`
- Pivot to active exploitation of an online service → `ctf-web`
- Found a malicious sample and need to analyze its behavior → `ctf-malware`
- Need to reverse firmware/drivers to continue → `ctf-reverse`
- Just encoding/base/game-type puzzles → `ctf-misc`

## Maintenance

- Associated with the `ctf-forensics` skill by same-named directory; after upstream adds or removes files, the `## File Index` table in this file must be updated accordingly.
- **Tip**: `steganography` / `stego-image` / `stego-advanced` / `stego-advanced-2` are divided **by carrier type** (general / image / audio signal / video transform), so you can locate them directly by carrier; whereas `network` and `network-advanced`, `disk-and-memory` / `disk-advanced` / `disk-recovery` are divided **by difficulty and stage**, so escalate one level when stuck.
- After changing the frontmatter of `SKILL.md`, verify the YAML is valid: invalid frontmatter makes dsh **silently ignore the entire skill**.
