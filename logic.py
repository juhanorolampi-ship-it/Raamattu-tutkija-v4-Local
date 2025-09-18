# logic.py (Versio 7.2 - Korjattu jaetekstin nouto)
import json
import logging
import faiss
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

# --- Vakioasetukset ---
VEKTORI_INDEKSI_TIEDOSTO = "raamattu_vektori_indeksi.faiss"
VIITE_KARTTA_TIEDOSTO = "raamattu_viite_kartta.json"
RAAMATTU_TIEDOSTO = "bible.json"
EMBEDDING_MALLI = "paraphrase-multilingual-MiniLM-L12-v2"

# --- Lokituksen alustus ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)


@st.cache_resource
def lataa_resurssit():
    """
    Lataa kaikki tarvittavat resurssit kerran ja pitää ne muistissa
    Streamlitin välimuistin avulla.
    """
    logging.info("Ladataan hakumalli, indeksi ja datatiedostot muistiin...")
    try:
        model = SentenceTransformer(EMBEDDING_MALLI)
        indeksi = faiss.read_index(VEKTORI_INDEKSI_TIEDOSTO)

        with open(VIITE_KARTTA_TIEDOSTO, "r", encoding="utf-8") as f:
            viite_kartta = json.load(f)

        with open(RAAMATTU_TIEDOSTO, "r", encoding="utf-8") as f:
            raamattu_data = json.load(f)

        # KORJAUS: Rakennetaan hakukartta, joka sisältää VAIN puhtaan jaetekstin
        # raportin näyttämistä varten.
        jae_haku_kartta = {}
        for kirja_dict in raamattu_data.get('book', {}).values():
            if not isinstance(kirja_dict, dict):
                continue
            kirjan_nimi = kirja_dict.get('info', {}).get('name')
            if not kirjan_nimi:
                continue

            for luku_nro, luku_dict in kirja_dict.get('chapter', {}).items():
                if not isinstance(luku_dict, dict):
                    continue
                for jae_nro, jae_dict in luku_dict.get('verse', {}).items():
                    if isinstance(jae_dict, dict):
                        teksti = jae_dict.get("text", "").strip()
                        if teksti:
                            viite = f"{kirjan_nimi} {luku_nro}:{jae_nro}"
                            jae_haku_kartta[viite] = teksti

        logging.info("Kaikki resurssit ladattu onnistuneesti.")
        return model, indeksi, viite_kartta, jae_haku_kartta

    except Exception as e:
        logging.error(f"Kriittinen virhe resurssien alustuksessa: {e}")
        return None, None, None, None


def etsi_merkityksen_mukaan(kysely: str, top_k: int = 20) -> list[dict]:
    """
    Etsii Raamatusta merkityksen perusteella käyttäen
    välimuistitettuja resursseja.
    """
    model, indeksi, viite_kartta, jae_haku_kartta = lataa_resurssit()

    if not all([model, indeksi, viite_kartta, jae_haku_kartta]):
        logging.error("Haku epäonnistui, koska resursseja ei voitu ladata.")
        return []

    kysely_vektori = model.encode([kysely])
    kysely_vektori_float32 = np.array(kysely_vektori, dtype=np.float32)
    _, loydetyt_indeksit_raw = indeksi.search(kysely_vektori_float32, top_k)

    tulokset = []
    for indeksi in loydetyt_indeksit_raw[0]:
        if indeksi != -1:
            viite = viite_kartta.get(str(indeksi))
            if viite:
                teksti = jae_haku_kartta.get(
                    viite, "[VIRHE: Tekstiä ei löytynyt]"
                )
                tulokset.append({"viite": viite, "teksti": teksti})
    return tulokset
