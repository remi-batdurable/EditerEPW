import streamlit as st
import pandas as pd
import io
import csv
import os

st.set_page_config(page_title="Éditeur EPW - Multi-Colonnes", layout="wide")

st.title("🎛️ Éditeur EPW Multi-Colonnes")
st.markdown("""
Injectez simultanément plusieurs variables (Température, Humidité, Vent, etc.) depuis votre Excel vers un EPW au format CSV.  
Le code détecte l'en-tête de l'EPW et vous laisse mapper les colonnes Excel vers les colonnes EPW cibles. Si les colonnes Excel sont nommées comme les colonnes EPW cibles, le mappage est automatique.  
Le fichier Excel doit contenir en première ligne l'entête et les 8760 valeurs de chaque donnée à partir de la ligne 2.  
La première colonne du fichier Excel peut etre une colonne de date (Entête = Date). Elle est exclue du mapping.  
Le fichier de sortie est un fichier EPW au format csv à télécharger avec les données choisies remplacées.
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
        all_excel_cols = [col for col in df_excel.columns if col != "Date"]  # Exclure la colonne Date

        st.success(f"Excel chargé : {len(df_excel)} lignes de données.")

        # Sélection MULTIPLE des colonnes sources (toutes sélectionnées par défaut sauf Date)
        selected_excel_cols = st.multiselect(
            "Sélectionnez les colonnes de l'Excel à injecter (toutes sont sélectionnées par défaut sauf 'Date')",
            options=all_excel_cols,
            default=all_excel_cols  # Toutes les colonnes sauf Date sont sélectionnées par défaut
        )

        if not selected_excel_cols:
            st.warning("Veuillez sélectionner au moins une colonne dans l'Excel.")
            st.stop()

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

        # Recherche de la ligne d'en-tête
        target_header = "Date,HH:MM,Datasource,Dry Bulb Temperature {C},Dew Point Temperature {C},Relative Humidity {%},Atmospheric Pressure {Pa},Extraterrestrial Horizontal Radiation {Wh/m2},Extraterrestrial Direct Normal Radiation {Wh/m2},Horizontal Infrared Radiation Intensity from Sky {Wh/m2},Global Horizontal Radiation {Wh/m2},Direct Normal Radiation {Wh/m2},Diffuse Horizontal Radiation {Wh/m2},Global Horizontal Illuminance {lux},Direct Normal Illuminance {lux},Diffuse Horizontal Illuminance {lux},Zenith Luminance {Cd/m2},Wind Direction {deg},Wind Speed {m/s},Total Sky Cover {.1},Opaque Sky Cover {.1},Visibility {km},Ceiling Height {m},Present Weather Observation,Present Weather Codes,Precipitable Water {mm},Aerosol Optical Depth {.001},Snow Depth {cm},Days Since Last Snow,Albedo {.01},Liquid Precipitation Depth {mm},Liquid Precipitation Quantity {hr}"

        header_line_index = -1
        for i, line in enumerate(lines):
            if line.strip() == target_header:
                header_line_index = i
                reader = csv.reader(io.StringIO(line))
                header_columns = next(reader)
                break

        if header_line_index == -1:
            st.error("Impossible de trouver la ligne d'en-tête descriptive.")
            st.stop()

        st.success(f"✅ En-tête EPW détecté ({len(header_columns)} colonnes).")

        # --- 3. Configuration du Mapping ---
        st.subheader("3. Correspondance des colonnes (Mapping)")
        st.write("Associez chaque colonne Excel sélectionnée à sa colonne cible dans l'EPW.")

        mapping_config = {}
        for i, col_excel in enumerate(selected_excel_cols):
            with st.container():
                c1, c2, c3 = st.columns([1, 2, 0.5])
                with c1:
                    st.write(f"**Source (Excel):** `{col_excel}`")
                with c2:
                    # Recherche d'une correspondance exacte dans header_columns
                    default_idx = None
                    for idx, h_col in enumerate(header_columns):
                        if col_excel.strip() == h_col.strip():
                            default_idx = idx
                            break

                    target = st.selectbox(
                        f"➡️ Remplacer dans l'EPW :",
                        options=header_columns,
                        index=default_idx if default_idx is not None else 0,
                        key=f"map_{i}"
                    )
                    mapping_config[col_excel] = target
                with c3:
                    # Affichage discret du numéro de colonne EPW
                    target_idx = header_columns.index(target) if target in header_columns else -1
                    st.text(f"#{target_idx}")

        st.divider()

        # --- 4. Identification des lignes de données ---
        data_lines_indices = []
        for i in range(header_line_index + 1, len(lines)):
            line = lines[i]
            if not line.strip():
                continue
            try:
                reader = csv.reader(io.StringIO(line))
                row = next(reader)
                if len(row) >= len(header_columns):
                    data_lines_indices.append(i)
            except:
                continue

        total_epw_rows = len(data_lines_indices)
        total_excel_rows = len(df_excel)

        st.info(f"📊 Données : Excel ({total_excel_rows} lignes) vs EPW ({total_epw_rows} lignes de données).")

        if total_excel_rows != total_epw_rows:
            st.warning(f"⚠️ Les nombres de lignes diffèrent. Le traitement s'arrêtera à {min(total_excel_rows, total_epw_rows)} lignes.")

        if st.button("🚀 Injecter toutes les colonnes sélectionnées"):
            limit = min(total_excel_rows, total_epw_rows)
            new_lines = lines[:]
            count_mod = 0
            progress = st.progress(0)

            mapping_indices = {}
            for col_excel, col_epw_name in mapping_config.items():
                idx = header_columns.index(col_epw_name)
                mapping_indices[col_excel] = idx

            for i in range(limit):
                line_idx = data_lines_indices[i]
                try:
                    reader = csv.reader(io.StringIO(lines[line_idx]))
                    row = next(reader)

                    modified = False
                    for col_excel, target_idx in mapping_indices.items():
                        val = df_excel.at[i, col_excel]
                        if not pd.isna(val):
                            if target_idx < len(row):
                                row[target_idx] = str(val)
                                modified = True

                    if modified:
                        out = io.StringIO()
                        w = csv.writer(out)
                        w.writerow(row)
                        new_lines[line_idx] = out.getvalue().strip()
                        count_mod += 1

                except Exception:
                    continue

                if i % 500 == 0:
                    progress.progress(i / limit)

            progress.progress(1.0)
            st.success(f"✅ Terminé ! **{count_mod}** lignes mises à jour avec {len(mapping_config)} colonnes.")

            final_content = '\n'.join(new_lines)

            # Génération du nom de fichier de sortie
            epw_filename = uploaded_epw.name
            name_without_ext, ext = os.path.splitext(epw_filename)
            output_filename = f"{name_without_ext} modifié{ext}"

            st.download_button(
                label="📥 Télécharger le fichier EPW modifié",
                data=final_content.encode('utf-8'),
                file_name=output_filename,
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Erreur critique : {e}")
        st.code(str(e))
else:
    st.info("Veuillez charger les fichiers EPW et Excel.")
