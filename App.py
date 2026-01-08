import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- DONNÉES DE RÉFÉRENCE ---
PRODUITS = {
    "Viande fraîche": {"cp": 3.2, "t_stock": 2, "regime": "Positif"},
    "Viande congelée": {"cp": 1.8, "t_stock": -20, "regime": "Négatif"},
    "Fruits et Légumes": {"cp": 3.7, "t_stock": 6, "regime": "Positif"},
    "Poisson frais": {"cp": 3.5, "t_stock": 1, "regime": "Positif"},
    "Poisson congelé": {"cp": 2.0, "t_stock": -25, "regime": "Négatif"},
    "Produits Laitiers": {"cp": 3.3, "t_stock": 4, "regime": "Positif"},
    "Crème glacée": {"cp": 2.1, "t_stock": -22, "regime": "Négatif"},
    "Autre (Manuel)": {"cp": 3.0, "t_stock": 2, "regime": "Positif"}
}

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Expert Frigo Pro", layout="wide")

if 'bilans' not in st.session_state:
    st.session_state.bilans = []

st.title("❄️ Logiciel de Bilan Thermique Frigorifique")
st.markdown("Calcul de puissance, consommation énergétique et export de rapports.")

# --- FORMULAIRE DE SAISIE ---
with st.form("form_global"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📍 Local & Produit")
        nom = st.text_input("Nom de la chambre", "Chambre 01")
        produit_sel = st.selectbox("Type de produit", list(PRODUITS.keys()))
        t_ext = st.number_input("T° Ambiante Ext. (°C)", value=30)
        
    with col2:
        st.subheader("📐 Enveloppe (m)")
        L = st.number_input("Longueur", value=4.0)
        W = st.number_input("Largeur", value=3.0)
        H = st.number_input("Hauteur", value=2.5)
        iso = st.selectbox("Épaisseur Isolation PUR (mm)", [60, 80, 100, 120, 140, 200], index=2)
        
    with col3:
        st.subheader("⚡ Exploitation")
        masse = st.number_input("Rotation/jour (kg)", value=500)
        t_entree = st.number_input("T° entrée produit (°C)", value=15)
        prix_kwh = st.number_input("Prix kWh (€)", value=0.22)
        cop = st.slider("COP du groupe", 1.0, 4.5, 2.8 if "Positif" in PRODUITS[produit_sel]["regime"] else 1.6)

    submit = st.form_submit_button("AJOUTER AU BILAN GLOBAL")

# --- LOGIQUE DE CALCUL ---
if submit:
    t_int = PRODUITS[produit_sel]["t_stock"]
    cp = PRODUITS[produit_sel]["cp"]
    
    # 1. Déperditions Parois (λ PUR = 0.022)
    surface = 2 * (L*W + L*H + W*H)
    k = 0.022 / (iso / 1000)
    q_parois = k * surface * (t_ext - t_int)
    
    # 2. Charge Produit
    q_produit = (masse * cp * (t_entree - t_int)) / (24 * 3.6) # Watts
    
    # 3. Renouvellement & Divers (15% forfaitaire)
    q_base = q_parois + q_produit
    q_total_continu = q_base * 1.15
    
    # 4. Puissance Groupe (Marche 18h/24)
    puissance_groupe = q_total_continu * (24 / 18)
    
    # 5. Énergie & Coût
    conso_annuelle = (puissance_groupe / 1000) * 18 * 365 / cop
    cout_annuel = conso_annuelle * prix_kwh
    
    st.session_state.bilans.append({
        "Chambre": nom,
        "Produit": produit_sel,
        "Dim.": f"{L}x{W}",
        "Pois (W)": round(puissance_groupe),
        "kWh/an": round(conso_annuelle),
        "Coût/an (€)": round(cout_annuel)
    })

# --- RÉSULTATS ET EXPORT ---
if st.session_state.bilans:
    st.divider()
    df = pd.DataFrame(st.session_state.bilans)
    st.subheader("📋 Récapitulatif du Projet")
    st.dataframe(df, use_container_width=True)

    # Fonction PDF
    def generate_pdf(data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, "RAPPORT DE SYNTHESE THERMIQUE", ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        pdf.cell(190, 10, f"Généré le : {datetime.date.today()}", ln=True, align='C')
        pdf.ln(10)
        
        # En-têtes
        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Arial", 'B', 9)
        cols = list(data.columns)
        for col in cols:
            pdf.cell(31, 10, col, border=1, align='C', fill=True)
        pdf.ln()
        
        # Données
        pdf.set_font("Arial", '', 9)
        for index, row in data.iterrows():
            for col in cols:
                pdf.cell(31, 10, str(row[col]), border=1, align='C')
            pdf.ln()
        
        return pdf.output(dest='S').encode('latin-1')

    pdf_file = generate_pdf(df)
    st.download_button(
        label="📥 Télécharger le Rapport PDF",
        data=pdf_file,
        file_name="bilan_frigorifique.pdf",
        mime="application/pdf"
    )

    if st.button("🗑️ Effacer tout"):
        st.session_state.bilans = []
        st.rerun()
