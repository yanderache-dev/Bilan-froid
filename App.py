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

# Initialisation
if 'bilans' not in st.session_state:
    st.session_state.bilans = []

st.title("❄️ Logiciel de Bilan Thermique Frigorifique")

# --- FORMULAIRE ---
with st.form("form_global"):
    col1, col2, col3 = st.columns(3)
    with col1:
        nom = st.text_input("Nom de la chambre", "Chambre 01")
        produit_sel = st.selectbox("Type de produit", list(PRODUITS.keys()))
        t_ext = st.number_input("T° Ambiante Ext. (°C)", value=30)
    with col2:
        L = st.number_input("Longueur (m)", value=4.0)
        W = st.number_input("Largeur (m)", value=3.0)
        H = st.number_input("Hauteur (m)", value=2.5)
        iso = st.selectbox("Isolant PUR (mm)", [60, 80, 100, 120, 140, 200], index=2)
    with col3:
        masse = st.number_input("Rotation/jour (kg)", value=500)
        t_entree = st.number_input("T° entrée produit (°C)", value=15)
        prix_kwh = st.number_input("Prix kWh (€)", value=0.22)
        cop = st.slider("COP du groupe", 1.0, 4.5, 2.5)

    submit = st.form_submit_button("AJOUTER AU BILAN")

if submit:
    t_int = PRODUITS[produit_sel]["t_stock"]
    cp = PRODUITS[produit_sel]["cp"]
    
    # CALCULS
    surface = 2 * (L*W + L*H + W*H)
    k = 0.022 / (iso / 1000)
    q_parois = k * surface * (t_ext - t_int)
    q_produit = (masse * cp * (t_entree - t_int)) / 86.4
    
    puissance_groupe = (q_parois + q_produit) * 1.2 * (24 / 18)
    conso_annuelle = (puissance_groupe / 1000) * 18 * 365 / cop
    
    # Ajout sécurisé
    nouvelle_ligne = {
        "Nom": str(nom),
        "Produit": str(produit_sel),
        "Puis. (W)": int(puissance_groupe),
        "kWh/an": int(conso_annuelle),
        "Cout/an (€)": int(conso_annuelle * prix_kwh)
    }
    st.session_state.bilans.append(nouvelle_ligne)

# --- AFFICHAGE ET EXPORT ---
if st.session_state.bilans:
    df = pd.DataFrame(st.session_state.bilans)
    st.subheader("📋 Récapitulatif du Projet")
    st.table(df) # Utilisation de table pour éviter les bugs d'index de dataframe

    # Générateur PDF corrigé
    def generate_pdf(data_df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(190, 10, "RAPPORT THERMIQUE", ln=True, align='C')
        pdf.ln(5)
        
        # En-têtes
        pdf.set_font("Arial", 'B', 10)
        for col in data_df.columns:
            pdf.cell(38, 10, str(col), border=1, align='C')
        pdf.ln()
        
        # Lignes
        pdf.set_font("Arial", '', 9)
        for _, row in data_df.iterrows():
            for val in row:
                # On remplace les caractères spéciaux pour éviter les erreurs Latin-1
                txt = str(val).replace('€', 'EUR').replace('°', 'deg')
                pdf.cell(38, 10, txt, border=1, align='C')
            pdf.ln()
        return pdf.output(dest='S').encode('latin-1', 'replace')

    try:
        pdf_bytes = generate_pdf(df)
        st.download_button("📥 Télécharger le Rapport PDF", data=pdf_bytes, file_name="bilan.pdf")
    except Exception as e:
        st.error(f"Erreur lors de la préparation du PDF : {e}")

    if st.button("🗑️ Effacer tout"):
        st.session_state.bilans = []
        st.rerun()
