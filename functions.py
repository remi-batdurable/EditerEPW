import pandas as pd
import numpy as np
from datetime import datetime

def lire_fichier(fichier):
    """Lire un fichier (Excel ou CSV) et retourner un DataFrame."""
    if fichier.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(fichier, engine='openpyxl')
    elif fichier.name.endswith('.csv'):
        # Essayer plusieurs encodages courants
        encodages = ['utf-8', 'latin1', 'ISO-8859-1', 'cp1252']
        for encodage in encodages:
            try:
                return pd.read_csv(fichier, sep=',', decimal='.', encoding=encodage)
            except UnicodeDecodeError:
                continue
        # Si aucun encodage ne fonctionne, lever une erreur
        raise ValueError("Impossible de lire le fichier CSV. Encodage non supporté.")
    else:
        raise ValueError("Format de fichier non supporté. Utilisez .xlsx, .xls ou .csv.")

def exporter_vers_epw(df_source, df_dest, nd_donnees=8760):
    """
    Adapter les données du fichier TRACC (Excel) vers le format EPW (CSV).
    df_source : DataFrame du fichier source (TRACC).
    df_dest : DataFrame du fichier destination (EPW).
    nd_donnees : Nombre de lignes de données (8760 par défaut).
    """
    # Configuration des colonnes source (TRACC)
    config_source = {
        'TempAir': 8,          # Colonne 9 en VBA (index 8 en Python)
        'TempSol': 28,         # Colonne 29 en VBA (index 28 en Python)
        'HR': 11,              # Colonne 12 en VBA (index 11 en Python)
        'HS': 29,              # Colonne 30 en VBA (index 29 en Python)
        'RR': 26,              # Colonne 27 en VBA (index 26 en Python)
        'VentForce': 25,       # Colonne 26 en VBA (index 25 en Python)
        'VentDir': 24,         # Colonne 25 en VBA (index 24 en Python)
        'TempCiel': 31,        # Colonne 32 en VBA (index 31 en Python)
        'TempRosee': 9,        # Colonne 10 en VBA (index 9 en Python)
        'SoleilHt': 14,        # Colonne 15 en VBA (index 14 en Python)
        'SoleilAzimut': 13,    # Colonne 14 en VBA (index 13 en Python)
        'RayGlobalH': 17,      # Colonne 18 en VBA (index 17 en Python)
        'RayDirectN': 21,      # Colonne 22 en VBA (index 21 en Python)
        'RayDiffusH': 18,      # Colonne 19 en VBA (index 18 en Python)
        'Nebulosite': 30,      # Colonne 31 en VBA (index 30 en Python)
        'PressionATM': 12,     # Colonne 13 en VBA (index 12 en Python)
    }

    # Configuration des colonnes destination (EPW)
    config_dest = {
        'TempAir': 3,               # Colonne 4 en EPW (index 3)
        'TempRosee': 4,             # Colonne 5 en EPW (index 4)
        'HR': 5,                    # Colonne 6 en EPW (index 5)
        'PressionATM': 6,           # Colonne 7 en EPW (index 6)
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
    ls_depart = 26  # Ligne 27 en VBA (index 26 en Python)
    ls_fin = ls_depart + nd_donnees - 1
    ld_depart = 19  # Ligne 20 en EPW (index 19 en Python)
    ld_fin = ld_depart + nd_donnees - 1

    # Copier les données de la source vers la destination
    for key, col_src in config_source.items():
        if key in config_dest:
            col_dest = config_dest[key]
            df_dest.iloc[ld_depart:ld_fin+1, col_dest] = df_source.iloc[ls_depart:ls_fin+1, col_src].values

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
        col_dest = config_dest[key]
        df_dest.iloc[ld_depart:ld_fin+1, col_dest] = valeur

    return df_dest

def formater_dates(df, col_date=0, ld_depart=19, ld_fin=None):
    """Formater les dates au format AAAA/MM/JJ."""
    if ld_fin is None:
        ld_fin = ld_depart + 8759  # 8760 lignes par défaut
    for i in range(ld_depart, ld_fin + 1):
        if pd.notna(df.iloc[i, col_date]):
            date = df.iloc[i, col_date]
            if isinstance(date, (datetime, pd.Timestamp)):
                df.iloc[i, col_date] = date.strftime("%Y/%m/%d")
    return df

def exporter_en_csv(df, nom_fichier):
    """Exporter un DataFrame en CSV avec des séparateurs US."""
    return df.to_csv(nom_fichier, index=False, sep=',', decimal='.')
