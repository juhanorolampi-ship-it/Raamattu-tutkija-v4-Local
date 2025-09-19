# logic.py (Versio 10.5 - Lopulliset PEP-8-korjaukset)
import json
import logging
import re
import faiss
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer, CrossEncoder

# --- Vakioasetukset ---
VEKTORI_INDEKSI_TIEDOSTO = "raamattu_vektori_indeksi.faiss"
VIITE_KARTTA_TIEDOSTO = "raamattu_viite_kartta.json"
RAAMATTU_TIEDOSTO = "bible.json"
EMBEDDING_MALLI = "TurkuNLP/sbert-cased-finnish-paraphrase"
CROSS_ENCODER_MALLI = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# --- Strategiakerroksen sanakirja ---
STRATEGIA_SANAKIRJA = {
    "jännite": (
        "Hae Raamatusta kohtia, jotka kuvaavat rakentavaa erimielisyyttä, "
        "toisiaan täydentäviä rooleja tai sitä, miten erilaisuus johtaa "
        "hengelliseen kasvuun ja terveen jännitteen kautta parempaan lopputulokseen."
    ),
    "tasapaino": (
        "Etsi kohtia, jotka käsittelevät tasapainoa, harmoniaa tai oikeaa "
        "suhdetta kahden eri asian, kuten työn ja levon, tai totuuden "
        "ja rakkauden, välillä."
    ),
    "profeetta": (
        "Etsi kohtia, jotka kuvaavat profeetallisen ja pastoraalisen tai "
        "opettavan roolin välistä dynamiikkaa, yhteistyötä tai jännitettä "
        "seurakunnassa."
    ),
    "paimen": (
        "Etsi kohtia, jotka kuvaavat profeetallisen ja pastoraalisen tai "
        "opettavan roolin välistä dynamiikkaa, yhteistyötä tai jännitettä "
        "seurakunnassa."
    ),
    "pappi": (
        "Etsi kohtia, jotka kuvaavat profeetallisen ja pastoraalisen tai "
        "opettavan roolin välistä dynamiikkaa, yhteistyötä tai jännitettä "
        "seurakunnassa."
    ),
    "koetinkivi": (
        "Etsi jakeita, jotka käsittelevät luonteen testaamista ja koettelemista "
        "erityisissä olosuhteissa, kuten vastoinkäymisissä, menestyksessä, "
        "kritiikin alla tai näkymättömyydessä."
    ),
    "testi": (
        "Etsi jakeita, jotka käsittelevät luonteen testaamista ja koettelemista "
        "erityisissä olosuhteissa, kuten vastoinkäymisissä, menestyksessä, "
        "kritiikin alla tai näkymättömyydessä."
    ),
    "näkymättömyys": (
        "Hae jakeita, jotka käsittelevät palvelemista ilman ihmisten "
        "näkemystä, kiitosta tai tunnustusta, keskittyen Jumalan palkkioon "
        "ja oikeaan sydämen asenteeseen."
    ),
    "kritiikki": (
        "Etsi jakeita, jotka opastavat, miten suhtautua oikeutetusti "
        "tai epäoikeutetusti saatuun kritiikkiin, arvosteluun tai "
        "nuhteeseen säilyttäen nöyrän ja opetuslapseen sopivan sydämen."
    ),
    "intohimo": (
        "Hae jakeita, jotka kuvaavat sydämen paloa, innostusta, "
        "syvää mielenkiintoa tai Jumalan antamaa tahtoa ja paloa "
        "tiettyä asiaa tai tehtävää kohtaan."
    ),
    "kyvyt": (
        "Etsi kohtia, jotka käsittelevät luontaisia, synnynnäisiä "
        "taitoja, lahjakkuutta ja osaamista, jotka Jumala on ihmiselle antanut "
        "ja joita voidaan käyttää hänen kunniakseen."
    )
}


# --- Lokituksen alustus ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)


@st.cache_resource
def lataa_resurssit():
    """Lataa kaikki tarvittavat resurssit kerran ja pitää ne muistissa."""
    logging.info("Ladataan hakumallit, indeksi ja datatiedostot muistiin...")
    try:
        model = SentenceTransformer(EMBEDDING_MALLI)
        cross_encoder = CrossEncoder(CROSS_ENCODER_MALLI)
        indeksi = faiss.read_index(VEKTORI_INDEKSI_TIEDOSTO)
        with open(VIITE_KARTTA_TIEDOSTO, "r", encoding="utf-8") as f:
            viite_kartta = json.load(f)
        with open(RAAMATTU_TIEDOSTO, "r", encoding="utf-8") as f:
            raamattu_data = json.load(f)
        jae_haku_kartta = {}
        for book_obj in raamattu_data["book"].values():
            kirjan_nimi = book_obj.get("info", {}).get("name")
            luvut_obj = book_obj.get("chapter")
            if not kirjan_nimi or not isinstance(luvut_obj, dict):
                continue
            for luku_nro, luku_obj in luvut_obj.items():
                jakeet_obj = luku_obj.get("verse")
                if not isinstance(jakeet_obj, dict):
                    continue
                for jae_nro, jae_obj in jakeet_obj.items():
                    teksti = jae_obj.get("text", "").strip()
                    if teksti:
                        viite = f"{kirjan_nimi} {luku_nro}:{jae_nro}"
                        jae_haku_kartta[viite] = teksti
        logging.info("Kaikki resurssit ladattu onnistuneesti.")
        return model, cross_encoder, indeksi, viite_kartta, jae_haku_kartta
    except Exception as e:
        logging.error(f"Kriittinen virhe resurssien alustuksessa: {e}")
        return None, None, None, None, None


