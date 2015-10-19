-- Create a view linking the quota_history and quota_monthly tables as
-- well as providing a percentage value.
CREATE VIEW quota_vw AS
SELECT
	timestamp,
	remaining,
	quota AS total,
	(CAST(remaining AS REAL)/ quota * 100) AS percent
FROM
	quota_history qh
	INNER JOIN 
	quota_monthly qm
	ON datetime(qm.month_start) = datetime(qh.timestamp, 'start of month')
;
