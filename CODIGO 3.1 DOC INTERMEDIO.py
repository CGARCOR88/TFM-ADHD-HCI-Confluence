# -*- coding: utf-8 -*-

import pandas as pd

# ========== RUTAS DE ARCHIVOS ==========
RUTA_COD1 =         r"C:\Users\Usuario\Desktop\resultados_1.xlsx"
RUTA_COD2 =         r"C:\Users\Usuario\Desktop\resultados_gwas.xlsx"
ARCHIVO_SALIDA =    r"C:\Users\Usuario\Desktop\intermedio_bd.xlsx"

# ========================================================================
# --------------> FUN 1 : LECTURA DEL ARCHIVO: RESULTADOS 1 <-------------
# ========================================================================

def leer_cod1_maestra_y_reactome(ruta_cod1: str):
    try:
        maestra_df = pd.read_excel(ruta_cod1, sheet_name="Maestra")
        reactome_df = pd.read_excel(ruta_cod1, sheet_name="Reactome")
    except Exception as e:
        print(f"[ERROR] No se pudieron leer hojas de {ruta_cod1}: {e}")
        return None, None

    # Normalizar nombres de columnas
    maestra_df.columns = [c.strip().lower() for c in maestra_df.columns]
    reactome_df.columns = [c.strip().lower() for c in reactome_df.columns]

    return maestra_df, reactome_df

# ========================================================================
# -------------> FUN 2 : LECTURA DEL ARCHIVO RESULTADOS GWAS <------------
# ========================================================================

def leer_cod2_gwas(ruta_cod2: str):
    try:
        gwas_df = pd.read_excel(ruta_cod2, sheet_name="resultados_gwas")
    except Exception as e:
        print(f"[ERROR] No se pudo leer hoja 'resultados_gwas' de {ruta_cod2}: {e}")
        return None

    gwas_df.columns = [c.strip().lower() for c in gwas_df.columns]
    return gwas_df

# ========================================================================
# --------------------> FUN 3 : INCLUSION DE FENOTIPOS <------------------
# ========================================================================

def derivar_fenotipos(maestra_df: pd.DataFrame):
    if maestra_df is None or "fenotipo" not in maestra_df.columns:
        return pd.DataFrame(columns=["id", "trait"])

    fenotipos_unicos = sorted(set(maestra_df["fenotipo"].dropna().unique()))
    fenotipos_tbl = pd.DataFrame({
        "id": range(1, len(fenotipos_unicos) + 1),
        "trait": fenotipos_unicos
    })
    return fenotipos_tbl

# ========================================================================
# ---------------------> FUN 4 : CONTRUCCION TABLAS <---------------------
# ========================================================================

def construir_tablas_intermedias(maestra_df, reactome_df, gwas_df):
    if maestra_df is None:
        return None, None, None, None, None, None

    # ---- Hoja genes ----
    genes_tbl = pd.DataFrame({
        "id": range(1, len(maestra_df) + 1),
        "nombre": maestra_df.get("genename"),
        "gen": maestra_df.get("symbol_input"),
        "simbolo": maestra_df.get("gen"),
        "localizacion_cromosomica": maestra_df.get("localizacion_cromosomica"),
        "entrez_id": maestra_df.get("entrez"),
        "ensembl_id": maestra_df.get("ensembl"),
        "uniprot_id": maestra_df.get("uniprot")
    })

    # ---- Hoja pathways ----
    if reactome_df is not None:
        pathways_unicos = sorted(set(reactome_df["reactome_name"].dropna().unique()))
        pathways_tbl = pd.DataFrame({
            "id": range(1, len(pathways_unicos) + 1),
            "nombre": pathways_unicos
        })
    else:
        pathways_tbl = pd.DataFrame(columns=["id", "nombre"])

    # ---- Hoja fenotipos ----
    fenotipos_tbl = derivar_fenotipos(maestra_df)

    # ---- Hoja artículos ----
    if gwas_df is not None:
        articulos_unicos = gwas_df.drop_duplicates(subset=["pmid"])
        articulos_tbl = pd.DataFrame({
            "pmid": articulos_unicos["pmid"],
            "doi": pd.NA,
            "titulo": pd.NA,
            "anio": pd.NA
        })
    else:
        articulos_tbl = pd.DataFrame(columns=["pmid", "doi", "titulo", "anio"])

    # ---- Hoja variantes ----
    if gwas_df is not None:
        variantes_tbl = gwas_df.drop_duplicates(subset=["rsid"])[["rsid", "pvalue"]]
    else:
        variantes_tbl = pd.DataFrame(columns=["rsid", "pvalue"])

    # ---- Hoja asociaciones ----
    asociaciones_tbl = pd.DataFrame(columns=["id", "gen_id", "fenotipo_id", "via_id", "pmid", "rsid", "pvalue"])

    return genes_tbl, pathways_tbl, fenotipos_tbl, articulos_tbl, variantes_tbl, asociaciones_tbl


    # **********************************************************
    # *********** PROCESAMIENTO DE DATOS Y EXPORTACIÓN *********
    # **********************************************************
    
def exportar_excel_intermedio():
    print("[1/3] Leyendo datos…")
    maestra_df, reactome_df = leer_cod1_maestra_y_reactome(RUTA_COD1)
    gwas_df = leer_cod2_gwas(RUTA_COD2)

    print("[2/3] Construyendo tablas intermedias…")
    genes_tbl, pathways_tbl, fenotipos_tbl, articulos_tbl, variantes_tbl, asociaciones_tbl = construir_tablas_intermedias(
        maestra_df, reactome_df, gwas_df
    )

    print("[3/3] Exportando a Excel…")
    with pd.ExcelWriter(ARCHIVO_SALIDA) as writer:
        genes_tbl.to_excel(writer, sheet_name="Genes", index=False)
        pathways_tbl.to_excel(writer, sheet_name="Pathways", index=False)
        fenotipos_tbl.to_excel(writer, sheet_name="Fenotipos", index=False)
        articulos_tbl.to_excel(writer, sheet_name="Articulos", index=False)
        variantes_tbl.to_excel(writer, sheet_name="Variantes", index=False)
        asociaciones_tbl.to_excel(writer, sheet_name="Asociaciones", index=False)

    print(f"✔ Archivo intermedio generado en: {ARCHIVO_SALIDA}")


# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    exportar_excel_intermedio()
