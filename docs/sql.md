# SQL

Use this SQL to create a (simplified) line from the single point geoms of a pilots tracks:

```sql
SELECT ST_Simplify(ST_MakeLine(p.geometry ORDER BY p.id), 0.00003) AS line_geom
FROM pilottrack p
WHERE p."pilotSessionId" = 123456789;
-- WHERE p."pilotSessionId" = (SELECT ps.id FROM pilotsession ps WHERE ps.callsign = 'ABCDE');
```

## Clustering

Variant 1:

```sql
SELECT
  ST_Centroid(ST_Collect(geometry)) AS cluster_geom,
  COUNT(*) AS num_points
FROM (
  SELECT geometry, ST_ClusterKMeans(geometry, 100) OVER () AS cluster_id
  FROM pilottrack
) AS clusters
GROUP BY cluster_id order by num_points DESC;
```

Density based approach with bboxes:

```sql
SELECT kmean, count(*), ST_SetSRID(ST_Extent(geom), 4326) as bbox
FROM
(
    SELECT ST_ClusterKMeans(geometry, 100) OVER() AS kmean, ST_Centroid(geometry) as geom
    FROM pilottrack
) tsub
GROUP BY kmean;
```

Density based approach with centroids:

```sql
SELECT kmean, count(*), st_centroid(st_union(geom)) AS geom
FROM
(
 SELECT ST_ClusterKMeans(geometry, 100) OVER() AS kmean, ST_Centroid(geometry) as geom
 FROM pilottrack
) tsub
GROUP BY kmean;
```
