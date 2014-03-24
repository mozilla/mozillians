[mozillians.org](https://mozillians.org)
========

A community directory for Mozillians to connect with each other.

See what's deployed
=======
[What's deployed for this project?](http://mzl.la/mozillians-deployed) See what commits are deployed on our [developer](https://mozillians-dev.allizom.org/), [stage](https://mozillians-dev.allizom.org/) and [production](http://mozillians.org/) environments.

Install, docs, API and more
=======
For documentation, see [mozillians.rtfd.org](http://mozillians.readthedocs.org/) or build the docs/

Contribute
=======

File a bug
------
[Create a bug](https://bugzilla.mozilla.org/enter_bug.cgi?product=Community%20Tools&component=Phonebook) on bugzilla.mozilla.org in the Community Tools > Phonebook component. If you then want to give a Pull Request, mention the bug number in the pull request to help with tracking. Here's an example commit message for a bug fix:
```
[fix bug 937104] Update to latest playdoh.
```

Write code
------
Get started with our [How to Contribute](http://mozillians.readthedocs.org/en/latest/contribute.html) documentation.

Chat with the team
------
You can talk with the team in the #commtools IRC channel on [irc.mozilla.org](http://irc.mozilla.org/). We're a friendly group!


Temporary notes about converting the location data
==================================================

These are some notes about converting from the old way of storing mozillians' location
data (the country, region, and city fields) to the new way.

The new data fields
-------------------

New fields have been added to the UserProfile. `geo_country`, `geo_region`, and `geo_city`
are nullable foreign keys to the `Country`, `Region`, and `City` models in the new
`geo` app. `lat` and `lng` are nullable floats to record the exact map point that the
user selected when entering their location.

Converting the old data to the new fields
-----------------------------------------

There's a temporary `geocode` management command. Running it will convert a batch of
the profiles' data using the Mapbox (beta) geocoding API. It creates new Country, Region,
and City objects as needed, and points at them from the new fields in the user profile.
It sets the users' lat and lng to the same lat and lng as the city we came up with for
them, if any.

To run the geocode command:

    python manage.py geocode

You can run it repeatedly until all the data is converted. (It'll print out how many
remain after each run.)

The geocoding code is not perfect. It's a tradeoff between converting a good proportion
of the users who have entered data in a reasonable format, and not spending too much effort.
If someone has entered, say, "The Bay area" in the city or region field, this isn't going
to make any sense of it. The user will probably end up with the country set, and maybe
the region (state), but not the city.

For efficiency, each time the geocode command decides to map a new combination of
country, region, and city entered by a user to a particular new geo_country, geo_region,
and maybe geo_city, it adds a record to a new (temporary) table `geocoding`. Then it
looks for any other users who have entered the same data (case-insensitive) and applies
the same conversion without looking up the same input at Mapbox again.

We can dump the data from the geo app
on a developer system where we've run the geocoding, then load the same data on a test
or production server.  Then running the geocode command again will first go through all
the known geocodings and apply them to the current users, without hitting Mapbox again.
Then it will continue with the profiles it was unable to geocode, using Mapbox as needed,
but it should still be a lot more efficient than running the whole thing from scratch.

To dump the data:

    python manage.py dumpdata geo >geodata.json

To load the data:

    python manage.py loaddata geodata.json


Cleaning up when done
---------------------

After all the data has been converted, and the new interface is in place so people are
entering their data the new way:

* Delete the old country, region, and city fields from UserProfile.
* Delete the `geocoding` model from `geo/models.py`.
* Add the corresponding migrations.
* Delete the geocode management command (`mozillians/geo/management/commands/geocode.py` and any
  `__init__.py` files in empty directories on that path).
* Delete this section of the docs.
