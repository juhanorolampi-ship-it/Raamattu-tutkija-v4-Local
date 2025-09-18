# run_full_diagnostics.py (Versio 4.1 - Korjattu parseri)
import os
import logging
import time
import re
from collections import defaultdict

from logic import etsi_merkityksen_mukaan

# --- MÄÄRITYKSET ---
SYOTE_TIEDOSTO = 'syote.txt'
TULOS_LOKI = 'diagnostiikka_raportti_v4.txt'
HAKUTULOSTEN_MAARA_PER_TEEMA = 15 # Nostetaan hieman pyyntösi mukaan

# --- LOKITUSMÄÄRITYKSET ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(TULOS_LOKI, encoding='utf-8', mode='w')
file_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'
))
logger.addHandler(stream_handler)

# --- APUFUNKTIOT ---
def log_header(text):
    line = "=" * 80
    logger.info("\n" + line)
    logger.info(text.center(80))
    logger.info(line + "\n")

def lue_syote_tiedosto(tiedostopolku):
    try:
        with open(tiedostopolku, 'r', encoding='utf-8') as f:
            sisalto = f.read()
    except FileNotFoundError:
        logging.error(f"Syötetiedostoa '{tiedostopolku}' ei löytynyt.")
        return None, None

    sisallysluettelo_match = re.search(
        r"SISÄLLYSLUETTELO JA HAKUSANAT\n-+\n(.*?)\n-+", sisalto, re.DOTALL
    )
    sisallysluettelo = sisallysluettelo_match.group(1).strip() if sisallysluettelo_match else ""
    
    # Etsitään sisältö vasta sisällysluettelon jälkeen, jotta vältetään bugi
    sisallon_alku = sisalto.find(sisallysluettelo) if sisallysluettelo else 0
    varsinainen_sisalto = sisalto[sisallon_alku:]
    
    osiot = {}
    pattern = re.compile(
        r"^(\d[\d\.]*)\s*.*?\n\nTeema:\s*(.*?)(?=\n\n^\d|\Z)", re.DOTALL | re.MULTILINE
    )
    matches = pattern.findall(varsinainen_sisalto)
    
    for match in matches:
        osio_nro = match[0].strip().rstrip('.')
        teema_teksti = match[1].strip().replace('\n', ' ')
        osiot[osio_nro] = teema_teksti

    return sisallysluettelo, osiot

# --- PÄÄOHJELMA ---
def suorita_kasittely():
    total_start_time = time.time()
    log_header("RAAMATTU-TUTKIJA v4.1 - MERKITYSHAKU DIAGNOSTIIKKA (KORJATTU)")

    sisallysluettelo, osiot = lue_syote_tiedosto(SYOTE_TIEDOSTO)
    if not osiot:
        logging.error("Ohjelma päättyy, koska syötettä ei voitu jäsentää.")
        return

    logging.info(f"Löytyi {len(osiot)} osiota käsiteltäväksi tiedostosta '{SYOTE_TIEDOSTO}'.")
    
    jae_kartta = defaultdict(list)
    kaikki_loydetyt_jakeet = set()

    for i, (osio_nro, teema) in enumerate(osiot.items(), 1):
        logging.info(f"--- Käsittelyssä osio {i}/{len(osiot)}: {osio_nro} ---")
        logging.info(f"Hakuaihe (teema): '{teema}'")
        
        tulokset = etsi_merkityksen_mukaan(
            kysely=teema, 
            top_k=HAKUTULOSTEN_MAARA_PER_TEEMA
        )
        
        if tulokset:
            logging.info(f"Löytyi {len(tulokset)} relevanttia jaetta.")
            for tulos in tulokset:
                jae_viite_teksti = f"{tulos['viite']}: \"{tulos['teksti']}\""
                jae_kartta[osio_nro].append(jae_viite_teksti)
                kaikki_loydetyt_jakeet.add(jae_viite_teksti)
        else:
            logging.warning("Ei hakutuloksia tälle teemalle.")
        logging.info("-" * 40)

    total_end_time = time.time()
    log_header("DIAGNOSTIIKAN YHTEENVETO")
    logging.info(f"Kokonaiskesto: {(total_end_time - total_start_time):.2f} sekuntia.")
    logging.info(f"Löydetty yhteensä {len(kaikki_loydetyt_jakeet)} uniikkia jaetta.")
    
    log_header("YKSITYISKOHTAINEN JAEJAOTTELU")
    
    sorted_osiot = sorted(
        jae_kartta.items(),
        key=lambda item: [int(p) for p in item[0].split('.')]
    )

    for osio_nro, jakeet in sorted_osiot:
        otsikko_match = re.search(
            r"^{}\.?\s*(.*)".format(re.escape(osio_nro)),
            sisallysluettelo, re.MULTILINE
        )
        otsikko = otsikko_match.group(1).strip() if otsikko_match else f"Osio {osio_nro}"
        
        logger.info(f"\n### {osio_nro} {otsikko} ({len(jakeet)} jaetta) ###")
        if jakeet:
            for jae in jakeet:
                logger.info(f"- {jae}")
        else:
            logger.info("- Ei löytynyt jakeita tähän osioon.")

    logging.info(f"\nDiagnostiikkaraportti on tallennettu tiedostoon: '{TULOS_LOKI}'")

if __name__ == "__main__":
    suorita_kasittely()