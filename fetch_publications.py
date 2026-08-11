"""
Google Scholar Yayın Çekici
===========================
Bu script, scholarly kütüphanesi kullanarak Google Scholar profilinden
yayın verilerini çeker ve assets/data/publications.json dosyasına yazar.

Kurulum:
    pip install scholarly

Kullanım:
    python fetch_publications.py

Notlar:
    - Google CAPTCHA'dan kaçınmak için VPN veya proxy kullanmayın.
    - Script çok sık çalıştırılırsa Google erişimi engelleyebilir.
    - Her 6-12 ayda bir çalıştırmak yeterlidir.
"""

import json
import re
import time
import sys
from datetime import date
from pathlib import Path

SCHOLAR_ID = "EWXdpogAAAAJ"
OUTPUT_PATH = Path("assets/data/publications.json")


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def load_curated_fields() -> dict:
    """Elle eklenen abstract/quartile gibi alanları başlığa göre indeksler,
    böylece bu script tekrar çalıştığında üzerine yazılmazlar."""
    if not OUTPUT_PATH.exists():
        return {}
    try:
        old_data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    curated = {}
    for pub in old_data.get("publications", []):
        key = normalize_title(pub.get("title", ""))
        if not key:
            continue
        fields = {k: v for k, v in pub.items() if k in ("abstract", "quartile")}
        if fields:
            curated[key] = fields
    return curated


CONFERENCE_KEYWORDS = [
    "proceedings", "conference", "congress", "symposium", "sempozyum",
    "kurultay", "workshop", "intercontinental geoinformation", "isprs archives",
    "geoext", "uzal-cbs", "harita bilimsel", "konferans",
]

def detect_type(bib: dict) -> str:
    """Yayın türünü bibliyografik veriden tespit eder."""
    if bib.get("journal"):
        return "journal"
    venue = " ".join([
        bib.get("booktitle", ""),
        bib.get("conference", ""),
        bib.get("venue", ""),
    ]).lower()
    if any(kw in venue for kw in CONFERENCE_KEYWORDS):
        return "conference"
    if bib.get("booktitle"):
        return "book"
    return "journal"


def extract_doi(pub: dict) -> str:
    """Mevcut alanlardan DOI'yi çıkarmaya çalışır."""
    eprint = pub.get("bib", {}).get("eprint", "")
    if eprint.startswith("10."):
        return eprint
    url = pub.get("pub_url", "")
    if "doi.org/" in url:
        return url.split("doi.org/")[-1].split("&")[0].strip()
    return ""


def fetch_publications():
    try:
        from scholarly import scholarly as sc
    except ImportError:
        print("Hata: scholarly kütüphanesi bulunamadı.")
        print("Kurulum için: pip install scholarly")
        sys.exit(1)

    print(f"Google Scholar'dan veri çekiliyor (ID: {SCHOLAR_ID})...")
    print("Bu işlem birkaç dakika sürebilir. Lütfen bekleyin.\n")

    # Yazar profilini çek
    try:
        author = sc.search_author_id(SCHOLAR_ID)
        sc.fill(author, sections=["basics", "indices", "counts", "publications"])
    except Exception as e:
        print(f"Yazar profili çekilemedi: {e}")
        print("Google CAPTCHA engeli olabilir. Bir süre bekleyip tekrar deneyin.")
        sys.exit(1)

    name         = author.get("name", "")
    h_index      = author.get("hindex", 0)
    i10_index    = author.get("i10index", 0)
    citations    = author.get("citedby", 0)
    total_pubs   = len(author.get("publications", []))

    print(f"Profil bulundu: {name}")
    print(f"  Toplam yayın : {total_pubs}")
    print(f"  Atıf         : {citations}")
    print(f"  h-indeks     : {h_index}")
    print(f"  i10-indeks   : {i10_index}\n")

    curated = load_curated_fields()
    publications = []
    failed = 0

    for i, pub in enumerate(author["publications"], 1):
        title_preview = pub.get("bib", {}).get("title", "")[:60]
        print(f"  [{i}/{total_pubs}] {title_preview}...")

        try:
            sc.fill(pub)
        except Exception as e:
            print(f"    ! Detay çekilemedi: {e}")
            failed += 1

        bib = pub.get("bib", {})
        venue = (
            bib.get("journal")
            or bib.get("conference")
            or bib.get("booktitle")
            or ""
        )

        entry = {
            "title":     bib.get("title", ""),
            "authors":   bib.get("author", ""),
            "venue":     venue,
            "year":      str(bib.get("pub_year", "")),
            "citations": pub.get("num_citations", 0),
            "url":       pub.get("pub_url", ""),
            "doi":       extract_doi(pub),
            "type":      detect_type(bib),
        }
        entry.update(curated.get(normalize_title(entry["title"]), {}))
        publications.append(entry)

        # Google'ı yavaşlatmamak için kısa bekleme
        time.sleep(1.5)

    # Yıla göre azalan sırala
    publications.sort(key=lambda p: p["year"], reverse=True)

    output = {
        "meta": {
            "fetched_at":     str(date.today()),
            "scholar_id":     SCHOLAR_ID,
            "name":           name,
            "h_index":        h_index,
            "i10_index":      i10_index,
            "citations_total": citations,
        },
        "publications": publications,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nTamamlandı!")
    print(f"  {len(publications)} yayın kaydedildi ({failed} adet detay çekilemedi).")
    print(f"  Çıktı: {OUTPUT_PATH}")
    if failed:
        print(f"\n  Not: {failed} yayının detayı çekilemedi.")
        print("  Bu yayınlar temel bilgilerle kaydedildi.")


if __name__ == "__main__":
    fetch_publications()
