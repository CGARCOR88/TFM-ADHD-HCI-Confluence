
# -*- coding: utf-8 -*-

import math
import pandas as pd
import mysql.connector as mysql

# ================================================================
# -----------------> FUN 1 : LECTURA DE LA HOJA <-----------------
# ================================================================

EXCEL_PATH = r"C:\Users\Usuario\Desktop\intermedio_bd.xlsx"
SHEET_GENES = "genes"
SHEET_FENOS = "fenotipos"
SHEET_VIAS  = "vias"
SHEET_ART   = "articulos"
SHEET_VARS  = "variantes"
SHEET_ASSOC = "asociaciones"

DB_CFG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "1234",
    "database": "genes_2e",
    "autocommit": False
}

# ================================================================
# -----------------------> FUN AUXILIARES <-----------------------
# ================================================================

def to_none(x):
    """Convierte NaN y cadenas vacías a None para MySQL."""
    if x is None:
        return None
    try:
        if isinstance(x, float) and math.isnan(x):
            return None
    except Exception:
        pass
    if isinstance(x, str) and x.strip() == "":
        return None
    return x

def fetchone_id(cur):
    row = cur.fetchone()
    return None if row is None else row[0]

# ================================================================
# -----------------------> CARGA DE DATOS <-----------------------
# ================================================================

def load_intermediate_excel(path):
    xls = pd.ExcelFile(path)
    def get_sheet(name):
        df = pd.read_excel(xls, sheet_name=name)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    return {
        "genes":        get_sheet(SHEET_GENES),
        "fenotipos":    get_sheet(SHEET_FENOS),
        "vias":         get_sheet(SHEET_VIAS),
        "articulos":    get_sheet(SHEET_ART),
        "variantes":    get_sheet(SHEET_VARS),
        "asociaciones": get_sheet(SHEET_ASSOC),
    }

# ======================================================================
# -------------------------> FUNCIONES UPSERTS <------------------------
# ======================================================================

   # --> insercion de genes
     
def upsert_gene(cur, row):
    sql = ("""
        INSERT INTO genes (nombre, gen, simbolo, localizacion_cromosomica, entrez_id, ensembl_id, uniprot_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            nombre=VALUES(nombre),
            gen=VALUES(gen),
            localizacion_cromosomica=VALUES(localizacion_cromosomica),
            entrez_id=VALUES(entrez_id),
            ensembl_id=VALUES(ensembl_id),
            uniprot_id=VALUES(uniprot_id),
            id=LAST_INSERT_ID(id)
    """)
    cur.execute(sql, (
        to_none(row.get("nombre")),
        to_none(row.get("gen")),
        to_none(row.get("simbolo")),
        to_none(row.get("localizacion_cromosomica")),
        to_none(row.get("entrez_id")),
        to_none(row.get("ensembl_id")),
        to_none(row.get("uniprot_id")),
    ))
    cur.execute("SELECT LAST_INSERT_ID()")
    return fetchone_id(cur)

    # --> insercion de fenotipo
    
def get_or_create_fenotipo(cur, trait, efo_id=None):
    trait = to_none(trait)
    if not trait:
        return None
    cur.execute("SELECT id FROM fenotipos WHERE trait=%s LIMIT 1", (trait,))
    fid = fetchone_id(cur)
    if fid is not None:
        if efo_id is not None:
            cur.execute("UPDATE fenotipos SET efo_id=%s WHERE id=%s", (to_none(efo_id), fid))
        return fid
    cur.execute("INSERT INTO fenotipos (trait, efo_id) VALUES (%s,%s)", (trait, to_none(efo_id)))
    return cur.lastrowid

    # --> insercion de pathways

def upsert_via(cur, nombre, reactome_stid=None):
    nombre = to_none(nombre)
    reactome_stid = to_none(reactome_stid)
    if not nombre and not reactome_stid:
        return None

    sql = ("""
        INSERT INTO vias (nombre, reactome_id)
        VALUES (%s,%s)
        ON DUPLICATE KEY UPDATE
            nombre = COALESCE(VALUES(nombre), nombre),
            reactome_id = COALESCE(VALUES(reactome_id), reactome_id),
            id = LAST_INSERT_ID(id)
    """)
    cur.execute(sql, (nombre, reactome_stid))
    cur.execute("SELECT LAST_INSERT_ID()")
    return fetchone_id(cur)

def upsert_articulo(cur, pmid, doi=None, titulo=None, anio=None):
    pmid = to_none(pmid)
    if pmid is None:
        return
    sql = ("""
        INSERT INTO articulos (pmid, doi, titulo, anio)
        VALUES (%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            doi=COALESCE(VALUES(doi), doi),
            titulo=COALESCE(VALUES(titulo), titulo),
            anio=COALESCE(VALUES(anio), anio)
    """)
    cur.execute(sql, (pmid, to_none(doi), to_none(titulo), to_none(anio)))

    # --> insercion de variantes

