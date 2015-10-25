-- Schema description.
CREATE TABLE quota_history(
	timestamp TEXT,
	remaining INT,
	PRIMARY KEY(timestamp)
);

CREATE TABLE quota_monthly(
	month_start TEXT,
	quota INT,
	PRIMARY KEY(month_start)
);
