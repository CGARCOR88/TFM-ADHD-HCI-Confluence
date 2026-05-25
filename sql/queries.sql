-- ============================================================
-- sql/queries.sql
-- Consultas analíticas sobre la base de datos genes_2e
-- ============================================================

USE genes_2e;

-- ------------------------------------------------------------
-- Q1: Vías moleculares compartidas entre TDAH y ACI
--     Muestra las vías donde hay genes de ambos fenotipos
-- ------------------------------------------------------------
SELECT
  v.reactome_id                                                             AS `Reactome ID`,
  v.nombre                                                                  AS `Vía`,
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
ORDER BY (N_TDAH + N_ACI) DESC, v.reactome_id;


-- ------------------------------------------------------------
-- Q2: Genes con más variantes GWAS significativas (p < 5e-8)
-- ------------------------------------------------------------
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
LIMIT 50;


-- ------------------------------------------------------------
-- Q3: Resumen por fenotipo — genes, vías y variantes totales
-- ------------------------------------------------------------
SELECT
  f.trait                          AS fenotipo,
  COUNT(DISTINCT a.gen_id)         AS n_genes,
  COUNT(DISTINCT a.via_id)         AS n_vias,
  COUNT(DISTINCT a.rsid)           AS n_variantes,
  COUNT(DISTINCT a.pmid)           AS n_articulos
FROM asociaciones a
JOIN fenotipos f ON a.fenotipo_id = f.id
GROUP BY f.trait;


-- ------------------------------------------------------------
-- Q4: Top 20 genes con más vías moleculares asociadas
-- ------------------------------------------------------------
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
LIMIT 20;