def upsert_variante(cur, rsid, pvalue):
    rsid = to_none(rsid)
    if not rsid:
        return
    sql = ("""
        INSERT INTO variantes (rsid, pvalue)
        VALUES (%s,%s)
        ON DUPLICATE KEY UPDATE
            pvalue = LEAST(COALESCE(variantes.pvalue, 1e308), COALESCE(VALUES(pvalue), 1e308))
    """)
    cur.execute(sql, (rsid, to_none(pvalue)))

    # --> insercion de asociaciones

def insert_asociacion(cur, gen_id, fenotipo_id, via_id, pmid, rsid, pvalue):
    sql = ("""
        INSERT INTO asociaciones (gen_id, fenotipo_id, via_id, pmid, rsid, pvalue)
        VALUES (%s,%s,%s,%s,%s,%s)
    """)
    cur.execute(sql, (
        to_none(gen_id), to_none(fenotipo_id), to_none(via_id),
        to_none(pmid), to_none(rsid), to_none(pvalue)
    ))

# ===================== PIPELINE =====================
def main():
    data = load_intermediate_excel(EXCEL_PATH)
    df_genes = data["genes"].copy()
    df_fenos = data["fenotipos"].copy()
    df_vias  = data["vias"].copy()
    df_art   = data["articulos"].copy()
    df_vars  = data["variantes"].copy()
    df_assoc = data["asociaciones"].copy()

    # normaliza nombres de columnas
    for df in (df_genes, df_fenos, df_vias, df_art, df_vars, df_assoc):
        df.columns = [str(c).strip().lower() for c in df.columns]

    cnx = mysql.connect(**DB_CFG)
    cur = cnx.cursor()

    try:
        # 1) GENES: simbolo -> id
        simbolo_to_id = {}
        for _, r in df_genes.iterrows():
            simbolo = str(r.get("simbolo") or "").strip()
            if not simbolo:
                continue
            gid = upsert_gene(cur, r)
            simbolo_to_id[simbolo] = gid

        # 2) FENOTIPOS: trait -> id
        trait_to_id = {}
        for _, r in df_fenos.iterrows():
            tid = get_or_create_fenotipo(cur, r.get("trait"), r.get("efo_id"))
            if tid is not None and r.get("trait") is not None:
                trait_to_id[str(r.get("trait"))] = tid

        # 3) VIAS: construye mapa por nombre y por reactome_stid
        
        via_to_id = {}
        for _, r in df_vias.iterrows():
            vname = r.get("nombre")
            rid   = r.get("reactome_stid")
            vid = upsert_via(cur, vname, rid)
            if vid is not None:
                if vname:
                    via_to_id[str(vname).strip()] = vid
                if rid:
                    via_to_id[str(rid).strip()] = vid

        # 4) ARTICULOS
        
        for _, r in df_art.iterrows():
            upsert_articulo(cur, r.get("pmid"), r.get("doi"), r.get("titulo"), r.get("anio"))

        # 5) VARIANTES
        
        for _, r in df_vars.iterrows():
            upsert_variante(cur, r.get("rsid"), r.get("pvalue"))

        # 6) ASOCIACIONES: resuelve vía por reactome_stid (prioridad) o por via_nombre
        
        for _, r in df_assoc.iterrows():
            simbolo = r.get("simbolo")
            trait   = r.get("trait")
            via_nm  = r.get("via_nombre")
            rid_as  = r.get("reactome_stid")
            pmid    = r.get("pmid")
            rsid    = r.get("rsid")
            pvalue  = r.get("pvalue")

            gen_id = simbolo_to_id.get(to_none(simbolo)) if simbolo else None
            fenotipo_id = trait_to_id.get(to_none(trait)) if trait else None

            via_id = None
            
            # 1º: intentar por reactome_stid (si viene en asociaciones)
            if rid_as:
                via_id = via_to_id.get(str(rid_as).strip())
                if via_id is None:
                    via_id = upsert_via(cur, None, rid_as)
                    if via_id:
                        via_to_id[str(rid_as).strip()] = via_id

            # 2º: si no, intentar por via_nombre
            if via_id is None and via_nm:
                via_id = via_to_id.get(str(via_nm).strip())
                if via_id is None:
                    # crear al vuelo si viene nombre pero no estaba en hoja vias
                    via_id = upsert_via(cur, via_nm, None)
                    if via_id:
                        via_to_id[str(via_nm).strip()] = via_id

            # Inserta asociación si tiene al menos gen y fenotipo
            if gen_id and fenotipo_id:
                insert_asociacion(cur, gen_id, fenotipo_id, via_id, pmid, rsid, pvalue)

        cnx.commit()
        print(" Carga completada y confirmada (COMMIT).")

    except Exception as e:
        cnx.rollback()
        print(" Error, se hizo ROLLBACK:", repr(e))
        raise
    finally:
        cur.close()
        cnx.close()

if __name__ == "__main__":
    main()
