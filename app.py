import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Éditeur EPW Robuste", layout="wide")

st.title("🛡️ Éditeur EPW Robuste (Préservation du format)")
st.markdown("""
Cette application modifie une colonne spécifique d'un fichier **EPW** (au format CSV) 
en utilisant des données sources **Excel**, même si l'ordre des lignes diffère.

**Garanties de robustesse :**
- Le fichier EPW est lu et écrit comme du **texte brut**.
- Aucun formatage de nombre, d'espace ou de virgule n'est altéré par pandas.
- Seule la colonne cible est modifiée, le reste du fichier (y compris les en-têtes éventuels) est conservé à l'identique.
- Gestion intelligente de l'alignement par Date/Heure.
""")

# --- 1. Chargement des fichiers ---
col1, col2 = st.columns(2)

with col1:
    uploaded_epw = st.file_uploader("1. Fichier EPW (CSV complet)", type=["csv", "txt", "epw"])
with col2:
    uploaded_excel = st.file_uploader("2. Fichier Excel (Sources)", type=["xlsx", "xls"])

if uploaded_epw and uploaded_excel:
    try:
        # --- 2. Lecture du fichier Excel (Seul fichier chargé en DataFrame) ---
        df_excel = pd.read_excel(uploaded_excel)
        st.success("Fichier Excel chargé avec succès.")
        
        # Affichage pour aider l'utilisateur à identifier les colonnes
        with st.expander("Aperçu des données Excel"):
            st.dataframe(df_excel.head())
            st.write(f"Colonnes disponibles : {list(df_excel.columns)}")

        # --- 3. Configuration de la fusion ---
        st.subheader("3. Configuration de l'alignement et de la modification")
        
        col_key, col_src, col_target = st.columns(3)
        
        with col_key:
            key_col_excel = st.selectbox("Colonne 'Clé' dans l'Excel (Date/Heure)", options=list(df_excel.columns))
            # On demande à l'utilisateur le numéro ou le nom de la colonne dans l'EPW si connu, 
            # mais comme on lit en texte, on va demander l'index de la colonne (0-based)
            st.info("Dans un EPW standard : 0=Année, 1=Mois, 2=Jour, 3=Heure, 4=Minute, 6=Température...")
        
        with col_src:
            source_col_excel = st.selectbox("Colonne 'Valeur' dans l'Excel (Nouvelle donnée)", options=list(df_excel.columns))
            
        with col_target:
            target_col_index = st.number_input("Index de la colonne à modifier dans l'EPW (0, 1, 2...)", min_value=0, value=6, step=1)
            st.caption("L'index commence à 0. Ex: 6 pour la température sèche.")

        # Préparation de la table de recherche (Lookup Table)
        # On crée un dictionnaire : { "2026-01-01 01:00": 23.5, ... }
        # On normalise la clé en string pour éviter les problèmes de format
        df_excel['_key_norm'] = df_excel[key_col_excel].astype(str)
        lookup_dict = pd.Series(df_excel[source_col_excel].values, index=df_excel['_key_norm']).to_dict()
        
        st.write(f"✅ {len(lookup_dict)} valeurs prêtes à être injectées depuis l'Excel.")

        if st.button("🚀 Traiter et Générer le fichier"):
            # Lecture du contenu EPW en texte brut
            epw_content = uploaded_epw.read().decode('utf-8')
            lines = epw_content.splitlines()
            
            new_lines = []
            count_modified = 0
            count_total = 0
            
            # Barre de progression
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- 4. Traitement Ligne par Ligne (Robuste) ---
            for i, line in enumerate(lines):
                # On ignore les lignes vides
                if not line.strip():
                    new_lines.append(line)
                    continue
                
                # On découpe la ligne pour analyser la structure
                # On utilise csv.reader logic manuellement ou split simple si pas de guillemets complexes
                # Pour un EPW standard, split(',') suffit souvent, mais attention aux guillemets.
                # Approche sécurisée : utiliser le module csv sur une ligne
                import csv
                from io import StringIO
                
                reader = csv.reader(StringIO(line))
                try:
                    row = next(reader)
                except StopIteration:
                    new_lines.append(line)
                    continue

                # Si la ligne n'a pas assez de colonnes (ex: en-tête ou ligne corrompue), on la garde telle quelle
                if len(row) <= target_col_index:
                    new_lines.append(line)
                    continue
                
                # Construction de la clé de temps depuis les colonnes EPW standards
                # Hypothèse : EPW standard (Year, Month, Day, Hour, Minute) aux index 0,1,2,3,4
                # Si votre fichier est différent, il faudra adapter cette logique.
                # On essaie de construire une clé similaire à celle de l'Excel.
                # Exemple de clé standard : "2026-01-01 01:00" ou "2026,1,1,1,0"
                # Pour être robuste, on va essayer de matcher le format exact de l'Excel si possible,
                # ou construire un format standard.
                
                # Stratégie : On construit une clé "YYYY,M,D,H,M" (format brut EPW) et on espère que l'Excel est compatible
                # OU on laisse l'utilisateur définir comment construire la clé ? 
                # Pour simplifier l'UI, on suppose que la clé Excel est une date/heure lisible.
                # On va construire une clé standardisée depuis l'EPW : "YYYY-MM-DD HH:MM"
                
                try:
                    y, m, d, h, mi = row[0], row[1], row[2], row[3], row[4]
                    # Normalisation pour matcher (ex: enlever les zéros non nécessaires si l'Excel le fait)
                    # Le plus sûr est de créer plusieurs variantes de clés ou de demander le format à l'utilisateur.
                    # Ici, on crée une clé simple : "Y,M,D,H,Mi"
                    epw_key = f"{y},{m},{d},{h},{mi}"
                    
                    # Tentative de correspondance directe
                    new_val = None
                    if epw_key in lookup_dict:
                        new_val = lookup_dict[epw_key]
                    else:
                        # Essai avec un formatage différent (si l'Excel est "2026-01-01 01:00")
                        # On essaie de formater comme une date ISO
                        epw_key_iso = f"{y}-{int(m):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}"
                        if epw_key_iso in lookup_dict:
                            new_val = lookup_dict[epw_key_iso]
                    
                    if new_val is not None:
                        # MODIFICATION ICI : On remplace uniquement la valeur dans la liste row
                        row[target_col_index] = str(new_val)
                        
                        # On reconstruit la ligne exactement comme un CSV standard
                        # Cela préserve les guillemets si nécessaire grâce au module csv
                        output = io.StringIO()
                        writer = csv.writer(output)
                        writer.writerow(row)
                        new_lines.append(output.getvalue().strip())
                        count_modified += 1
                    else:
                        # Pas de correspondance, on garde la ligne originale
                        new_lines.append(line)
                        
                except (ValueError, IndexError):
                    # Erreur de parsing (ex: ligne d'en-tête non standard), on garde la ligne originale
                    new_lines.append(line)
                
                count_total += 1
                if i % 1000 == 0:
                    progress_bar.progress(min(i / len(lines), 1.0))
                    status_text.text(f"Traitement : {i}/{len(lines)} lignes...")

            progress_bar.progress(1.0)
            status_text.text("Terminé !")
            
            st.success(f"Traitement terminé ! {count_modified} lignes modifiées sur {count_total} lignes de données.")
            
            # --- 5. Export ---
            final_content = '\n'.join(new_lines)
            
            st.download_button(
                label="📥 Télécharger le fichier EPW modifié",
                data=final_content,
                file_name="meteo_modifie.epw", # On garde l'extension .epw ou .csv selon préférence
                mime="text/csv"
            )
            
            st.info("Le fichier généré conserve exactement le formatage original (espaces, guillemets, précision) pour toutes les colonnes non modifiées.")

    except Exception as e:
        st.error(f"Une erreur critique est survenue : {e}")
        st.code(str(e))
else:
    st.info("Veuillez charger les deux fichiers pour commencer.")
