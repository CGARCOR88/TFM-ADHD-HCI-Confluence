# -*- coding: utf-8 -*-
"""
step06_queries.py  —  Consultas analíticas sobre genes_2e
==========================================================
Ejecuta las 4 consultas analíticas sobre la base de datos MySQL
y guarda los resultados en data/output/resultados_consultas.xlsx.
"""

import logging

import mysql.connector
import pandas as pd

from config.settings import DB_CFG, DATA_OUT

logger = logging.getLogger(__name__)

# ── Consultas analíticas ──────────────────────────────────────────────────────

_Q1 = """
SELECT
  v.reactome_id                                                             AS `Reactome ID`,
  v.nombre                                                                  AS `Via`,
  GROUP_CONCAT(DISTINCT CASE WHEN f.trait = 'TDAH' THEN g.simbolo END
               ORDER BY g.simbolo)                                          AS `Genes TDAH`,
  GROUP_CONCAT(DISTINCT CASE WHEN f.trait = 'ACI'  THEN g.simbolo END
               ORDER BY g.simbolo)                                          AS `Genes ACI`,
  COUNT(DISTINCT CASE WHEN f.trait = 'TDAH' THEN g.id END)                 AS `N_TDAH`,
  COUNT(DISTINCT CASE WHEN f.trait = 'ACI'  THEN g.id END)                 AS `N_ACI`
FROM asociaciones a
JOIN genes      g ON a.gen_id      = g.id
JOIN vias       v ON a.via_id      = v.id
JOIN fenotipos  f ON a.fenotipo_id = f.id
WHERE f.trait IN ('TDAH', 'ACI')
  AND v.reactome_id IN (
      SELECT v2.reactome_id
      FROM   asociaciones a2
      JOIN   vias       v2 ON a2.via_id      = v2.id
      JOIN   fenotipos  f2 ON a2.fenotipo_id = f2.id
      WHERE  v2.reactome_id IS NOT NULL
        AND  f2.trait IN ('TDAH', 'ACI')
      GROUP BY v2.reactome_id
      HAVING COUNT(DISTINCT f2.trait) = 2
  )
GROUP BY v.reactome_id, v.nombre
ORDER BY (N_TDAH + N_ACI) DESC, v.reactome_id
"""

_Q2 = """
SELECT
  g.simbolo,
  g.ensembl_id,
  f.trait                          AS fenotipo,
  COUNT(DISTINCT a.rsid)           AS n_variantes,
  MIN(a.pvalue)                    AS pvalue_min
FROM asociaciones a
JOIN genes     g ON a.gen_id      = g.id
JOIN fenotipos f ON a.fenotipo_id = f.id
WHERE a.pvalue < 5e-8
GROUP BY g.simbolo, g.ensembl_id, f.trait
ORDER BY n_variantes DESC
LIMIT 50
"""

_Q3 = """
SELECT
  f.trait                          AS fenotipo,
  COUNT(DISTINCT a.gen_id)         AS n_genes,
  COUNT(DISTINCT a.via_id)         AS n_vias,
  COUNT(DISTINCT a.rsid)           AS n_variantes,
  COUNT(DISTINCT a.pmid)           AS n_articulos
FROM asociaciones a
JOIN fenotipos f ON a.fenotipo_id = f.id
GROUP BY f.trait
"""

_Q4 = """
SELECT
  g.simbolo,
  f.trait,
  COUNT(DISTINCT a.via_id) AS n_vias
FROM asociaciones a
JOIN genes     g ON a.gen_id      = g.id
JOIN fenotipos f ON a.fenotipo_id = f.id
WHERE a.via_id IS NOT NULL
GROUP BY g.simbolo, f.trait
ORDER BY n_vias DESC
LIMIT 20
"""

QUERIES = [
    ("Q1_Vias_Compartidas",   "Vías moleculares compartidas TDAH ↔ ACI",              _Q1),
    ("Q2_Top_Variantes_GWAS", "Genes con más variantes GWAS significativas (p<5e-8)",  _Q2),
    ("Q3_Resumen_Fenotipo",   "Resumen por fenotipo (genes, vías, variantes)",         _Q3),
    ("Q4_Top_Genes_Por_Vias", "Top 20 genes con más vías moleculares",                 _Q4),
]


def main() -> None:
    logger.info("Conectando a MySQL para ejecutar consultas analíticas...")
    try:
        conn = mysql.connector.connect(**DB_CFG)
    except mysql.connector.Error as exc:
        logger.error("No se pudo conectar a MySQL: %s", exc)
        raise

    DATA_OUT.mkdir(parents=True, exist_ok=True)
    output_path = DATA_OUT / "resultados_consultas.xlsx"

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_name, description, sql in QUERIES:
                logger.info("Ejecutando %s: %s", sheet_name, description)
                try:
                    df = pd.read_sql(sql, conn)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info("  → %d filas encontradas", len(df))
                    if not df.empty:
                        logger.info("\n%s\n", df.to_string(index=False))
                except Exception as exc:
                    logger.error("  Error en %s: %s", sheet_name, exc)
    finally:
        conn.close()

    logger.info("Resultados exportados a: %s", output_path)


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()