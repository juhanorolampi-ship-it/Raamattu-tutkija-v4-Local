# luo_vektoritietokanta.py (Versio 2.2 - Finaali)
import json
import logging
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- MÄÄRITYKSET ---
RAAMATTU_TIEDOSTO = "bible.json"
VEKTORI_INDEKSI_TIEDOSTO = "raamattu_vektori_indeksi.faiss"
VIITE_KARTTA_TIEDOSTO = "raamattu_viite_kartta.json"
EMBEDDING_MALLI = "paraphrase-multilingual-MiniLM-L12-v2"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)

def luo_vektoritietokanta():
    """
    Lukee Raamatun, yhdistää jakeiden otsikot ja tekstit, luo niistä
    vektoriupotukset ja tallentaa ne FAISS-indeksiin.
    """
    logging.info("Aloitetaan vektoritietokannan (v2.2) luonti...")
    
    try:
        with open(RAAMATTU_TIEDOSTO, "r", encoding="utf-8") as f:
            raamattu_data = json.load(f)
    except Exception as e:
        logging.error(f"KRIITTINEN VIRHE: '{RAAMATTU_TIEDOSTO}' lataus epäonnistui: {e}")
        return

    logging.info(f"Ladataan embedding-malli: '{EMBEDDING_MALLI}'...")
    try:
        model = SentenceTransformer(EMBEDDING_MALLI)
    except Exception as e:
        logging.error(f"Mallin lataus epäonnistui: {e}")
        return

    logging.info("Yhdistetään jakeiden otsikoita ja tekstejä...")
    jakeiden_kokotekstit = []
    jakeiden_viitteet = []

    # Oikea tapa käydä bible.json läpi (kirjat ovat sanakirja)
    for kirja_dict in raamattu_data.get('book', {}).values():
        if not isinstance(kirja_dict, dict):
            continue
        kirjan_nimi = kirja_dict.get('info', {}).get('name')
        if not kirjan_nimi:
            continue
        
        for luku_nro, luku_dict in kirja_dict.get('chapter', {}).items():
            if not isinstance(luku_dict, dict):
                continue
            for jae_nro_str, jae_dict in luku_dict.get('verse', {}).items():
                if isinstance(jae_dict, dict):
                    otsikko = jae_dict.get("title", "")
                    teksti = jae_dict.get("text", "")
                    
                    # TÄRKEÄ PARANNUS: Piste lisätään vain, jos otsikko on olemassa (sinun ideasi!)
                    if otsikko:
                        koko_teksti = f"{otsikko}. {teksti}".strip()
                    else:
                        koko_teksti = teksti.strip()
                    
                    if koko_teksti:
                        viite = f"{kirjan_nimi} {luku_nro}:{jae_nro_str}"
                        jakeiden_kokotekstit.append(koko_teksti)
                        jakeiden_viitteet.append(viite)

    logging.info(f"Kerätty {len(jakeiden_kokotekstit)} jaetta. Muunnetaan vektoreiksi...")
    
    vektorit = model.encode(jakeiden_kokotekstit, show_progress_bar=True)
    
    vektorin_ulottuvuus = vektorit.shape[1]
    indeksi = faiss.IndexFlatL2(vektorin_ulottuvuus)
    indeksi.add(np.array(vektorit, dtype=np.float32))

    faiss.write_index(indeksi, VEKTORI_INDEKSI_TIEDOSTO)
    logging.info(f"Uusi indeksi tallennettu: '{VEKTORI_INDEKSI_TIEDOSTO}'")

    viite_kartta = {str(i): viite for i, viite in enumerate(jakeiden_viitteet)}
    with open(VIITE_KARTTA_TIEDOSTO, "w", encoding="utf-8") as f:
        json.dump(viite_kartta, f, ensure_ascii=False, indent=4)
    logging.info(f"Uusi viitekartta tallennettu: '{VIITE_KARTTA_TIEDOSTO}'")
    logging.info("Vektoritietokanta päivitetty onnistuneesti versioon 2.2!")

if __name__ == "__main__":
    luo_vektoritietokanta()