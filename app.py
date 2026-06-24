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
            
            # --- 5. Traitement Ligne par Ligne ---
            total_lines = len(lines)
            
            for i, line in enumerate(lines):
                if not line.strip():
                    new_lines.append(line)
                    continue
                
                # Parsing CSV sécurisé
                try:
                    reader = csv.reader(io.StringIO(line))
                    row = next(reader)
                except Exception:
                    new_lines.append(line) # Ligne non CSV, on garde
                    continue

                # Vérification longueur
                if len(row) <= target_col_index:
                    new_lines.append(line)
                    continue
                
                # Construction de la clé depuis l'EPW
                try:
                    # Hypothèse structure EPW standard: Y,M,D,H,Min
                    y, m, d, h, mi = row[0], row[1], row[2], row[3], row[4]
                    
                    # Clé 1: Format brut "Y,M,D,H,Mi"
                    epw_key_raw = f"{y},{m},{d},{h},{mi}"
                    
                    # Clé 2: Format ISO "YYYY-MM-DD HH:MM"
                    try:
                        y_i, m_i, d_i, h_i, mi_i = int(y), int(m), int(d), int(h), int(mi)
                        epw_key_iso = f"{y_i}-{m_i:02d}-{d_i:02d} {h_i:02d}:{mi_i:02d}"
                    except ValueError:
                        epw_key_iso = ""

                    new_val = None
                    
                    # Tentative de matching
                    if epw_key_raw in lookup_dict:
                        new_val = lookup_dict[epw_key_raw]
                    elif epw_key_iso in lookup_dict:
                        new_val = lookup_dict[epw_key_iso]

                    if new_val is not None:
                        # Remplacement de la valeur
                        row[target_col_index] = str(new_val)
                        
                        # Réécriture CSV propre
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(row)
                        new_lines.append(output.getvalue().strip())
                        count_modified += 1
                    else:
                        new_lines.append(line)
                        
                except Exception:
                    # Erreur inattendue sur une ligne, on la conserve telle quelle
                    new_lines.append(line)
                
                count_total += 1
                
                # Mise à jour de la barre de progression (toutes les 500 lignes pour performance)
                if i % 500 == 0:
                    progress_val = min((i / total_lines), 1.0)
                    progress_bar.progress(progress_val)
                    status_text.text(f"Traitement : {i}/{total_lines} lignes...")

            progress_bar.progress(1.0)
            status_text.text("Terminé !")
            
            st.success(f"Traitement terminé ! **{count_modified}** lignes modifiées sur {count_total} lignes totales.")
            
            if count_modified == 0:
                st.warning("Aucune modification n'a été effectuée. Vérifiez que les formats de dates/heures dans la colonne 'Clé' de l'Excel correspondent bien à ceux de l'EPW.")

            # --- 6. Export ---
            final_content = '\n'.join(new_lines)
            
            st.download_button(
                label="📥 Télécharger le fichier EPW modifié",
                data=final_content.encode('utf-8'),
                file_name="meteo_modifie.epw",
                mime="text/csv"
            )
            st.info("Le fichier téléchargé est encodé en UTF-8.")

    except Exception as e:
        st.error(f"Une erreur critique est survenue : {e}")
        st.code(str(e))
else:
    st.info("Veuillez charger les deux fichiers pour commencer.")
