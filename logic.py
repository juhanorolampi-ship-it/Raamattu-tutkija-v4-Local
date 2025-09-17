# logic.py (Versio 4.0 - Vector Search)
import json
import logging
import time
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- MÄÄRITYKSET ---
VEKTORI_INDEKSI_TIEDOSTO = "raamattu_vektori_indeksi.faiss"
VIITE_KARTTA_TIEDOSTO = "raamattu_viite_kartta.json"
RAAMATTU_TIEDOSTO = "bible.json" # Tarvitaan jakeiden tekstin hakemiseen
EMBEDDING_MALLI = "paraphrase-multilingual-MiniLM-L12-v2"

# --- LOKITUS ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)

# --- GLOBAALIT MUUTTUJAT VÄLIMUISTITUSTA VARTEN ---
# Ladataan resurssit vain kerran ohjelman käynnistyessä muistiin.
# Tämä nopeuttaa hakuja merkittävästi, kun mallia ja dataa ei
# ladata levyltä joka kerta uudelleen.
try:
    logging.info("Ladataan hakumalli, indeksi ja datatiedostot muistiin...")
    MODEL = SentenceTransformer(EMBEDDING_MALLI)
    INDEKSI = faiss.read_index(VEKTORI_INDEKSI_TIEDOSTO)
    
    with open(VIITE_KARTTA_TIEDOSTO, "r", encoding="utf-8") as f:
        VIITE_KARTTA = json.load(f)
    
    with open(RAAMATTU_TIEDOSTO, "r", encoding="utf-8") as f:
        RAAMATTU_DATA = json.load(f)
    
    # Rakennetaan nopea hakurakenne jakeiden tekstien noutamiseen viitteellä
    JAE_HAKU_KARTTA = {}
    for kirja_obj in RAAMATTU_DATA.get('book', {}).values():
        if isinstance(kirja_obj, dict):
            kirjan_nimi = kirja_obj.get('info', {}).get('name')
            if kirjan_nimi:
                for luku_nro_str, luku_data in kirja_obj.get('chapter', {}).items():
                    if isinstance(luku_data, dict):
                        for jae_nro_str, jae_data in luku_data.get('verse', {}).items():
                            if isinstance(jae_data, dict) and "text" in jae_data:
                                viite = f"{kirjan_nimi} {luku_nro_str}:{jae_nro_str}"
                                JAE_HAKU_KARTTA[viite] = jae_data["text"]

    logging.info("Kaikki resurssit ladattu onnistuneesti.")

except Exception as e:
    logging.error(f"Kriittinen virhe alustuksessa: {e}")
    logging.error("Varmista, että 'luo_vektoritietokanta.py' on ajettu onnistuneesti.")
    MODEL, INDEKSI, VIITE_KARTTA, JAE_HAKU_KARTTA = None, None, None, None


def etsi_merkityksen_mukaan(kysely: str, top_k: int = 20) -> list[dict]:
    """
    Etsii Raamatusta 'top_k' määrän jakeita, jotka parhaiten vastaavat
    annetun kyselyn merkitystä käyttäen vektorihakua.

    Args:
        kysely: Vapaamuotoinen hakulause, esim. "Jumalan rakkaus ihmiskuntaa kohtaan".
        top_k: Palautettavien jakeiden enimmäismäärä.

    Returns:
        Lista sanakirjoja, joissa kussakin on 'viite' ja 'teksti'.
        Palauttaa tyhjän listan, jos alustus epäonnistui tai haku ei tuota tuloksia.
    """
    if not all([MODEL, INDEKSI, VIITE_KARTTA, JAE_HAKU_KARTTA]):
        logging.error("Haku epäonnistui. Resursseja ei ole alustettu oikein.")
        return []

    logging.info(f"Suoritetaan merkityshaku kyselyllä: '{kysely}', top_k={top_k}")
    start_time = time.time()

    # 1. Muunna käyttäjän kysely vektoriksi
    kysely_vektori = MODEL.encode([kysely])
    kysely_vektori_float32 = np.array(kysely_vektori, dtype=np.float32)

    # 2. Suorita haku FAISS-indeksistä
    # Palauttaa etäisyydet (D) ja indeksit (I) lähimmistä vektoreista
    _, I = INDEKSI.search(kysely_vektori_float32, top_k)

    # 3. Muunna indeksit takaisin Raamatun viitteiksi ja hae tekstit
    tulokset = []
    loydetyt_indeksit = I[0] # Hakutulokset ensimmäiselle (ja ainoalle) kyselylle

    for indeksi in loydetyt_indeksit:
        if indeksi != -1: # FAISS voi palauttaa -1, jos tuloksia on vähemmän kuin top_k
            # Avain on merkkijono JSON-tiedostossa
            viite = VIITE_KARTTA.get(str(indeksi))
            if viite:
                teksti = JAE_HAKU_KARTTA.get(viite, "[Tekstiä ei löytynyt]")
                tulokset.append({"viite": viite, "teksti": teksti})

    end_time = time.time()
    logging.info(f"Haku valmis. Kesto: {end_time - start_time:.4f} sekuntia. Löydettiin {len(tulokset)} jaetta.")
    
    return tulokset

# Voit lisätä tähän testikoodia, jos haluat testata funktion toimintaa suoraan
if __name__ == '__main__':
    logging.info("--- Testataan hakulogiikkaa ---")
    
    testikysely = "Ketkä olivat Jeesuksen opetuslapset?"
    hakutulokset = etsi_merkityksen_mukaan(testikysely, top_k=5)
    
    if hakutulokset:
        print(f"\nTestikyselyn '{testikysely}' top 5 tulosta:")
        for tulos in hakutulokset:
            print(f"- {tulos['viite']}: \"{tulos['teksti']}\"")
    else:
        print("Testihaku ei tuottanut tuloksia tai alustus epäonnistui.")