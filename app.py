import json
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="Onderhoudsadvies Demo", page_icon="🔧", layout="centered")
st.title("🔧 Onderhoudsadvies Demo")

st.markdown("Voer voertuiggegevens in en genereer een onderhoudsadvies.")

kenteken = st.text_input("Kenteken", value="VW-TIGUAN-TEST")
km_stand = st.number_input("Kilometerstand", min_value=0, value=61500, step=500)
brandstof = st.selectbox("Brandstof", ["benzine", "diesel", "hybride", "elektrisch"])
klachten = st.multiselect("Klachten", [
    "trillen", "piepen", "scheef trekken", "zwakke remmen", "lange remweg",
    "onregelmatig stationair"
])

st.markdown("**Onderhoudshistorie (optioneel, JSON lijst)**")
default_hist = json.dumps([
    {"datum":"2023-05-10","type":"Olie + filter","km_stand":48000},
    {"datum":"2022-09-01","type":"Remvloeistof verversen","km_stand":40000}
], indent=2, ensure_ascii=False)
hist_text = st.text_area("Bijv.:", value=default_hist, height=160)

def parse_hist(txt):
    try:
        data = json.loads(txt)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

def regelengine(kenteken, km_stand, brandstof, klachten, onderhoudshistorie):
    adviezen = []

    is_tiguan = "TIGUAN" in kenteken.upper() or "VW" in kenteken.upper()

    # 1. Olie/filters elke 15.000 km
    if km_stand % 15000 >= 12000:
        adviezen.append({
            "categorie": "Motorolie & filter",
            "advies": "Plan een kleine beurt (olie + oliefilter)",
            "urgentie": "normaal",
            "toelichting": "Richtlijn elke 15.000 km of jaarlijks",
            "richtprijs_eur": 180
        })

    # 2. Bougies benzine elke 60.000 km
    if brandstof.lower() == "benzine" and km_stand >= 60000 and (km_stand % 60000) >= 55000:
        adviezen.append({
            "categorie": "Bougies",
            "advies": "Vervang bougies",
            "urgentie": "normaal",
            "toelichting": "Benzinemotor, elke ~60.000 km",
            "richtprijs_eur": 140
        })

    # 3. Remmen bij klachten
    klachten_lc = [s.lower() for s in klachten]
    if any(k in klachten_lc for k in ["trillen", "piepen", "scheef trekken", "zwakke remmen", "lange remweg"]):
        adviezen.append({
            "categorie": "Remmen",
            "advies": "Controleer schijven/blokken en remvloeistof",
            "urgentie": "hoog",
            "toelichting": "Klachten duiden op verhoogde slijtage of ongelijkmatige aanname",
            "richtprijs_eur": 250
        })

    # 4. Luchtfilter elke 30.000 km
    if km_stand % 30000 >= 25000:
        adviezen.append({
            "categorie": "Luchtfilter",
            "advies": "Vervang luchtfilter",
            "urgentie": "normaal",
            "toelichting": "Elke 30.000 km of bij vermogensverlies",
            "richtprijs_eur": 35
        })

    # 5. Pollenfilter jaarlijks
    had_pollen_12m = False
    for e in onderhoudshistorie:
        if isinstance(e, dict) and str(e.get("type","")).lower() in ["pollenfilter", "interieurfilter"]:
            try:
                if e.get("datum"):
                    dt = datetime.fromisoformat(e["datum"])
                    if (datetime.now() - dt).days <= 365:
                        had_pollen_12m = True
            except Exception:
                pass
    if not had_pollen_12m:
        adviezen.append({
            "categorie": "Interieur/pollenfilter",
            "advies": "Vervang interieurfilter",
            "urgentie": "laag",
            "toelichting": "Aanbevolen jaarlijks voor schone lucht in de cabine",
            "richtprijs_eur": 30
        })

    # 6. DSG/automaat olie (voorbeeld): elke 60.000 km
    if is_tiguan and km_stand >= 60000 and (km_stand % 60000) >= 55000:
        adviezen.append({
            "categorie": "Transmissie",
            "advies": "Ververs automaat-/DSG-olie indien van toepassing",
            "urgentie": "normaal",
            "toelichting": "Veel VAG-automaten: elke ~60.000 km",
            "richtprijs_eur": 350
        })

    # 7. Remvloeistof elke 2 jaar
    had_remvloeistof_24m = False
    for e in onderhoudshistorie:
        if isinstance(e, dict) and "remvloeistof" in str(e.get("type","")).lower():
            try:
                if e.get("datum"):
                    dt = datetime.fromisoformat(e["datum"])
                    if (datetime.now() - dt).days <= 730:
                        had_remvloeistof_24m = True
            except Exception:
                pass
    if not had_remvloeistof_24m:
        adviezen.append({
            "categorie": "Remvloeistof",
            "advies": "Ververs remvloeistof",
            "urgentie": "normaal",
            "toelichting": "Elke 2 jaar i.v.m. hygroscopische werking",
            "richtprijs_eur": 70
        })

    # 8. Onregelmatig stationair
    if any("onregelmatig stationair" in s.lower() for s in klachten):
        adviezen.append({
            "categorie": "Inlaat/PCV",
            "advies": "Controleer gasklepbehuizing en PCV-klep op vervuiling/defect",
            "urgentie": "normaal",
            "richtprijs_eur": 120
        })

    return adviezen

if st.button("Genereer advies"):
    historie = parse_hist(hist_text)
    adviezen = regelengine(kenteken, km_stand, brandstof, klachten, historie)

    st.subheader("Resultaat")
    st.json({
        "voertuig": {"kenteken": kenteken, "brandstof": brandstof},
        "peildatum": datetime.now().strftime("%Y-%m-%d"),
        "km_stand": km_stand,
        "adviezen": adviezen
    })
