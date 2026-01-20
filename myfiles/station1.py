import sqlite3
from datetime import datetime
import nfc_reader
import logging
import random
sign = b"AHTS"

PATH = "../data/flaschen_database.db"
BLOCK_NUMBER = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("station1")

def pack_flaschen_id(fid: int) -> bytes: # Flaschen ID in 16 bytes für die RFIDs
    return sign + fid.to_bytes(4, "little") + bytes(8)

def unpack_flaschen_id(block: bytes): # liest 16 Byte Block und sucht die Flaschen-ID
    if not block or len(block) != 16:
        return None
    if block[:4] != sign: # sign falsch -> keine chance
        return None
    fid = int.from_bytes(block[4:8], "little") # 4-7 als Zahl
    return fid if fid > 0 else None

def log(msg: str):
    with open("station1.log", "a") as f:
        f.write(f"[{datetime.now().isoformat(sep=' ', timespec='seconds')}] {msg}\n")

def next_free_bottle_id(cur):
    cur.execute("SELECT MAX(Flaschen_ID) FROM Flasche")
    result = cur.fetchone()[0]
    return 1 if result is None else int(result) + 1

def main():
    log("Station 1 gestartet")
    reader = nfc_reader.NFCReader()
    logger.info("Waiting for RFID/NFC card...")
    while True:
        uid = reader.read_passive_target(timeout=0.5)
        print(".", end="")
        if uid is None:
            continue
        logger.info("Found card with UID: %s", [hex(i) for i in uid])
        break

    uid = bytes(uid)
    existing = reader.read_block(uid, BLOCK_NUMBER)
    existing_id = unpack_flaschen_id(existing)
    if existing_id is not None:
        log(f"Bereits getaggt: FlaschenID = {existing_id} (kein neues Tagging)")
        return
    conn = sqlite3.connect(PATH)
    cursor = conn.cursor()
    rezept_id = random.randint(1,3)
    try:
        flaschen_id = next_free_bottle_id(cursor)
        data = pack_flaschen_id(flaschen_id)
        ok = reader.write_block(uid, BLOCK_NUMBER, data)
        log(f"FlaschenID vergeben! ID = {flaschen_id}")

        cursor.execute("""
            INSERT INTO Flasche (Flaschen_ID, Rezept_ID, Tagged_Date, has_error)
            VALUES (?, ?, ?, ?)
        """, (flaschen_id, rezept_id, datetime.now(), False))

        conn.commit()
        log(f"Flaschen-ID {flaschen_id} erfolgreich gespeichert")

    except Exception as e:
        log(f"FEHLER: {e}")

    finally:
        conn.close()
    
if __name__ == "__main__":
    main()