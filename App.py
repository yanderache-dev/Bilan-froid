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
        client_nom = st.text_input("Nom du Client / Entreprise", "Projet Client")
    with col_c2:
        projet_ref = st.text_input("Référence du projet", f"REF-{datetime.date.today().year}")

# --- FORMULAIRE DE SAISIE ---
with st.form("form_global"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📍 Local & Produit")
        nom = st.text_input("Nom de la chambre", "Chambre 01")
        produit_sel = st.selectbox("Type de produit", list(PRODUITS.keys()))
        t_int = st.number_input("T° à maintenir (°C)", value=PRODUITS[produit_sel]["t_stock"])
        t_ext = st.number_input("T° Ambiante Ext. (°C)", value=32)
        
    with col2:
        st.subheader("📐 Enveloppe (m)")
        L = st.number_input("Longueur", value=4.0)
        W = st.number_input("Largeur", value=3.0)
        H = st.number_input("Hauteur", value=2.5)
        iso = st.selectbox("Isolant PUR (mm)", [60, 80, 100, 120, 140, 200], index=2)
        
    with col3:
        st.subheader("⚡ Exploitation")
        masse = st.number_input("Rotation/jour (kg)", value=500)
        # Valeur par défaut = T° de consigne (produit arrive à température)
        t_entree = st.number_input("T° entrée produit (°C)", value=t_int)
        prix_kwh = st.number_input("Prix kWh (EUR)", value=0.22)
        cop = st.slider("COP du groupe", 1.0, 4.5, 2.8 if t_int > 0 else 1.6)

    submit = st.form_submit_button("AJOUTER AU BILAN")

# --- MOTEUR DE CALCUL ---
if submit:
    cp = PRODUITS[produit_sel]["cp"]
    vol = L * W * H
    surf_sol = L * W
    surf_parois = 2 * (L*W + L*H + W*H)
    k = 0.022 / (iso / 1000)
    
    # 1. Déperditions parois
    q_parois = k * surf_parois * (t_ext - t_int)
    
    # 2. Apport produit (0 si T° entrée = T° consigne)
    q_produit = (masse * cp * max(0, t_entree - t_int)) / 86.4
    
    # 3. Renouvellement d'air (Renforcé pour coller à la réalité métier)
    nb_renouv = 25 if vol < 40 else 15
    q_air = (vol * nb_renouv * 0.35 * (t_ext - t_int)) / 24
    
    # 4. Apports internes (Ventilateurs + Éclairage)
    q_interne = surf_sol * 15 
    
    # 5. Total avec coefficient de sécurité (10%)
    q_total_flux = (q_parois + q_produit + q_air + q_interne) * 1.10
    
    # 6. Puissance installée (Temps de marche 18h/24h)
    puissance_groupe = q_total_flux * (24 / 18)
    
    conso_annuelle = (puissance_groupe / 1000) * 18 * 365 / cop
    
    st.session_state.bilans.append({
        "Nom": str(nom),
        "T° Cons.": int(t_int),
        "Vol (m3)": round(vol, 1),
        "Surf (m2)": round(surf_sol, 1),
        "Puis. (W)": int(puissance_groupe),
        "kWh/an": int(conso_annuelle),
        "Cout/an (EUR)": int(conso_annuelle * prix_kwh)
    })

# --- AFFICHAGE ET EXPORTS ---
if st.session_state.bilans:
    df = pd.DataFrame(st.session_state.bilans)
    st.subheader(f"📊 Projet : {projet_ref} - Client : {client_nom}")
    st.table(df)

    c1, c2, c3 = st.columns(3)
    
    with c1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📊 Excel (CSV)", data=csv, file_name=f"Bilan_{projet_ref}.csv")

    with c2:
        def generate_pdf(data_df, client, ref):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, "RAPPORT D'EXPERTISE THERMIQUE", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(190, 8, f"Client : {client} | Ref : {ref}", ln=True, align='C')
            pdf.ln(10)
            
            # Header
            pdf.set_font("Arial", 'B', 8)
            cw = 190 / len(data_df.columns)
            for col in data_df.columns:
                pdf.cell(cw, 10, str(col), border=1, align='C')
            pdf.ln()
            
            # Données
            pdf.set_font("Arial", '', 8)
            for _, row in data_df.iterrows():
                for val in row:
                    txt = str(val).replace('€', 'EUR').replace('°', 'deg')
                    pdf.cell(cw, 10, txt.encode('latin-1', 'replace').decode('latin-1'), border=1, align='C')
                pdf.ln()
            return pdf.output(dest='S').encode('latin-1', 'replace')

        pdf_bytes = generate_pdf(df, client_nom, projet_ref)
        st.download_button("📥 Rapport PDF", data=pdf_bytes, file_name=f"Bilan_{projet_ref}.pdf")

    with c3:
        if st.button("🗑️ Effacer tout"):
            st.session_state.bilans = []
            st.rerun()
