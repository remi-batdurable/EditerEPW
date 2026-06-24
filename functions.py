import pandas as pd
import numpy as np

def lire_fichier(fichier):
    """Lire un fichier (Excel ou CSV) et retourner un DataFrame."""
    if fichier.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(fichier, engine='openpyxl')
    elif fichier.name.endswith('.csv'):
        # Essayer plusieurs encodages pour éviter les erreurs
        encodages = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
        for encodage in encodages:
            try:
                return pd.read_csv(fichier, sep=',', decimal='.', encoding=encodage)
            except UnicodeDecodeError:
                continue
        raise ValueError("Impossible de lire le fichier CSV. Encodage non supporté.")
    else:
        raise ValueError("Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv.")

def exporter_vers_epw(df_source, df_dest, nd_donnees=8760):
    """
    Adapter les données du fichier TRACC vers le format EPW.
    Ajoute automatiquement les colonnes manquantes si nécessaire.
    """
    # Configuration des colonnes source (TRACC)
    config_source = {
        'TempAir': 6, 'HR': 8, 'RR': 17, 'VentForce': 16, 'VentDir': 15,
        'TempRosee': 7, 'SoleilHt': 11, 'SoleilAzimut': 10, 'RayGlobalH': 12,
        'RayDirectN': 14, 'RayDiffusH': 13, 'Nebulosite': 18, 'PressionATM': 9,
    }

    # Configuration des colonnes destination (EPW)
    config_dest = {
        'TempAir': 3, 'TempRosee': 4, 'HR': 5, 'PressionATM': 6,
        'RayExtraterrestreH': 7, 'RayExtraterrestreDirectN': 8, 'RayIRciel': 9,
        'RayGlobalH': 10, 'RayDirectN': 11, 'RayDiffusH': 12,
        'IlluminanceGlobalH': 13, 'IlluminanceDirectN': 14, 'IlluminanceDiffusH': 15,
        'LuminanceZenith': 16, 'VentDir': 17, 'VentForce': 18,
        'CouvertureCiel': 19, 'CouvertureCielCouvert': 20, 'Visibilite': 21,
        'HtPlafond': 22, 'ObsMeteo': 23, 'ObsMeteoCode': 24, 'Pluie': 25,
        'AerosolOptiqueEp': 26, 'NeigeEp': 27, 'NeigeJourDepuis': 28,
        'Albedo': 29, 'RR': 30, 'PluieDebit': 31,
    }

    # --- CORRECTION : Ajouter les colonnes manquantes au df_dest ---
    nb_colonnes_requises = max(config_dest.values()) + 1
    nb_colonnes_actuelles = df_dest.shape[1]
    
    if nb_colonnes_actuelles < nb_colonnes_requises:
        colonnes_manquantes = nb_colonnes_requises - nb_colonnes_actuelles
        for i in range(colonnes_manquantes):
            # On ajoute des colonnes avec des valeurs par défaut (ex: 0 ou 9999 selon le standard EPW)
            # Ici on met 0 par défaut, à ajuster selon vos besoins
            df_dest[f'col_manquante_{i}'] = 0
        
        # Optionnel : Renommer les colonnes pour qu'elles correspondent aux indices attendus
        # Ou simplement s'assurer que le DataFrame a assez de colonnes pour l'indexation .iloc
        # La méthode la plus sûre pour .iloc est de réindexer ou de s'assurer que la largeur est bonne.
        # Ici, on va simplement s'assurer que le DataFrame a la bonne largeur en ajoutant des colonnes vides.
        # Note: .iloc fonctionne par position, donc ajouter des colonnes à la fin suffit.
        pass

    # Recalculer la largeur actuelle après ajout
    if df_dest.shape[1] < nb_colonnes_requises:
         # Si l'ajout ci-dessus n'a pas suffi (cas rare), on force l'extension
         # Création d'un nouveau DataFrame avec le bon nombre de colonnes
         new_cols = nb_colonnes_requises - df_dest.shape[1]
         for i in range(new_cols):
             df_dest.iloc[:, -1:] # Juste pour vérifier, on va plutôt utiliser concat si besoin
         
         # Méthode simple : ajouter des colonnes jusqu'à atteindre le compte
         while df_dest.shape[1] < nb_colonnes_requises:
             df_dest[f'extra_{df_dest.shape[1]}'] = 0

    # ---------------------------------------------------------------

    # Lignes de départ et fin
    ls_depart = 1  
    ld_depart = 19 

    # Calculer nd_donnees dynamiquement
    nd_donnees = min(len(df_source) - ls_depart, len(df_dest) - ld_depart)
    if nd_donnees <= 0:
        raise ValueError("Aucune donnée à copier. Vérifiez les lignes de départ.")

    ls_fin = ls_depart + nd_donnees - 1
    ld_fin = ld_depart + nd_donnees - 1

    # Vérifier que les colonnes SOURCE existent (le destination est maintenant garanti)
    max_col_source = max(config_source.values())
    if df_source.shape[1] <= max_col_source:
        raise ValueError(f"Le fichier source n'a pas assez de colonnes. Attendu : {max_col_source + 1}, trouvé : {df_source.shape[1]}")

    # Copier les données
    for key, col_src in config_source.items():
        if key in config_dest:
            col_dest = config_dest[key]
            # Vérification de sécurité pour col_dest
            if col_dest >= df_dest.shape[1]:
                continue # Ou lever une erreur si critique
                
            source_data = df_source.iloc[ls_depart:ls_fin+1, col_src].values
            if len(source_data) != nd_donnees:
                raise ValueError(f"Taille incorrecte pour {key}. Attendu : {nd_donnees}, trouvé : {len(source_data)}")
            df_dest.iloc[ld_depart:ld_fin+1, col_dest] = source_data

    # Traitements spécifiques
    # Pression ATM : multiplier par 100
    if 'PressionATM' in config_source and 'PressionATM' in config_dest:
        col_src = config_source['PressionATM']
        col_dest = config_dest['PressionATM']
        if col_dest < df_dest.shape[1]:
            df_dest.iloc[ld_depart:ld_fin+1, col_dest] = df_source.iloc[ls_depart:ls_fin+1, col_src].values * 100

    # Nebulosité -> CouvertureCiel et CouvertureCielCouvert
    if 'Nebulosite' in config_source:
        col_src = config_source['Nebulosite']
        for key in ['CouvertureCiel', 'CouvertureCielCouvert']:
            if key in config_dest:
                col_dest = config_dest[key]
                if col_dest < df_dest.shape[1]:
                    df_dest.iloc[ld_depart:ld_fin+1, col_dest] = df_source.iloc[ls_depart:ls_fin+1, col_src].values / 10

    # Remplir les colonnes avec des valeurs par défaut
    valeurs_par_defaut = {
        'RayExtraterrestreH': 9999, 'RayExtraterrestreDirectN': 9999, 'RayIRciel': 9999,
        'IlluminanceGlobalH': 999999, 'IlluminanceDirectN': 999999, 'IlluminanceDiffusH': 999999,
        'LuminanceZenith': 9999, 'Visibilite': 9999, 'HtPlafond': 99999,
        'ObsMeteo': 0, 'ObsMeteoCode': 999999999, 'Pluie': 999,
        'AerosolOptiqueEp': 999, 'NeigeEp': 999, 'NeigeJourDepuis': 99,
        'Albedo': 0.2, 'PluieDebit': 0,
    }

    for key, valeur in valeurs_par_defaut.items():
        if key in config_dest:
            col_dest = config_dest[key]
            if col_dest < df_dest.shape[1]:
                df_dest.iloc[ld_depart:ld_fin+1, col_dest] = valeur

    return df_dest
def exporter_en_csv(df, nom_fichier):
    """Exporter un DataFrame en CSV avec des séparateurs US et des points comme décimales."""
    return df.to_csv(nom_fichier, index=False, sep=',', decimal='.')
