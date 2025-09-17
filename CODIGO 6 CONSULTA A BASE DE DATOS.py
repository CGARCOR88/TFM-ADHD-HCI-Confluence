# -*- coding: utf-8 -*-
"""

Consultas a base de datos ya creada

SELECT
  v.reactome_id     AS `Reactome ID`,
  v.nombre          AS `via nombre`,
  GROUP_CONCAT(DISTINCT CASE WHEN f.trait='TDAH' THEN g.simbolo END ORDER BY g.simbolo) AS TDAH,
  GROUP_CONCAT(DISTINCT CASE WHEN f.trait='ACI'  THEN g.simbolo END ORDER BY g.simbolo) AS ACI
FROM asociaciones a
JOIN genes      g ON a.gen_id      = g.id
JOIN vias       v ON a.via_id      = v.id
JOIN fenotipos  f ON a.fenotipo_id = f.id
WHERE f.trait IN ('TDAH','ACI')
  AND v.reactome_id IN (
    SELECT v2.reactome_id
    FROM asociaciones a2
    JOIN vias       v2 ON a2.via_id      = v2.id
    JOIN fenotipos  f2 ON a2.fenotipo_id = f2.id
    WHERE v2.reactome_id IS NOT NULL
      AND f2.trait IN ('TDAH','ACI')
    GROUP BY v2.reactome_id
    HAVING COUNT(DISTINCT f2.trait) = 2
  )
GROUP BY v.reactome_id, v.nombre
ORDER BY v.reactome_id;

"""