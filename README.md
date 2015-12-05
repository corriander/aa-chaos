aachaos
=======

Simple utility for pulling down Andrew & Arnolds ISP line info from
their [Chaos API](http://aa.net.uk/support-chaos.html).

This is geared towards a simple **Home::1** service configuration
(100/200 GB, single line) and a mini-project for my own purposes
(inc. a sandpit for trying out some new things); no guarantees about
functionality or completeness!

Credit for some inspiration for implementing as a webapp from 
[here][databurndown] as linked to by A&A.


Install
-------

> This is a very rough guide, proper installation hasn't been
> implemented.

Put user credentials in `~/.config/aachaos/auth` (`chmod 600`) in the
following format:

	user:password

A database will be created at `~/.local/share/aachaos/store.db` (NB:
this hasn't been tested, there'll likely be issues here).


Usage
-----

Execute in the project directory via:

	python -m aachaos.main

Run tests in the project directory with:

	python -m unittest discover


TODO
----

  - Shift database interface into new `db.py` so the following
	architecture can be implemented cleanly:

				       +-----+          +-----+
				       |     |          | API |
				       | DB  |          |     |
				       +-+-^-+          +--+--+
				         | |               |
				         | |               |
				+--------v-+----------+    |
				|     db interface    |    |
				+----+-------------^--+    |
				     |             |       |
				     |             |       |
				     |       +-----+--+    |
				     |       | store  |    |
				     |       +-----^--+    |
				     |             |       |
				     |             |       |
				+----v-------------+-------v-----+
				|             get                |
				+----+-------------+-------^-----+
				     |             |       |
					 |             |       |
				+----v----+        |       |
		gfx	<---|   vis   |        |       |
				+----+----+        |       |
				     |             |       |
					 |             |       |
				+----v-------------v-------+-----+
				|             main               |
				+--------------------------------+

	It's similar now, but with `store` providing the database
	interface. This is sufficient but not quite as semantically tight.
  - We should generate the visualisation when fetching from the API as
	there's no point doing it at other times (or, alternatively, only
	generate it if it hasn't been generated since the last fetch...
	maybe less intensive on the server).
  - Dependencies
  - Install / package
  - Proper [entry point][todo_entrypoint] (refactor main slightly).
	
	
[databurndown]: https://github.com/sammachin/databurndown.git
[todo_entrypoint]: https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
