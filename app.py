import streamlit as st
import pandas as pd
import io
import csv

st.set_page_config(page_title="Éditeur EPW - Intelligent", layout="wide")

st.title("🎯 Éditeur EPW Intelligent (Par Nom de Colonne)")
st.markdown("""
Ce code détecte automatiquement la ligne d'en-tête de votre EPW (celle contenant 'Date', 'Dry Bulb...', etc.).
Il identifie la colonne à modifier par son **nom** plutôt que par son index, éliminant tout risque d'erreur.
""")

col1, col2 = st.columns(2)
with col1:
    uploaded_epw = st.file_uploader("1. Fichier EPW", type=["csv", "txt", "epw"])
with col2:
    uploaded_excel = st.file_uploader("2. Fichier Excel", type=["xlsx", "xls"])

if uploaded_epw and uploaded_excel:
    try:
        # --- 1. Traitement Excel ---
        df_excel = pd.read_excel(uploaded_excel)
        source_col = st.selectbox("Colonne Excel contenant les valeurs", options=list(df_excel.columns))
        list_values = df_excel[source_col].tolist()
        total_excel_rows = len(list_values)
        st.info(f"📊 **{total_excel_rows}** valeurs prêtes dans l'Excel.")

        # --- 2. Lecture et Analyse EPW ---
        epw_raw = uploaded_epw.read()
        epw_text = ""
        detected_enc = ""
        
        for enc in ['utf-8', 'windows-1252', 'iso-8859-1', 'latin-1', 'cp1252']:
            try:
                epw_text = epw_raw.decode(enc)
                detected_enc = enc
                break
            except UnicodeDecodeError:
                continue
        
        if not epw_text:
            st.error("Échec de lecture (Encodage inconnu).")
            st.stop()

        lines = epw_text.splitlines()
        
        # Recherche de la ligne d'en-tête spécifique
        header_line_index = -1
        header_columns = []
        
        # Mots clés typiques de votre en-tête
        keywords = ["Date", "Dry Bulb", "Dew Point", "Relative Humidity", "Atmospheric Pressure"]
        
        for i, line in enumerate(lines):
            # On cherche une ligne qui contient plusieurs de ces mots clés
            match_count = sum(1 for k in keywords if k in line)
            if match_count >= 3: # Si on trouve au moins 3 mots clés, c'est la bonne ligne
                header_line_index = i
                # Parsing de cette ligne pour récupérer les noms de colonnes
                reader = csv.reader(io.StringIO(line))
                header_columns = next(reader)
                break
        
        if header_line_index == -1:
            st.error("Impossible de trouver la ligne d'en-tête descriptive dans le fichier EPW.")
            st.write("Assurez-vous que la ligne contenant 'Date,HH:MM,Dry Bulb...' est bien présente.")
            st.stop()
        
        st.success(f"✅ En-tête détecté à la ligne {header_line_index + 1}.")
        st.write("Colonnes disponibles dans l'EPW :")
        st.json(header_columns) # Affiche la liste proprement

        # --- 3. Sélection de la colonne cible ---
        target_col_name = st.selectbox(
            "Quelle colonne de l'EPW voulez-vous remplacer ?",
            options=header_columns,
            index=header_columns.index("Dry Bulb Temperature {C}") if "Dry Bulb Temperature {C}" in header_columns else 0
        )
        
        target_col_index = header_columns.index(target_col_name)
        st.info(f"La colonne '{target_col_name}' est l'index **{target_col_index}**.")

        # --- 4. Identification des lignes de données ---
        # On considère comme "données" toutes les lignes APRÈS la ligne d'en-tête
        # qui ont un format CSV valide.
        data_lines_indices = []
        for i in range(header_line_index + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            try:
                reader = csv.reader(io.StringIO(line))
                row = next(reader)
                if len(row) >= len(header_columns): # Doit avoir au moins autant de colonnes que l'en-tête
                    data_lines_indices.append(i)
            except:
                continue
        
        total_epw_data_rows = len(data_lines_indices)
        st.info(f"📊 **{total_epw_data_rows}** lignes de données trouvées après l'en-tête.")

        if total_excel_rows != total_epw_data_rows:
            st.warning(f"⚠️ Écart de lignes : Excel ({total_excel_rows}) vs EPW ({total_epw_data_rows}). "
                       f"Le traitement s'arrêtera au plus petit nombre.")

        # --- 5. Traitement ---
        if st.button("🚀 Injecter les données"):
            new_lines = lines[:]
            count_mod = 0
            limit = min(total_excel_rows, total_epw_data_rows)
            
            progress = st.progress(0)
            
            for i in range(limit):
                line_idx = data_lines_indices[i]
                new_val = list_values[i]
                
                if pd.isna(new_val):
                    continue
                
                try:
                    reader = csv.reader(io.StringIO(lines[line_idx]))
                    row = next(reader)
                    
                    # Injection
                    if target_col_index < len(row):
                        row[target_col_index] = str(new_val)
                        
                        out = io.StringIO()
                        w = csv.writer(out)
                        w.writerow(row)
                        new_lines[line_idx] = out.getvalue().strip()
                        count_mod += 1
                except:
                    continue
                
                if i % 500 == 0:
                    progress.progress(i / limit)
            
            progress.progress(1.0)
            st.success(f"✅ Terminé ! **{count_mod}** valeurs injectées dans la colonne '{target_col_name}'.")
            
            final_content = '\n'.join(new_lines)
            
            st.download_button(
                label="📥 Télécharger le fichier EPW modifié",
                data=final_content.encode('utf-8'),
                file_name=f"epw_modifie_{target_col_name.replace(' ', '_')}.epw",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Erreur : {e}")
        st.code(str(e))
else:
    st.info("En attente des fichiers...")
