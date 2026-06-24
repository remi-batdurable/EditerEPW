import streamlit as st
import openpyxl
from functions import lire_fichier_excel, exporter_vers_epw, formater_dates, exporter_en_csv
import pandas as pd
import os
from datetime import datetime

# Titre de l'application
st.title("🌍 Export TRACC vers EPW")
st.markdown("""
Cette application permet d'exporter des données météorologiques depuis un fichier **TRACC** (Excel)
vers un fichier **EPW** (format EnergyPlus), puis de générer un fichier CSV formaté.
""")

# Étape 1 : Charger le fichier source (TRACC)
st.header("1. Charger le fichier source (TRACC)")
fichier_source = st.file_uploader(
    "Importer le fichier TRACC (Excel)",
    type=["xlsx", "xls"],
    key="fichier_source"
)

if fichier_source:
    try:
        df_source = lire_fichier_excel(fichier_source)
        st.success("Fichier TRACC chargé avec succès !")
        st.write(f"**Nombre de lignes :** {len(df_source)}")
        st.write(f"**Colonnes :** {list(df_source.columns)}")
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier TRACC : {e}")

    # Étape 2 : Charger le fichier destination (EPW)
    st.header("2. Charger le fichier destination (EPW)")
    fichier_dest = st.file_uploader(
        "Importer le fichier EPW (Excel)",
        type=["xlsx", "xls"],
        key="fichier_dest"
    )

    if fichier_dest:
        try:
            df_dest = lire_fichier_excel(fichier_dest)
            st.success("Fichier EPW chargé avec succès !")

            # Bouton pour lancer l'export
            if st.button("Exporter les données"):
                with st.spinner("Traitement en cours..."):
                    try:
                        # Adapter les données
                        df_dest = exporter_vers_epw(df_source, df_dest)

                        # Formater les dates
                        df_dest = formater_dates(df_dest)

                        # Générer un nom de fichier CSV
                        nom_csv = os.path.splitext(fichier_dest.name)[0] + "_export.csv"

                        # Exporter en CSV
                        chemin_csv = exporter_en_csv(df_dest, nom_csv)

                        # Proposer le téléchargement
                        st.success("Exportation réussie !")
                        st.download_button(
                            label="Télécharger le fichier CSV",
                            data=df_dest.to_csv(index=False, sep=',', decimal='.').encode('utf-8'),
                            file_name=nom_csv,
                            mime='text/csv',
                        )
                    except Exception as e:
                        st.error(f"Erreur lors de l'export : {e}")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier EPW : {e}")
else:
    st.info("Veuillez charger le fichier TRACC pour commencer.")
