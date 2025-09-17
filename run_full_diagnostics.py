# run_full_diagnostics.py (Versio 4.0 - Vector Search)
import logging
import time
import re
from collections import defaultdict

# Tuodaan vain uusi, tarvittava funktio
from logic import etsi_merkityksen_mukaan

# --- MÄÄRITYKSET ---
SYOTE_TIEDOSTO = 'syote.txt'
TULOS_LOKI = 'diagnostiikka_raportti_v4.txt'
# Määritä, kuinka monta osuvinta jaetta haetaan per teema
HAKUTULOSTEN_MAARA_PER_TEEMA = 10 

# --- LOKITUSMÄÄRITYKSET ---
# Määritetään lokitus niin, että se sekä tulostaa konsoliin että kirjoittaa tiedostoon
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Poistetaan mahdolliset aiemmat käsittelijät tuplalokituksen estämiseksi
if logger.hasHandlers():
    logger.handlers.clear()

# Tiedostokäsittelijä (kirjoittaa raporttiin)
try:
    file_handler = logging.FileHandler(TULOS_LOKI, encoding='utf-8', mode='w')
    file_handler.setFormatter(logging.Formatter('%(message)s')) # Pelkkä viesti riittää tiedostoon
    logger.addHandler(file_handler)
except Exception as e:
    print(f"KRIITTINEN VIRHE: Lokitiedoston luonti epäonnistui: {e}")

# Konsolikäsittelijä (tulostaa näytölle)
stream_handler = logging.StreamHandler()
# Konsoliin voidaan tulostaa myös aikaleimat ja taso
stream_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'
))
logger.addHandler(stream_handler)

# --- APUFUNKTIOT ---
def log_header(text):
    """Tulostaa näyttävän otsikon lokiin."""
    line = "=" * 80
    logger.info("\n" + line)
    logger.info(text.center(80))
    logger.info(line + "\n")

def lue_syote_tiedosto(tiedostopolku):
    """
    Lukee syötetiedoston ja jäsentää sen sisällysluetteloksi sekä
    osioiksi, jotka sisältävät teemoja.
    """
    try:
        with open(tiedostopolku, 'r', encoding='utf-8') as f:
            sisalto = f.read()
    except FileNotFoundError:
        logging.error(f"Syötetiedostoa '{tiedostopolku}' ei löytynyt.")
        return None, None

    # Erotetaan sisällysluettelo ja osiot
    sisallysluettelo_match = re.search(
        r"SISÄLLYSLUETTELO JA HAKUSANAT\n-+\n(.*?)\n-+", sisalto, re.DOTALL
    )
    sisallysluettelo = sisallysluettelo_match.group(1).strip() if sisallysluettelo_match else ""

    # Jäsennä osiot ja niiden teemat
    osiot = {}
    # Regex, joka etsii osionumeron (esim. "2.1") ja sitä seuraavan "Teema:"-rivin
    pattern = re.compile(
        r"(\d+(?:\.\d+)*)\s*.*?Teema:\s*(.*?)(?=\n\n|\n\d+\.|\Z)", re.DOTALL
    )
    matches = pattern.findall(sisalto)
    
    for match in matches:
        osio_nro = match[0].strip()
        teema_teksti = match[1].strip().replace('\n', ' ')
        osiot[osio_nro] = teema_teksti

    return sisallysluettelo, osiot

# --- PÄÄOHJELMA ---
def suorita_kasittely():
    """Käsittelee syötetiedoston ja suorittaa merkityshaut."""
    total_start_time = time.time()
    log_header("RAAMATTU-TUTKIJA v4.0 - MERKITYSHAKU DIAGNOSTIIKKA")

    sisallysluettelo, osiot = lue_syote_tiedosto(SYOTE_TIEDOSTO)
    if not osiot:
        logging.error("Ohjelma päättyy, koska syötettä ei voitu jäsentää.")
        return

    logging.info(f"Löytyi {len(osiot)} osiota käsiteltäväksi tiedostosta '{SYOTE_TIEDOSTO}'.")
    
    # Sanakirja tulosten tallentamiseen
    jae_kartta = defaultdict(list)
    kaikki_loydetyt_jakeet = set()

    # Käydään läpi jokainen osio ja sen teema
    for i, (osio_nro, teema) in enumerate(osiot.items(), 1):
        logging.info(f"--- Käsittelyssä osio {i}/{len(osiot)}: {osio_nro} ---")
        logging.info(f"Hakuaihe (teema): '{teema}'")
        
        # TÄMÄ ON UUSI YDIN: Yksi kutsu korvaa koko vanhan prosessin!
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

    # --- TULOSTEN YHTEENVETO ---
    total_end_time = time.time()
    log_header("DIAGNOSTIIKAN YHTEENVETO")
    logging.info(f"Kokonaiskesto: {(total_end_time - total_start_time):.2f} sekuntia.")
    logging.info(f"Löydetty yhteensä {len(kaikki_loydetyt_jakeet)} uniikkia jaetta.")
    
    log_header("YKSITYISKOHTAINEN JAEJAOTTELU")
    
    # Järjestetään osiot numerojärjestykseen tulostusta varten
    sorted_osiot = sorted(
        jae_kartta.items(),
        key=lambda item: [int(p) for p in item[0].split('.')]
    )

    for osio_nro, jakeet in sorted_osiot:
        otsikko_match = re.search(
            r"^{}\\.?\s*(.*)".format(re.escape(osio_nro)),
            sisallysluettelo, re.MULTILINE
        )
        otsikko = otsikko_match.group(1).strip() if otsikko_match else "Nimetön osio"
        
        logger.info(f"\n### {osio_nro} {otsikko} ({len(jakeet)} jaetta) ###")
        if jakeet:
            for jae in jakeet:
                logger.info(f"- {jae}")
        else:
            logger.info("- Ei löytynyt jakeita tähän osioon.")

    logging.info(f"\nDiagnostiikkaraportti on tallennettu tiedostoon: '{TULOS_LOKI}'")

if __name__ == "__main__":
    suorita_kasittely()