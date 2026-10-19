# CTF Forensics - Blockchain / EVM On-Chain Forensics

## Table of Contents
- [EVM Calldata Decoding](#evm-calldata-decoding)
- [EVM Storage Slot Forensics](#evm-storage-slot-forensics)
- [EVM Event Log and Transfer ABI Decoding](#evm-event-log-and-transfer-abi-decoding)
- [Transaction Replay / Call Trace](#transaction-replay--call-trace)
- [Bitcoin / UTXO Peel Chain](#bitcoin--utxo-peel-chain)
- [See Also](#see-also)

---

## EVM Calldata Decoding

**Pattern:** A CTF provides an Ethereum transaction hash, raw calldata, or ABI JSON and asks what the contract call was doing. Calldata starts with the 4-byte function selector (Keccak-256 of `name(type,type)`), followed by 32-byte ABI words.

```python
import requests
import hashlib

def selector(fn_sig: str) -> str:
    return hashlib.sha3_256(fn_sig.encode()).hexdigest()[:8]

def parse_calldata(data: bytes):
    if len(data) < 4:
        return None
    return data[:4].hex(), [data[i:i+32] for i in range(4, len(data), 32)]

# From Etherscan: https://api.etherscan.io/api?module=proxy&action=eth_getTransactionByHash&txhash=...
raw = bytes.fromhex("a9059cbb" + "00"*12 + "11"*22 + "00"*31 + "01")
sig, words = parse_calldata(raw)
print(sig)          # a9059cbb
print("transfer(address,uint256)" == None)  # sanity check only

# Decode common ERC-20 args manually
to = "0x" + words[0][12:].hex().lstrip("0") or "0x0"
value = int.from_bytes(words[1], "big")
print(to, value)
```

**Key insight:** ABI words are right-aligned; addresses occupy the last 20 bytes of the first word. A zero word is `0x0000000000000000000000000000000000000000000000000000000000000000`, and decoding should always be checked against the actual function signature rather than assuming offset/layout.

---

## EVM Storage Slot Forensics

**Pattern:** Contract state can hide flags in storage even when the source is unavailable. `eth_getStorageAt` returns raw 32-byte slots; mappings and arrays use Keccak-based slot formulas.

```bash
# Direct RPC query (public/mainnet/archive node):
curl -X POST https://rpc.example \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_getStorageAt","params":["0xCONTRACT", "0x1", "latest"]}'
```

```python
import requests, json, hashlib

def get_storage(rpc, contract, slot):
    r = requests.post(rpc, json={"jsonrpc":"2.0","id":1,
        "method":"eth_getStorageAt",
        "params":[contract, hex(slot), "latest"]})
    return r.json()["result"]  # '0x' + 64 hex

def slot_for_mapping_keccak(key: bytes, base_slot: int) -> int:
    # keccak256(key padded to 32 bytes || base_slot padded to 32 bytes)
    return int.from_bytes(hashlib.sha3_256(
        key.rjust(32, b"\x00") + base_slot.to_bytes(32, "big")), "big")

# Often flag is stored as ASCII in slot 0:
val = bytes.fromhex(get_storage("https://rpc.example", "0xCONTRACT", 0)[2:])
print(val.rstrip(b"\x00"))
```

**Key insight:** For a simple state variable, the slot number is the source-code declaration order. For mapping keys, compute `keccak256(key || slot)`. Arrays store length at the slot and elements starting at `keccak256(slot)`.

---

## EVM Event Log and Transfer ABI Decoding

**Pattern:** A token flight or contract interaction leaves event logs. `eth_getLogs` returns raw `topics` and `data`; the first topic is the event signature hash.

```python
import requests, hashlib, json

def event_topic(sig: str) -> str:
    return "0x" + hashlib.sha3_256(sig.encode()).hexdigest()

def parse_web3_log(log):
    # log["topics"] are 32-byte words; indexed args are first N topics
    sig, data = log["topics"][0], log["data"][2:]
    words = [data[i:i+64] for i in range(0, len(data), 64)]
    return sig, words

# ERC-20 Transfer(address indexed from,address indexed to,uint256 value)
# topics[1..2] are from/to addresses; data word is the value
log = {"topics": [
    event_topic("Transfer(address,address,uint256)"),
    "0x000000000000000000000000"+("AA"*20),
    "0x000000000000000000000000"+("BB"*20),
], "data": "0x"+"00"*31+"2a"}
sig, words = parse_web3_log(log)
from_addr = "0x" + log["topics"][1][-40:]
to_addr = "0x" + log["topics"][2][-40:]
value = int(words[0], 16)
print(from_addr, to_addr, value)
```

**Key insight:** Topic 0 is always `keccak256("Transfer(address,address,uint256)")` for standard ERC-20/721 transfers. The remaining indexed parameters are the next topics; non-indexed parameters are packed ABI words in `data`. When a challenge asks "who sent what", decoding both topics and data is the fastest route.

---

## Transaction Replay / Call Trace

**Pattern:** The challenge gives a tx hash and no source; reproduce what happened by replaying the call locally or using `debug_traceTransaction`.

```bash
# Geth/Anvil local node:
cast run <txhash> --rpc-url <RPC> --trace
```

```python
import requests

def call_trace(rpc, txhash):
    r = requests.post(rpc, json={"jsonrpc":"2.0","id":1,
        "method":"debug_traceTransaction",
        "params":[txhash, {"tracer":"callTracer"}]})
    return r.json()
```

**Key insight:** `callTracer` returns nested `from`, `to`, `value`, and `input`/`output` fields. For a single on-chain challenge, replaying into an Anvil fork (`anvil --fork-url <RPC> --fork-block-number ...`) lets you examine storage and events without changing the live chain.

---

## Bitcoin / UTXO Peel Chain

**Pattern (tumbler / peel chain):** Bitcoin transactions divide one input into many outputs; one output is a "peel" to the next hop while a round output is the fee or pathology. Follow the **larger non-round output** to trace the chain; break on the first obvious payout or flag address.

```python
# mempool.space API
import requests
txid = "..."  # from challenge
while True:
    tx = requests.get(f"https://mempool.space/api/tx/{txid}").json()
    outputs = [o for o in tx.get("vout", [])]
    if not outputs:
        break
    # Peel chain heuristic: the next hop is usually the largest BTC output,
    # excluding round/fee outputs.
    nxt = max(outputs, key=lambda o: o.get("value", 0))
    print(tx["txid"], nxt["scriptpubkey_address"], nxt["value"])
    txid = nxt.get("txid", "")
    if len(outputs) == 1 or txid in known_breaks:
        break
```

**Key insight:** Round `value` outputs are frequently payout/fee markers; the "peel" is the larger non-round amount. Using the public mempool.space API avoids API keys and is commonly allowed in CTFs. Always verify by the explorer UI at `https://mempool.space/tx/<txid>`.

---

## See Also

- [Ethereum / Blockchain Transaction Tracing (Defenit CTF 2020)](#ethereum--blockchain-transaction-tracing-defenit-ctf-2020) (statistical tumbler tracing, this file's sibling)
- `ctf-misc` for addresses that are just strings, not on-chain behavior
- `ctf-web` / `ctf-crypto` for contract exploit/web3 challenge logic after the data has been extracted