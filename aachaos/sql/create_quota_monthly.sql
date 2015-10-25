-- quota_monthly contains the total monthly quota aligned to the start
-- of the month; aa align it like this and quota is fixed for the
-- current month.
CREATE TABLE quota_monthly(
	month_start TEXT,
	quota INT,
	PRIMARY KEY(month_start)
);
