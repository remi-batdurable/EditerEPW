import streamlit as st
import pandas as pd
import io
import csv

st.set_page_config(page_title="Éditeur EPW Robuste (Multi-Encodage)", layout="wide")

st.title("🛡️ Éditeur EPW Robuste (Multi-Encodage)")
st.markdown("""
Cette application modifie une colonne spécifique d'un fichier **EPW** en utilisant des données **Excel**.
**Nouveauté :** Gestion automatique des problèmes d'encodage (UTF-8, Windows-1252, Latin-1).
""")

# --- 1. Chargement des fichiers ---
col1, col2 = st.columns(2)

with col1:
    uploaded_epw = st.file_uploader("1. Fichier EPW (CSV complet)", type=["csv", "txt", "epw"])
with col2:
    uploaded_excel = st.file_uploader("2. Fichier Excel (Sources)", type=["xlsx", "xls"])

if uploaded_epw and uploaded_excel:
    try:
        # --- 2. Lecture du fichier Excel ---
        df_excel = pd.read_excel(uploaded_excel)
        st.success("Fichier Excel chargé avec succès.")
        
        with st.expander("Aperçu des données Excel"):
            st.dataframe(df_excel.head())

        # --- 3. Configuration ---
        st.subheader("3. Configuration de l'alignement")
        
        col_key, col_src, col_target = st.columns(3)
        
        with col_key:
            key_col_excel = st.selectbox("Colonne 'Clé' dans l'Excel (Date/Heure)", options=list(df_excel.columns))
            st.info("Assurez-vous que cette colonne contient des dates/heures compatibles avec l'EPW.")
        
        with col_src:
            source_col_excel = st.selectbox("Colonne 'Valeur' dans l'Excel", options=list(df_excel.columns))
            
        with col_target:
            target_col_index = st.number_input("Index de la colonne à modifier dans l'EPW (0-based)", min_value=0, value=6, step=1)
            st.caption("0=Année, 1=Mois, ..., 6=Température (généralement).")

        # Préparation du dictionnaire de recherche
        # On s'assure que la clé est bien une chaîne de caractères
        df_excel['_key_norm'] = df_excel[key_col_excel].astype(str)
        lookup_dict = pd.Series(df_excel[source_col_excel].values, index=df_excel['_key_norm']).to_dict()
        st.write(f"✅ {len(lookup_dict)} valeurs prêtes depuis l'Excel.")

        if st.button("🚀 Traiter et Générer le fichier"):
            # --- 4. Lecture Robuste du fichier EPW (Gestion Encodage) ---
            epw_raw_data = uploaded_epw.read()
            epw_content = ""
            detected_encoding = ""
            
            encodings_to_try = ['utf-8', 'windows-1252', 'iso-8859-1', 'latin-1', 'cp1252']
            
            for enc in encodings_to_try:
                try:
                    epw_content = epw_raw_data.decode(enc)
                    detected_encoding = enc
                    st.success(f"Fichier EPW décodé avec succès en : **{enc}**")
                    break
                except UnicodeDecodeError:
                    continue
            
            if not epw_content:
                st.error("Impossible de lire le fichier EPW. L'encodage n'est reconnu ni en UTF-8, ni en Windows-1252/Latin-1.")
                st.stop()

            lines = epw_content.splitlines()
            new_lines = []
            count_modified = 0
            count_total = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- 5. Traitement
