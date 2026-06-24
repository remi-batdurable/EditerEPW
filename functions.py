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
    df_source : DataFrame du fichier source (TRACC).
    df_dest : DataFrame du fichier destination (EPW).
    nd_donnees : Nombre de lignes de données (8760 par défaut).
    """
    # Configuration des colonnes source (TRACC) - MIS À JOUR
    config_source = {
        'TempAir': 6,          
        'HR': 8,             
        'RR': 17,             
        'VentForce': 16,      
        'VentDir': 15,        
        'TempRosee': 7,       
        'SoleilHt': 11,       
        'SoleilAzimut': 10,   
        'RayGlobalH': 12,     
        'RayDirectN': 14,     
        'RayDiffusH': 13,     
        'Nebulosite': 18,     
        'PressionATM': 9,    
    }

    # Configuration des colonnes destination (EPW)
    config_dest = {
        'TempAir': 3,          # Colonne 4 en EPW (index 3)
        'TempRosee': 4,        # Colonne 5 en EPW (index 4)
        'HR': 5,               # Colonne 6 en EPW (index 5)
        'PressionATM': 6,      # Colonne 7 en EPW (index 6)
        'RayExtraterrestreH': 7,
        'RayExtraterrestreDirectN': 8,
        'RayIRciel': 9,
        'RayGlobalH': 10,
        'RayDirectN': 11,
        'RayDiffusH': 12,
        'IlluminanceGlobalH': 13,
        'IlluminanceDirectN': 14,
        'IlluminanceDiffusH': 15,
        'LuminanceZenith': 16,
        'VentDir': 17,
        'VentForce': 18,
        'CouvertureCiel': 19,
        'CouvertureCielCouvert': 20,
        'Visibilite': 21,
        'HtPlafond': 22,
        'ObsMeteo': 23,
        'ObsMeteoCode': 24,
        'Pluie': 25,
        'AerosolOptiqueEp': 26,
        'NeigeEp': 27,
        'NeigeJourDepuis': 28,
        'Albedo': 29,
        'RR': 30,
        'PluieDebit': 31,
    }

    # Lignes de départ et fin
    ls_depart = 1  
    ld_depart = 19  # Ligne 20 en EPW (index 19 en Python)

    # Calculer nd_donnees dynamiquement
    nd_donnees = min(len(df_source) - ls_depart, len(df_dest) - ld_depart)
    if nd_donnees <= 0:
        raise ValueError("Aucune donnée à copier. Vérifiez les lignes de départ.")

    ls_fin = ls_depart + nd_donnees - 1
    ld_fin = ld_depart + nd_donnees - 1

    # Vérifier que les colonnes existent
    max_col_source = max(config_source.values())
    max_col_dest = max(config_dest.values())
    if df_source.shape[1] <= max_col_source:
        raise ValueError(f"Le fichier source n'a pas assez de colonnes. Attendu : {max_col_source + 1}, trouvé : {df_source.shape[1]}")
    if df_dest.shape[1] <= max_col_dest:
        raise ValueError(f"Le fichier destination n'a pas assez de colonnes. Attendu : {max_col_dest + 1}, trouvé : {df_dest.shape[1]}")

    # Copier les données
    for key, col_src in config_source.items():
        if key in config_dest:
            col_dest = config_dest[key]
            source_data = df_source.iloc[ls_depart:ls_fin+1, col_src].values
            if len(source_data) != nd_donnees:
                raise ValueError(f"Taille incorrecte pour {key}. Attendu : {nd_donnees}, trouvé : {len(source_data)}")
            df_dest.iloc[ld_depart:ld_fin+1, col_dest] = source_data

    # Traitements spécifiques
    # Pression ATM : multiplier par 100
    col_src = config_source['PressionATM']
    col_dest = config_dest['PressionATM']
    df_dest.iloc[ld_depart:ld_fin+1, col_dest] = df_source.iloc[ls_depart:ls_fin+1, col_src].values * 100

    # Nebulosité -> CouvertureCiel et CouvertureCielCouvert : diviser par 10
    col_src = config_source['Nebulosite']
    for key in ['CouvertureCiel', 'CouvertureCielCouvert']:
        col_dest = config_dest[key]
        df_dest.iloc[ld_depart:ld_fin+1, col_dest] = df_source.iloc[ls_depart:ls_fin+1, col_src].values / 10

    # Remplir les colonnes avec des valeurs par défaut
    valeurs_par_defaut = {
        'RayExtraterrestreH': 9999,
        'RayExtraterrestreDirectN': 9999,
        'RayIRciel': 9999,
        'IlluminanceGlobalH': 999999,
        'IlluminanceDirectN': 999999,
        'IlluminanceDiffusH': 999999,
        'LuminanceZenith': 9999,
        'Visibilite': 9999,
        'HtPlafond': 99999,
        'ObsMeteo': 0,
        'ObsMeteoCode': 999999999,
        'Pluie': 999,
        'AerosolOptiqueEp': 999,
        'NeigeEp': 999,
        'NeigeJourDepuis': 99,
        'Albedo': 0.2,
        'PluieDebit': 0,
    }

    for key, valeur in valeurs_par_defaut.items():
        if key in config_dest:
            col_dest = config_dest[key]
            df_dest.iloc[ld_depart:ld_fin+1, col_dest] = valeur

    return df_dest

def exporter_en_csv(df, nom_fichier):
    """Exporter un DataFrame en CSV avec des séparateurs US et des points comme décimales."""
    return df.to_csv(nom_fichier, index=False, sep=',', decimal='.')
