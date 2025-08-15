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
# Regelengine (eenvoudige regels voor demo)
# ---------------------------------------------------------
def regelengine(kenteken: str, km_stand: int, brandstof: str,
                klachten: List[str], onderhoudshistorie: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    adviezen: List[Dict[str, Any]] = []

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

    # 3. Remmen controleren bij klachten
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

    # 5. Pollenfilter jaarlijks (check laatste 12 maanden)
    had_pollen_12m = False
    for e in onderhoudshistorie:
        if isinstance(e, dict) and str(e.get("type", "")).lower() in ["pollenfilter", "interieurfilter"]:
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

    # 7. Remvloeistof elke 2 jaar (check laatste 24 maanden)
    had_remvloeistof_24m = False
    for e in onderhoudshistorie:
        if isinstance(e, dict) and "remvloeistof" in str(e.get("type", "")).lower():
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
# Onderhoudshistorie: simpele tabel of geavanceerde JSON
# ---------------------------------------------------------
st.subheader("Onderhoudshistorie (optioneel)")

_default_rows = [
    {"datum": "2023-05-10", "type": "Olie + filter", "km_stand": 48000, "opmerkingen": ""},
    {"datum": "2022-09-01", "type": "Remvloeistof verversen", "km_stand": 40000, "opmerkingen": ""},
]

geavanceerd = st.toggle("Geavanceerde modus (JSON)", value=False,
                        help="Zet aan als je liever zelf JSON plakt.")

onderhoudshistorie: List[Dict[str, Any]] = []

if not geavanceerd:
    # Maak DataFrame en zet 'datum' expliciet om naar datetime64[ns]
    df_init = pd.DataFrame(_default_rows)
    df_init["datum"] = pd.to_datetime(df_init["datum"], errors="coerce")
    # (optioneel) km als integer-achtige kolom
    df_init["km_stand"] = pd.to_numeric(df_init["km_stand"], errors="coerce")

    edited = st.data_editor(
        df_init,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            # DateColumn verwacht een tijd-achtig dtype; we hebben 'datum' hierboven geconverteerd
            "datum": st.column_config.DateColumn("Datum", format="YYYY-MM-DD"),
            "type": st.column_config.TextColumn("Type"),
            "km_stand": st.column_config.NumberColumn("Kilometerstand", min_value=0, step=500),
            "opmerkingen": st.column_config.TextColumn("Opmerkingen"),
        },
        key="hist_editor",
    )
    onderhoudshistorie = normalize_historie_from_editor(edited)
else:
    st.caption("Plak hieronder JSON (een lijst van objecten met velden: datum, type, km_stand, opmerkingen).")
    hist_text = st.text_area(
        "JSON",
        value=json.dumps(_default_rows, indent=2, ensure_ascii=False),
        height=180
    )
    try:
        parsed = json.loads(hist_text)
        if not isinstance(parsed, list):
            raise ValueError("De JSON moet een lijst zijn (dus beginnen met [ en eindigen met ]).")
        st.success("Geldige JSON ✔")
        onderhoudshistorie = parsed
    except Exception as e:
        st.error(f"Ongeldige JSON: {e}")
        onderhoudshistorie = []

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

    # Optioneel: tabelweergave van adviezen
    if adviezen:
        st.markdown("**Overzicht adviezen**")
        st.dataframe(pd.DataFrame(adviezen), use_container_width=True)
    else:
        st.info("Geen adviezen op basis van de huidige invoer.")