def laajenna_kyselya_strategialla(kysely: str) -> str:
    """Analysoi ja laajentaa kyselyä strategiasanakirjan avulla."""
    pien_kysely = kysely.lower()
    for avainsana, selite in STRATEGIA_SANAKIRJA.items():
        if re.search(r'\\b' + avainsana + r'\\b', pien_kysely):
            laajennettu_kysely = f"{selite}. Alkuperäinen aihe on: {kysely}"
            logging.info(
                f"Strategia aktivoitu avainsanalla '{avainsana}'. "
                f"Laajennettu haku: \"{laajennettu_kysely[:100]}...\""
            )
            return laajennettu_kysely
    return kysely


def poimi_raamatunviitteet(teksti: str) -> list[str]:
    """Etsii ja poimii tekstistä raamatunviitteitä vankalla logiikalla."""
    pattern = r'((?:[1-3]\.\s)?[A-ZÅÄÖa-zåäö]+\.?\s\d+:\d+(?:-\d+)?)'
    return re.findall(pattern, teksti)


def hae_jakeet_viitteella(viite_str: str, jae_haku_kartta: dict) -> list[dict]:
    """Hakee jaejoukon tekstistä poimitun viitteen perusteella."""
    viite_pattern = re.compile(
        r'((?:[1-3]\.\s)?'
        r'[A-ZÅÄÖa-zåäö]+\.?)'
        r'\s(\d+):(\d+)(?:-(\d+))?'
    )
    match = viite_pattern.match(viite_str)
    if not match:
        return []

    kirja, luku, alku, loppu = match.groups()
    kirja = kirja.strip().lower().replace('.', '').replace(' ', '')
    luku_nro_str = str(int(luku))
    alku_jae = int(alku)
    loppu_jae = int(loppu) if loppu else alku_jae

    loytyneet = []
    for avain, teksti in jae_haku_kartta.items():
        avain_norm = avain.lower().replace('.', '').replace(' ', '')
        if kirja in avain_norm:
            try:
                luku_ja_jae_osa = avain.split(' ')[-1]
                haun_luku_str, haun_jae_str = luku_ja_jae_osa.split(':')
                haun_jae = int(haun_jae_str)
                if (haun_luku_str == luku_nro_str and
                        alku_jae <= haun_jae <= loppu_jae):
                    loytyneet.append({"viite": avain, "teksti": teksti})
            except (ValueError, IndexError):
                continue
    return sorted(loytyneet, key=lambda x: int(x['viite'].split(':')[-1]))


def etsi_merkityksen_mukaan(kysely: str, top_k: int = 15) -> list[dict]:
    """
    Etsii Raamatusta käyttäen logiikkaa, joka poimii ensin
    pakolliset jakeet ja täydentää sitten älyhaulla.
    """
    resurssit = lataa_resurssit()
    if not all(resurssit):
        logging.error("Haku epäonnistui, koska resursseja ei voitu ladata.")
        return []

    model, cross_encoder, indeksi, viite_kartta, jae_haku_kartta = resurssit

    viite_str_lista = poimi_raamatunviitteet(kysely)
    pakolliset_jakeet = []
    loytyneet_viitteet = set()
    for viite_str in viite_str_lista:
        jakeet = hae_jakeet_viitteella(viite_str, jae_haku_kartta)
        for jae in jakeet:
            if jae["viite"] not in loytyneet_viitteet:
                pakolliset_jakeet.append(jae)
                loytyneet_viitteet.add(jae["viite"])
    logging.info(
        f"Löydettiin {len(viite_str_lista)} viitettä, jotka vastasivat "
        f"{len(pakolliset_jakeet)} uniikkia jaetta."
    )

    alyhaun_tulokset = []
    if top_k > 0:
        laajennettu_kysely = laajenna_kyselya_strategialla(kysely)

        if top_k <= 10:
            kerroin = 10
        elif 11 <= top_k <= 20:
            kerroin = 9
        elif 21 <= top_k <= 40:
            kerroin = 8
        elif 41 <= top_k <= 60:
            kerroin = 7
        elif 61 <= top_k <= 80:
            kerroin = 6
        else:  # 81-100
            kerroin = 5

        haettava_maara = min(top_k * kerroin, indeksi.ntotal)
        if haettava_maara > 0:
            kysely_vektori = model.encode([laajennettu_kysely])
            _, indeksit = indeksi.search(
                np.array(kysely_vektori, dtype=np.float32), haettava_maara
            )
            ehdokkaat = []
            for idx in indeksit[0]:
                viite = viite_kartta.get(str(idx))
                if viite and viite not in loytyneet_viitteet:
                    ehdokkaat.append({
                        "viite": viite,
                        "teksti": jae_haku_kartta.get(viite, "")
                    })
            if ehdokkaat:
                parit = [[laajennettu_kysely, j["teksti"]] for j in ehdokkaat]
                pisteet = cross_encoder.predict(parit, show_progress_bar=False)
                for i, j in enumerate(ehdokkaat):
                    j['pisteet'] = pisteet[i]
                jarjestetyt = sorted(
                    ehdokkaat, key=lambda x: x['pisteet'], reverse=True
                )
                alyhaun_tulokset = jarjestetyt[:top_k]

    lopulliset_tulokset = pakolliset_jakeet + alyhaun_tulokset
    logging.info(
        f"Yhdistetty {len(pakolliset_jakeet)} pakollista jaetta ja "
        f"{len(alyhaun_tulokset)} älyhaun tulosta. "
        f"Yhteensä {len(lopulliset_tulokset)} jaetta."
    )
    return lopulliset_tulokset