import sqlite3
from datetime import datetime
import logging
import nfc_reader

DB_PATH = "../data/flaschen_database.db"
BLOCK_NUMBER = 4
MAGIC = b"BOTL"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("station2")

def log(msg: str):
    with open("station2.log", "a") as f:
        f.write(f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] {msg}\n")

def unpack_flaschen_id(block: bytes):
    if not block or len(block) != 16:
        return None
    if block[:4] != MAGIC:
        return None
    fid = int.from_bytes(block[4:8], "little")
    return fid if fid > 0 else None

def get_rezept_id(cur, flaschen_id: int):
    cur.execute("SELECT Rezept_ID FROM Flasche WHERE Flaschen_ID = ?", (flaschen_id,))
    row = cur.fetchone()
    return None if row is None else row[0]

def get_granulat_mengen(cur, rezept_id: int):
    cur.execute("""
        SELECT Granulat_ID, Menge
        FROM Rezept_besteht_aus_Granulat
        WHERE Rezept_ID = ?
        ORDER BY Granulat_ID
    """, (rezept_id,))
    return cur.fetchall()  # Liste von (Granulat_ID, Menge)

def main():
    log("Station 2 gestartet")

    reader = nfc_reader.NFCReader()
    logger.info("Waiting for RFID/NFC bottle...")

    uid = None
    while uid is None:
        uid = reader.read_passive_target(timeout=0.5)
        print(".", end="", flush=True)

    uid = bytes(uid)
    logger.info("Found card UID: %s", uid.hex(":"))

    block = reader.read_block(uid, BLOCK_NUMBER)
    flaschen_id = unpack_flaschen_id(block)
    if flaschen_id is None:
        log("FEHLER: Keine gültige Flaschen-ID auf dem Tag (nicht getaggt?)")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        rezept_id = get_rezept_id(cur, flaschen_id)
        if rezept_id is None:
            log(f"FEHLER: Flaschen_ID={flaschen_id} nicht in DB oder Rezept_ID ist NULL")
            return

        mengen = get_granulat_mengen(cur, int(rezept_id))
        if not mengen:
            log(f"FEHLER: Keine Granulat-Mengen für Rezept_ID={rezept_id} gefunden")
            return

        # Log-Ausgabe für diese Flasche
        parts = " | ".join([f"Granulat {gid}: {menge}" for gid, menge in mengen])
        log(f"Flaschen_ID={flaschen_id} Rezept_ID={rezept_id} -> {parts}")

        # Optional auch auf Konsole
        print(f"\nFlaschen_ID={flaschen_id}, Rezept_ID={rezept_id}")
        for gid, menge in mengen:
            print(f"  Granulat {gid}: {menge}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
