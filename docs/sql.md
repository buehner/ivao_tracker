# SQL

Use this SQL to create a line from the single point geoms of a pilots tracks:

```sql
SELECT ST_MakeLine(p.geometry ORDER BY p.id) AS line_geom
FROM pilottrack p
WHERE p."pilotSessionId" = 123456789;
```
