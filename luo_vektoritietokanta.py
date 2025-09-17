# luo_vektoritietokanta.py (v1.3 - Korjattu JSON-rakenne)
import json
import logging
import time
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- MÄÄRITYKSET ---
RAAMATTU_TIEDOSTO = "bible.json"
VEKTORI_INDEKSI_TIEDOSTO = "raamattu_vektori_indeksi.faiss"
VIITE_KARTTA_TIEDOSTO = "raamattu_viite_kartta.json"
EMBEDDING_MALLI = "paraphrase-multilingual-MiniLM-L12-v2"

# --- LOKITUS ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)

def luo_vektoritietokanta():
    """
    Lukee Raamatun JSON-tiedostosta, luo jokaisesta jakeesta semanttisen
    vektoriupotuksen (embedding) ja tallentaa ne FAISS-indeksiin sekä
    luo erillisen tiedoston viitteiden hallintaan.
    """
    logging.info("Aloitetaan vektoritietokannan luonti...")

    # 1. Lataa Raamatun data
    try:
        with open(RAAMATTU_TIEDOSTO, "r", encoding="utf-8") as f:
            raamattu_data = json.load(f)
        logging.info(f"'{RAAMATTU_TIEDOSTO}' ladattu onnistuneesti.")
    except Exception as e:
        logging.error(f"KRIITTINEN VIRHE ladattaessa '{RAAMATTU_TIEDOSTO}': {e}")
        return

    # 2. Alusta embedding-malli
    logging.info(f"Ladataan embedding-malli: '{EMBEDDING_MALLI}'...")
    try:
        model = SentenceTransformer(EMBEDDING_MALLI)
        logging.info("Malli ladattu onnistuneesti.")
    except Exception as e:
        logging.error(f"Mallin lataus epäonnistui: {e}")
        return

    # 3. Kerää jakeet ja viitteet
    logging.info("Kerätään jakeita ja viitteitä Raamatusta...")
    jakeiden_tekstit = []
    jakeiden_viitteet = []

    # --- KORJATTU LOGIIKKA TÄSSÄ ---
    # Käydään läpi kirja-sanakirjan arvoja (values), ei avaimia (keys).
    for kirja_obj in raamattu_data.get('book', {}).values():
        if not isinstance(kirja_obj, dict):
            continue

        kirjan_nimi = kirja_obj.get('info', {}).get('name')
        if not kirjan_nimi:
            continue
        
        # Lukujen data on sanakirja, jonka avaimet ovat lukujen numeroita merkkijonoina.
        for luku_nro_str, luku_data in kirja_obj.get('chapter', {}).items():
            if not isinstance(luku_data, dict):
                continue
            
            # Jakeiden data on 'verse'-avaimen alla toisessa sanakirjassa.
            for jae_nro_str, jae_data in luku_data.get('verse', {}).items():
                if isinstance(jae_data, dict):
                    viite = f"{kirjan_nimi} {luku_nro_str}:{jae_nro_str}"
                    teksti = jae_data.get("text", "")
                    if teksti:
                        jakeiden_tekstit.append(teksti)
                        jakeiden_viitteet.append(viite)

    if not jakeiden_tekstit:
        logging.error("Raamatusta ei löytynyt yhtään jaetta. Prosessi keskeytetään.")
        return
        
    logging.info(f"Kerätty yhteensä {len(jakeiden_tekstit)} jaetta.")

    # 4. Luo vektorit (embeddings)
    logging.info("Muunnetaan jakeita vektoreiksi. Tämä voi kestää hetken...")
    start_time = time.time()
    vektorit = model.encode(jakeiden_tekstit, show_progress_bar=True)
    end_time = time.time()
    logging.info(f"Vektorien luonti valmis. Kesto: {end_time - start_time:.2f} sekuntia.")

    # 5. Rakenna ja tallenna FAISS-indeksi
    vektorin_ulottuvuus = vektorit.shape[1]
    indeksi = faiss.IndexFlatL2(vektorin_ulottuvuus)
    indeksi.add(np.array(vektorit, dtype=np.float32))

    logging.info(f"FAISS-indeksi luotu, sisältää {indeksi.ntotal} vektoria.")
    
    try:
        faiss.write_index(indeksi, VEKTORI_INDEKSI_TIEDOSTO)
        logging.info(f"Indeksi tallennettu tiedostoon: '{VEKTORI_INDEKSI_TIEDOSTO}'")
    except Exception as e:
        logging.error(f"Indeksin tallennus epäonnistui: {e}")
        return

    # 6. Tallenna viitekartta
    viite_kartta = {i: viite for i, viite in enumerate(jakeiden_viitteet)}
    try:
        # JSON-avaimien on oltava merkkijonoja.
        viite_kartta_str_avaimin = {str(k): v for k, v in viite_kartta.items()}
        with open(VIITE_KARTTA_TIEDOSTO, "w", encoding="utf-8") as f:
            json.dump(viite_kartta_str_avaimin, f, ensure_ascii=False, indent=4)
        logging.info(f"Viitekartta tallennettu tiedostoon: '{VIITE_KARTTA_TIEDOSTO}'")
    except Exception as e:
        logging.error(f"Viitekartan tallennus epäonnistui: {e}")
        return
        
    logging.info("Kaikki valmista! Vektoritietokanta on nyt luotu.")


if __name__ == "__main__":
    luo_vektoritietokanta()