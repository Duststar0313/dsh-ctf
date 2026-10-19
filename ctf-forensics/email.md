# CTF Forensics - Email and Mailbox Forensics

## Table of Contents
- [EML / Email Message .eml Parsing](#eml--email-message-eml-parsing)
- [MBOX / Maildir](#mbox--maildir)
- [RFC 2047 Encoded Subject / Headers](#rfc-2047-encoded-subject--headers)
- [Attachment and Embedded Object Extraction](#attachment-and-embedded-object-extraction)
- [Outlook PST/OST](#outlook-pstost)
- [See Also](#see-also)

---

## EML / Email Message .eml Parsing

**Pattern:** A challenge provides a `.eml` file (or an email export) and expects you to extract headers, body, attachments, or a hidden payload. Python's standard library is enough for `Content-Type`, MIME body, and attachments.

```python
import email, email.policy

with open("evidence.eml", "rb") as f:
    msg = email.message_from_bytes(f.read(), policy=email.policy.default)

# Headers
print(msg["From"], msg["To"], msg["Date"], msg["Message-ID"])
# RFC 2047 subject: sometimes encoded with =?utf-8?b?...?=
print(msg["Subject"])

# Top-level MIME
print(msg.get_content_type(), msg.get_content_disposition())

for part in msg.walk():
    print(part.get_content_type(), part.get_content_disposition(),
          part.get_filename(), part.get("Content-ID"))
```

**Key insight:** Reading with `policy=email.policy.default` keeps encoded words as Unicode strings, so you don't need to manually call `decode_header` unless you want the raw encoded form. `msg.walk()` is the standard way to enumerate every MIME part; attachments are usually where a flag or malicious file hides.

---

## MBOX / Maildir

**Pattern:** A mailbox file contains multiple messages. `MBOX` is one file with `From ` separator lines; Maildir is a directory tree (`cur/`, `new/`, `tmp/`).

```python
import mailbox, email

mbox = mailbox.mbox("mail.mbox")   # or mailbox.Maildir("maildir_root")
for i, msg in enumerate(mbox):
    print(i, msg["From"], msg["Subject"])
    # msg is an email.message.Message
```

```bash
# Quick view with standard utilities:
cat mail.mbox | awk '/^From /{n++} {print > ("msg_" n ".eml")}'
# Maildir placement convention:
ls new/ cur/
```

**Key insight:** The first `From ` line starts each message; `mailbox` handles quoted separators, but if the file is corrupted you can still split on `\nFrom ` and parse each chunk with `email.message_from_bytes`. For CTF-sized boxes this manual split is often faster than fighting a damaged mbox index.

---

## RFC 2047 Encoded Subject / Headers

**Pattern:** Subjects like `=?UTF-8?B?SGVsbG8=?=` hide the actual text. Decode them even when the email tool renders them already.

```python
from email.header import decode_header

def decode(value: str) -> str:
    parts = decode_header(value)
    return "".join(
        p.decode(c or "ascii") if isinstance(p, bytes) else p
        for p, c in parts
    )

print(decode("=?UTF-8?B?SGVsbG8sIFdvcmxkIQ==?="))
```

**Key insight:** RFC 2047 can encode base64 (`?B?`) or quoted-printable (`?Q?`) and sometimes mixes chunks. Always process the decoded value for flag fragments; a naive `print(msg["Subject"])` in a non-python client may hide the actual characters.

---

## Attachment and Embedded Object Extraction

**Pattern:** Attachments can be extracted from the MIME tree; base64 or quoted-printable transfer encodings are decoded automatically by `get_payload(decode=True)`. Check filenames, `Content-ID`, inline images, and unusual parts.

```python
import email
from pathlib import Path

msg = email.message_from_bytes(Path("evidence.eml").read_bytes())

for part in msg.walk():
    fn = part.get_filename()
    if not fn:
        continue
    data = part.get_payload(decode=True)
    if data is None:
        continue
    print(fn, len(data))
    Path(fn).write_bytes(data)
```

**Key insight:** `get_payload(decode=True)` handles `Content-Transfer-Encoding: base64/quoted-printable`. `Content-ID` (`<...>`) is the primary handle for inline images; some CTFs hide a second attachment behind an unusual MIME part that a simple content-type filter would skip.

---

## Outlook PST/OST

**Pattern:** The challenge gives an Outlook `.pst` or `.ost` export. The standard tool is `readpst` (libpst) or `pffexport` (libpff); both are often packaged as `libpst-tools` / `libpff-utils`.

```bash
# Extract everything from a PST into folders/mbox
readpst -r -d outdir mail.pst          # -r = recursively, -d = output dir
readpst -M -d outdir mail.pst          # Export as MBOX instead
pffexport -d outdir mail.pst           # Alternative: libpff

# Inspect with strings first if the PST is corrupted
strings -n 8 mail.pst | grep -i flag
```

**Key insight:** PST/OST are indexed storage, not plain mbox. `readpst` gives the cleanest path to messages + attachments for a fresh Linux environment; if it can't parse a damaged PST, `pffexport` often still reads enough metadata (folder tree, dates, subjects) to locate a flag.

---

## See Also

- [Email Headers](#email-headers) in `network.md` (header-only forensics on PCAP or webmail)
- `ctf-misc` for flags hidden in header fields that are pure encoding puzzles
- `ctf-malware` when the email contains a malicious attachment/script