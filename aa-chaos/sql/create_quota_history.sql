-- The quota_history table contains remaining quota at the specified
-- times, this needs to be xref'd with quota_monthly to get the total
-- quota for that period.
CREATE TABLE quota_history(
	timestamp TEXT,
	remaining INT,
	PRIMARY KEY(timestamp)
);
