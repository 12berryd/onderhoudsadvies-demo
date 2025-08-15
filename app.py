import json
from datetime import datetime, date
from typing import List, Dict, Any
import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Pagina-instellingen
# ---------------------------------------------------------
st.set_page_config(
    page_title="Onderhoudsadvies Demo",
    page_icon="🔧",
    layout="centered"
)

st.title("🔧 Onderhoudsadvies Demo")
st.markdown("Voer voertuiggegevens in en genereer een onderhoudsadvies.")

# ---------------------------------------------------------
# Regelengine (verbeterde regels)
# ---------------------------------------------------------
def regelengine(kenteken: str, km_stand: int, brandstof: str,
                klachten: List[str], onderhoudshistorie: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    adviezen: List[Dict[str, Any]] = []
    now = datetime.now()

    def near_threshold(km: int, interval: int, window: int = 5000) -> bool:
        """True als je binnen 'window' km van een intervalgrens zit, vóór of ná die grens."""
        r = km % interval
        return (r <= window) or (interval - r <= window)

    def had_event_within(keywords: List[str], days: int) -> bool:
        """True als een event waarvan 'type' een keyword bevat, binnen 'days' dagen is gedaan."""
        for e in onderhoudshistorie:
            if not isinstance(e, dict):
                continue
            t = str(e.get("type", "")).lower()
            if any(kw in t for kw in keywords):
                try:
                    if e.get("datum"):
                        dt = datetime.fromisoformat(e["datum"])
                        if (now - dt).days <= days:
                            return True
                except Exception:
                    pass
        return False

    def last_event_age_days(keywords: List[str]) -> int | None:
        """Aantal dagen sinds het laatste event (minst recente datum) voor de gegeven keywords."""
        ages = []
        for e in onderhoudshistorie:
            if not isinstance(e, dict):
                continue
            t = str(e.get("type", "")).lower()
            if any(kw in t for kw in keywords) and e.get("datum"):
                try:
                    dt = datetime.fromisoformat(e["datum"])
                    ages.append((now - dt).days)
                except Exception:
                    pass
        return min(ages) if ages else None

    is_tiguan = "TIGUAN" in kenteken.upper() or "VW" in kenteken.upper()
    is_benzine = brandstof.lower() == "benzine"

    # --- 1) Kleine beurt (olie + oliefilter): jaarlijks of elke ~15.000 km (±3.000 km venster) ---
    age_olie_days = last_event_age_days(["olie", "oliefilter"])
    due_by_time = (age_olie_days is None) or (age_olie_days > 365)
    due_by_km = near_threshold(km_stand, interval=15000, window=3000)
    if due_by_time or due_by_km:
        adviezen.append({
            "categorie": "Motorolie & filter",
            "advies": "Plan een kleine beurt (olie + oliefilter)",
            "urgentie": "normaal",
            "toelichting": "Richtlijn jaarlijks of elke ~15.000 km (±3.000 km venster)",
            "richtprijs_eur": 180
        })

    # --- 2) Bougies (benzine): elke ~60.000 km (±5.000 km venster) ---
    if is_benzine and near_threshold(km_stand, interval=60000, window=5000):
        adviezen.append({
            "categorie": "Bougies",
            "advies": "Vervang bougies",
            "urgentie": "normaal",
            "toelichting": "Benzinemotor, rond elke 60.000 km (±5.000 km venster)",
            "richtprijs_eur": 140
        })

    # --- 3) Remmen bij klachten ---
    klachten_lc = [s.lower() for s in klachten]
    if any(k in klachten_lc for k in ["trillen", "piepen", "scheef trekken", "zwakke remmen", "lange remweg"]):
        adviezen.append({
            "categorie": "Remmen",
            "advies": "Controleer schijven/blokken en remvloeistof",
            "urgentie": "hoog",
            "toelichting": "Klachten duiden op verhoogde slijtage of ongelijkmatige aanname",
            "richtprijs_eur": 250
        })

    # --- 4) Luchtfilter: elke ~30.000 km (±5.000 km venster) ---
    if near_threshold(km_stand, interval=30000, window=5000):
        adviezen.append({
            "categorie": "Luchtfilter",
            "advies": "Vervang luchtfilter",
            "urgentie": "normaal",
            "toelichting": "Elke ~30.000 km (±5.000 km venster) of bij vermogensverlies",
            "richtprijs_eur": 35
        })

    # --- 5) Interieur/pollenfilter: jaarlijks ---
    if not had_event_within(["pollenfilter", "interieurfilter"], days=365):
        adviezen.append({
            "categorie": "Interieur/pollenfilter",
            "advies": "Vervang interieurfilter",
            "urgentie": "laag",
            "toelichting": "Aanbevolen jaarlijks voor schone lucht in de cabine",
            "richtprijs_eur": 30
        })

    # --- 6) DSG/automaatolie: rond elke 60.000 km (±5.000 km venster), indien van toepassing ---
    if is_tiguan and near_threshold(km_stand, interval=60000, window=5000):
        adviezen.append({
            "categorie": "Transmissie",
            "advies": "Ververs automaat-/DSG-olie indien van toepassing",
            "urgentie": "normaal",
            "toelichting": "Veel VAG-automaten: rond elke 60.000 km (±5.000 km venster)",
            "richtprijs_eur": 350
        })

    # --- 7) Remvloeistof: elke 2 jaar ---
    if not had_event_within(["remvloeistof"], days=730):
        adviezen.append({
            "categorie": "Remvloeistof",
            "advies": "Ververs remvloeistof",
            "urgentie": "normaal",
            "toelichting": "Elke 2 jaar i.v.m. hygroscopische werking",
            "richtprijs_eur": 70
        })

    # --- 8) Onregelmatig stationair ---
    if any("onregelmatig stationair" in s for s in klachten_lc):
        adviezen.append({
            "categorie": "Inlaat/PCV",
            "advies": "Controleer gasklepbehuizing en PCV-klep op vervuiling/defect",
            "urgentie": "normaal",
            "richtprijs_eur": 120
        })

    return adviezen

# ---------------------------------------------------------
# Helpers voor onderhoudshistorie
# ---------------------------------------------------------
def normalize_historie_from_editor(edited_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Zet data_editor output om naar nette lijst van dicts met datum-string."""
    records: List[Dict[str, Any]] = []
    if edited_df is None or edited_df.empty:
        return records

    for r in edited_df.to_dict(orient="records"):
        # lege rijen overslaan
        if not any([r.get("datum"), r.get("type"), r.get("km_stand"), r.get("opmerkingen")]):
            continue

        d = r.get("datum")
        # Ondersteun pd.Timestamp, datetime, date en strings/NaT
        if pd.isna(d):
            d_str = None
        elif isinstance(d, (pd.Timestamp, datetime, date)):
            d_str = pd.to_datetime(d).strftime("%Y-%m-%d")
        else:
            d_str = str(d).strip() if d else None

        # km naar int
        km = r.get("km_stand")
        try:
            km_int = int(km) if (km is not None and not pd.isna(km) and str(km) != "") else None
        except Exception:
            km_int = None

        records.append({
            "datum": d_str if d_str else None,
            "type": (r.get("type") or "").strip(),
            "km_stand": km_int,
            "opmerkingen": (r.get("opmerkingen") or "").strip() or None
        })
    return records

# ---------------------------------------------------------
# Invoer velden
# ---------------------------------------------------------
kenteken = st.text_input("Kenteken", value="VW-TIGUAN-TEST")
km_stand = st.number_input("Kilometerstand", min_value=0, value=61500, step=500)
brandstof = st.selectbox("Brandstof", ["benzine", "diesel", "hybride", "elektrisch"])
klachten = st.multiselect(
    "Klachten",
    ["trillen", "piepen", "scheef trekken", "zwakke remmen", "lange remweg", "onregelmatig stationair"],
    default=[]
)

# ---------------------------------------------------------
# Onderhoudshistorie: alleen de strakke tabel (geen JSON)
# ---------------------------------------------------------
st.subheader("Onderhoudshistorie (optioneel)")

_default_rows = [
    {"datum": "2023-05-10", "type": "Olie + filter", "km_stand": 48000, "opmerkingen": ""},
    {"datum": "2022-09-01", "type": "Remvloeistof verversen", "km_stand": 40000, "opmerkingen": ""},
]

# Maak DataFrame en zet 'datum' expliciet om naar datetime64[ns] en km_stand naar numeriek
df_init = pd.DataFrame(_default_rows)
df_init["datum"] = pd.to_datetime(df_init["datum"], errors="coerce")
df_init["km_stand"] = pd.to_numeric(df_init["km_stand"], errors="coerce")

edited = st.data_editor(
    df_init,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "datum": st.column_config.DateColumn("Datum", format="YYYY-MM-DD"),
        "type": st.column_config.TextColumn("Type"),
        "km_stand": st.column_config.NumberColumn("Kilometerstand", min_value=0, step=500),
        "opmerkingen": st.column_config.TextColumn("Opmerkingen"),
    },
    key="hist_editor",
)
onderhoudshistorie: List[Dict[str, Any]] = normalize_historie_from_editor(edited)

# ---------------------------------------------------------
# Actieknop en resultaat
# ---------------------------------------------------------
if st.button("Genereer advies"):
    try:
        km = int(km_stand)
    except Exception:
        st.error("Kilometerstand moet een getal zijn.")
        km = 0
    adviezen = regelengine(kenteken, km, brandstof, klachten, onderhoudshistorie)

    st.subheader("Resultaat")
    result = {
        "voertuig": {"kenteken": kenteken, "brandstof": brandstof},
        "peildatum": datetime.now().strftime("%Y-%m-%d"),
        "km_stand": km,
        "adviezen": adviezen
    }
    st.json(result)

    # Overzicht in tabel
    if adviezen:
        st.markdown("**Overzicht adviezen**")
        st.dataframe(pd.DataFrame(adviezen), use_container_width=True)
    else:
        st.info("Geen adviezen op basis van de huidige invoer.")
