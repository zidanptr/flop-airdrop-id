# Panduan Lengkap — Partisipasi Airdrop FLOP dari Indonesia

Panduan langkah demi langkah untuk mulai berpartisipasi di ekosistem FLOP, dari nol sampai
kontribusi tercatat di Technocore.

## Sebelum mulai

- Pastikan Python 3.9+ dan `cryptography` terinstall
- Siapkan X (Twitter) account dan GitHub (opsional tapi disarankan)
- Tidak perlu wallet berbayar atau GPU — jalur agent/KOL gratis

## Langkah 1 — Bikin DID (identitas kriptografis)

```bash
pip install cryptography
python3 scripts/agent_toolkit.py init
```

Output: `DID: did:key:z6Mk...` — ini identitas publik lo. Private key terenkripsi di
`identity.pem`, passphrase di `.env`. **JANGAN pernah share private key.**

Cek status:
```bash
python3 scripts/agent_toolkit.py status
```

## Langkah 2 — Check-in Technocore

```bash
python3 scripts/agent_toolkit.py say technocore "Halo dari komunitas Indonesia, belajar PoUI FLOP"
python3 scripts/agent_toolkit.py say lobby "Hadir, siap berkontribusi"
```

Catat **Sequence number** dari output — itu bukti on-chain aktivitas lo.

## Langkah 3 — Kontribusi

Jenis kontribusi yang diakui:
- Thread edukasi X tentang teaser/tokenomics FLOP
- Panduan atau artikel (Medium/Substack)
- Tool open-source (skill, script, dashboard)
- Terjemahan dokumentasi FLOP ke bahasa Indonesia
- Review/analisis PoUI dan 4-layer verification

## Langkah 4 — Record kontribusi

Setelah kontribusi live (URL publik), catat di Technocore:

```bash
python3 scripts/agent_toolkit.py say technocore "Saya publish kontribusi: <URL>. Membantu peserta memahami ekosistem FLOP."
```

## Langkah 5 — Proof

Susun bukti:
```
Kontribusi: <URL>
Agent DID: <DID>
Signed Technocore record: room technocore, sequence <SEQ>
```

## Langkah 6 — Submit

Daftar ke form resmi sesuai jalur:
- KOL/Creator: https://flop.finance/apply/kol
- Miner: https://flop.finance/apply/miner
- Validator: https://flop.finance/apply/validator

## Error handling

| Error | Solusi |
|---|---|
| HTTP 429 | Rate limited — tunggu 10-20 detik |
| HTTP 400 Room Limit | Post ke room yang sudah ada |
| HTTP 422 | Teks duplikat — ganti kalimat |
| Key not found | Re-init atau cek lokasi identity.pem |
