import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- DONNÉES DE RÉFÉRENCE ---
PRODUITS = {
    "Viande fraîche": {"cp": 3.2, "t_stock": 2},
    "Viande congelée": {"cp": 1.8, "t_stock": -20},
    "Fruits et Légumes": {"cp": 3.7, "t_stock": 6},
    "Poisson frais": {"cp": 3.5, "t_stock": 1},
    "Poisson congelé": {"cp": 2.0, "t_stock": -25},
    "Produits Laitiers": {"cp": 3.3, "t_stock": 4},
    "Crème glacée": {"cp": 2.1, "t_stock": -22},
    "Autre (Manuel)": {"cp": 3.0, "t_stock": 2}
}

st.set_page_config(page_title="Expert Frigo Pro", layout="wide")

if 'bilans' not in st.session_state:
    st.session_state.bilans = []

st.title("❄️ Logiciel de Bilan Thermique Frigorifique")

# --- SECTION INFORMATIONS CLIENT ---
with st.expander("📝 Informations Client & Projet", expanded=False):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        client_nom = st.text_input("Nom du Client / Entreprise", "Client de test")
    with col_c2:
        projet_ref = st.text_input("Référence du projet", "PRO-2024-001")

# --- FORMULAIRE DE SAISIE ---
with st.form("form_global"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📍 Local & Produit")
        nom = st.text_input("Nom de la chambre", "Chambre 01")
        produit_sel = st.selectbox("Type de produit", list(PRODUITS.keys()))
        t_stock_pre = PRODUITS[produit_sel]["t_stock"]
        t_int = st.number_input("T° à maintenir (°C)", value=t_stock_pre)
        t_ext = st.number_input("T° Ambiante Ext. (°C)", value=30)
    with col2:
        st.subheader("📐 Enveloppe (m)")
        L = st.number_input("Longueur", value=4.0)
        W = st.number_input("Largeur", value=3.0)
        H = st.number_input("Hauteur", value=2.5)
        iso = st.selectbox("Isolant PUR (mm)", [60, 80, 100, 120, 140, 200], index=2)
    with col3:
        st.subheader("⚡ Exploitation")
        masse = st.number_input("Rotation/jour (kg)", value=500)
        t_entree = st.number_input("T° entrée produit (°C)", value=t_int + 15)
        prix_kwh = st.number_input("Prix kWh (EUR)", value=0.22)
        cop = st.slider("COP du groupe", 1.0, 4.5, 2.5)

    submit = st.form_submit_button("AJOUTER AU BILAN")

if submit:
    cp = PRODUITS[produit_sel]["cp"]
    
    # CALCULS
    surface_parois = 2 * (L*W + L*H + W*H)
    volume = L * W * H
    k = 0.022 / (iso / 1000)
    
    q_parois = k * surface_parois * (t_ext - t_int)
    q_produit = (masse * cp * (t_entree - t_int)) / 86.4
    
    puissance_groupe = (q_parois + q_produit) * 1.2 * (24 / 18)
    conso_annuelle = (puissance_groupe / 1000) * 18 * 365 / cop
    
    st.session_state.bilans.append({
        "Chambre": str(nom),
        "T° Cons.": int(t_int),
        "Vol (m3)": round(volume, 1),
        "Surf (m2)": round(surface_parois, 1),
        "Puis. (W)": int(puissance_groupe),
        "kWh/an": int(conso_annuelle),
        "Cout/an (EUR)": int(conso_annuelle * prix_kwh)
    })

# --- AFFICHAGE ET EXPORTS ---
if st.session_state.bilans:
    df = pd.DataFrame(st.session_state.bilans)
    st.subheader(f"📊 Récapitulatif Projet : {projet_ref} ({client_nom})")
    st.table(df)

    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Télécharger pour Excel (CSV)", data=csv, file_name=f"bilan_{projet_ref}.csv", mime="text/csv")

    with col_exp2:
        def generate_pdf(data_df, client, ref):
            pdf = FPDF()
            pdf.add_page()
            # En-tête Client
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "RAPPORT D'EXPERTISE FRIGORIFIQUE", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(190, 8, f"Client : {client} | Projet : {ref}", ln=True, align='C')
            pdf.cell(190, 8, f"Date : {datetime.date.today()}", ln=True, align='C')
            pdf.ln(10)
            
            # Header Tableau
            pdf.set_font("Arial", 'B', 8)
            col_width = 190 / len(data_df.columns)
            for col in data_df.columns:
                pdf.cell(col_width, 10, str(col), border=1, align='C')
            pdf.ln()
            
            # Données
            pdf.set_font("Arial", '', 8)
            for _, row in data_df.iterrows():
                for val in row:
                    txt = str(val).replace('\u20ac', 'EUR').replace('°', 'deg')
                    pdf.cell(col_width, 10, txt.encode('latin-1', 'replace').decode('latin-1'), border=1, align='C')
                pdf.ln()
            return pdf.output(dest='S').encode('latin-1', 'replace')

        try:
            pdf_bytes = generate_pdf(df, client_nom, projet_ref)
            st.download_button("📥 Télécharger le Rapport PDF", data=pdf_bytes, file_name=f"Rapport_{projet_ref}.pdf")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

    with col_exp3:
        if st.button("🗑️ Tout effacer"):
            st.session_state.bilans = []
            st.rerun()
