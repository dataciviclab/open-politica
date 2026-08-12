-- mart_kpi — la "pagella del Parlamento" (formato lungo, interrogabile)
SELECT *
FROM clean_input
ORDER BY dimensione, periodo, kpi
