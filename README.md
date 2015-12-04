aachaos
=======

Simple utility for pulling down Andrew & Arnolds ISP line info from
their [Chaos API](http://aa.net.uk/support-chaos.html).

This is geared towards a simple **Home::1** service configuration
(100/200 GiB, single line). Inspiration from <https://github.com/sammachin/databurndown.git>.

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
		     |       +-----+--+    |
		     |             |       |
		     |             |       |
		+----v-------------+-------v-----+
		|             get                |
		+--------------------------------+

  - Add a separate `vis` module at the same level as `get`, with
	`main` adapted to provide access to both via defined "routes"
	(fetch and store from API, fetch from database). Make `main` work 
	properly when run as a script again, which it currently doesn't
	since using Python3. Note that we should generate the
	visualisation when fetching from the API as there's no point doing
	it at other times (or, alternatively, only generate it if it
	hasn't been generated since the last fetch... maybe less intensive
	on the server).
