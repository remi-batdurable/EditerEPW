import streamlit as st
from functions import lire_fichier, exporter_vers_epw, exporter_en_csv
import pandas as pd
import os

# Titre de l'application
st.title("🌍 Export TRACC vers EPW")
st.markdown("""
Cette application permet d'exporter des données météorologiques depuis un fichier **TRACC** (Excel)
vers un fichier **EPW** (CSV), puis de générer un fichier CSV formaté.
""")

# Étape 1 : Charger le fichier source (TRACC)
st.header("1. Charger le fichier source (TRACC)")
fichier_source = st.file_uploader(
    "Importer le fichier TRACC (Excel : .xlsx, .xls)",
    type=["xlsx", "xls"],
    key="fichier_source"
)

if fichier_source:
    try:
        df_source = lire_fichier(fichier_source)
        st.success("Fichier TRACC chargé avec succès !")
        st.write(f"**Nombre de lignes :** {len(df_source)}")
        st.write(f"**Colonnes :** {list(df_source.columns)}")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier TRACC : {e}")

    # Étape 2 : Charger le fichier destination (EPW)
    st.header("2. Charger le fichier destination (EPW)")
    fichier_dest = st.file_uploader(
        "Importer le fichier EPW (CSV : .csv)",
        type=["csv"],
        key="fichier_dest"
    )

    if fichier_dest:
        try:
            df_dest = lire_fichier(fichier_dest)
            st.success("Fichier EPW chargé avec succès !")
            
            # --- AJOUTEZ CECI POUR DEBUGGER ---
            st.warning(f"🔍 Diagnostic : Le fichier a {df_dest.shape[0]} lignes et {df_dest.shape[1]} colonnes détectées par Python.")
            st.write("Aperçu des 2 premières lignes brutes :")
            st.write(df_dest.head(2))
            st.write("Nom des colonnes détectées :")
            st.write(list(df_dest.columns))
            # ----------------------------------

            # Bouton pour lancer l'export
            if st.button("Exporter les données"):
                with st.spinner("Traitement en cours..."):
                    try:
                        # Adapter les données
                        df_dest = exporter_vers_epw(df_source, df_dest)

                        # Générer un nom de fichier CSV
                        nom_csv = os.path.splitext(fichier_dest.name)[0] + "_export.csv"

                        # Exporter en CSV avec des points comme décimales
                        csv_data = df_dest.to_csv(index=False, sep=',', decimal='.')

                        # Proposer le téléchargement
                        st.success("Exportation réussie !")
                        st.download_button(
                            label="Télécharger le fichier CSV",
                            data=csv_data.encode('utf-8'),
                            file_name=nom_csv,
                            mime='text/csv',
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de l'export : {e}")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier EPW : {e}")
else:
    st.info("Veuillez charger le fichier TRACC pour commencer.")
