# run_full_diagnostics.py (Versio 5.1 - Yksityiskohtainen ajastus)
import logging
import time
import re
from collections import defaultdict

# Varmistetaan, että logic.py-tiedostosta tuodaan oikea funktio
from logic import etsi_merkityksen_mukaan, lataa_resurssit

# --- MÄÄRITYKSET ---
SYOTE_TIEDOSTO = 'syote.txt'
TULOS_LOKI = 'diagnostiikka_raportti_uusi_testi.txt'
HAKUTULOSTEN_MAARA_PER_TEEMA = 15

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


def log_header(text):
    """Tulostaa siistin otsikon lokitiedostoon."""
    line = "=" * 80
    logger.info("\n%s\n%s\n%s\n", line, text.center(80), line)


def lue_syote_tiedosto(tiedostopolku):
    """Lukee ja jäsentää syötetiedoston vankasti."""
    try:
        with open(tiedostopolku, 'r', encoding='utf-8') as f:
            sisalto = f.read()
    except FileNotFoundError:
        logging.error(f"Syötetiedostoa '{tiedostopolku}' ei löytynyt.")
        return None, None

    sisallysluettelo_match = re.search(
        r"Sisällysluettelo:(.*?)(?=\n\d\.|\Z)", sisalto, re.DOTALL
    )
    sisallysluettelo = sisallysluettelo_match.group(1).strip() if sisallysluettelo_match else ""

    hakulauseet = {}
    osiot = re.split(r'\n(?=\d\.\s)', sisalto)

    for osio_teksti in osiot:
        osio_teksti = osio_teksti.strip()
        if not osio_teksti:
            continue

        rivit = osio_teksti.split('\n', 1)
        otsikko = rivit[0].strip()
        kuvaus = rivit[1].strip() if len(rivit) > 1 else ""

        osio_match = re.match(r"^([\d\.]+)", otsikko)
        if osio_match:
            osio_nro = osio_match.group(1).strip('.')
            haku = f"{otsikko}: {kuvaus.replace('\n', ' ')}"
            hakulauseet[osio_nro] = haku

    return hakulauseet, sisallysluettelo


def suorita_diagnostiikka():
    """Ajaa koko diagnostiikkaprosessin yksityiskohtaisella ajastuksella."""
    total_start_time = time.time()
    log_header("RAAMATTU-TUTKIJA v4 - DIAGNOSTIIKKA (Yksityiskohtainen ajastus)")

    # Ladataan resurssit kerran alussa, jotta sen kesto ei sotke hakuaikoja
    logging.info("Esiladataan kaikki resurssit...")
    resurssien_lataus_alku = time.time()
    lataa_resurssit()
    resurssien_lataus_loppu = time.time()
    logging.info(
        "Resurssit ladattu. Kesto: "
        f"{(resurssien_lataus_loppu - resurssien_lataus_alku):.2f} sekuntia."
    )

    hakulauseet, sisallysluettelo = lue_syote_tiedosto(SYOTE_TIEDOSTO)
    if not hakulauseet:
        logging.error("Lopetetaan suoritus, koska syötettä ei voitu jäsentää.")
        return

    logging.info(f"Löytyi {len(hakulauseet)} osiota käsiteltäväksi tiedostosta '{SYOTE_TIEDOSTO}'.")

    jae_kartta = defaultdict(list)
    kaikki_loydetyt_jakeet = set()
    total_search_time = 0

    sorted_osiot = sorted(
        hakulauseet.items(),
        key=lambda item: [int(p) for p in item[0].split('.')]
    )

    for i, (osio_nro, haku) in enumerate(sorted_osiot):
        logging.info(f"--- Käsittelyssä osio {i+1}/{len(sorted_osiot)}: {osio_nro} ---")
        
        # Ajastetaan koko hakuprosessi
        haku_alku = time.time()
        tulokset = etsi_merkityksen_mukaan(
            haku, top_k=HAKUTULOSTEN_MAARA_PER_TEEMA
        )
        haku_loppu = time.time()
        
        kesto = haku_loppu - haku_alku
        total_search_time += kesto

        logging.info(f"Haku valmis. Kokonaiskesto: {kesto:.4f} sekuntia. Löydettiin {len(tulokset)} jaetta.")

        if tulokset:
            for tulos in tulokset:
                jae_viite_teksti = f"- {tulos['viite']}: \"{tulos['teksti']}\""
                jae_kartta[osio_nro].append(jae_viite_teksti)
                kaikki_loydetyt_jakeet.add(jae_viite_teksti)
        logging.info("-" * 40)

    total_end_time = time.time()
    log_header("DIAGNOSTIIKAN YHTEENVETO")
    logging.info(f"Koko diagnostiikan ajo kesti: {(total_end_time - total_start_time):.2f} sekuntia.")
    logging.info(f"Hakujen kokonaisaika (ilman resurssien latausta): {total_search_time:.2f} sekuntia.")
    logging.info(f"Löydetty yhteensä {len(kaikki_loydetyt_jakeet)} uniikkia jaetta.")

    log_header("YKSITYISKOHTAINEN JAEJAOTTELU")

    for osio_nro, _ in sorted_osiot:
        # ... (tämä osa pysyy samana, joten jätän sen pois selkeyden vuoksi)
        otsikko = ""
        if sisallysluettelo:
             otsikko_match = re.search(
                r"^{}\\.?\\s*(.*)".format(re.escape(osio_nro)),
                sisallysluettelo,
                re.MULTILINE
            )
             if otsikko_match:
                otsikko = otsikko_match.group(1).strip()

        if not otsikko:
            haku = hakulauseet.get(osio_nro, "")
            otsikko = haku.split(':', 1)[0]

        logger.info(f"\n--- {osio_nro} {otsikko} ---\n")

        if osio_nro in jae_kartta:
            for jae in jae_kartta[osio_nro]:
                logger.info(jae)
        else:
            logger.info("Ei jakeita tähän osioon.")

    logging.info("\nDiagnostiikka valmis.")


if __name__ == '__main__':
    suorita_diagnostiikka()