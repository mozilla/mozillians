Geocoders
=========

Code for accessing various geocoding web services with an ultra simple API:

    name, (lat, lon) = geocode('london')

The geocode functions return (unicode_place_name, (float_lat, float_lon)) if
the string can be geocoded, and (None, (None, None)) if it cannot.

Currently supported: Google Geocoder, Yahoo! Geocoder, Yahoo! Placemaker,
GeoNames and Multimap.

Google:

>>> from geocoders.google import geocoder
>>> geocode = geocoder('GOOGLE-API-KEY')
>>> geocode('new york')
(u'New York, NY, USA', (40.756053999999999, -73.986951000000005))
>>> geocode('oneuth')
(u'South, Bloomfield, NY 14469, USA', (-77.5385449999999, 42.865267000000003))

Yahoo!:

>>> from geocoders.yahoo import geocoder
>>> geocode = geocoder('YAHOO-API-KEY')
>>> geocode('new york')
(u'New York, NY, US', (40.714550000000003, -74.007124000000005))
>>> geocode('oneuth')
(u'Aneth, UT 84510, US', (37.217799999999997, -109.189911))

Yahoo! Placemaker:

>>> from geocoders.placemaker import geocoder
>>> geocode = geocoder('YAHOO-API-KEY')
>>> geocode('new york')
(u'New York, NY, US', (40.714500000000001, -74.007099999999994))
>>> geocode('oneuth')
(None, (None, None))

While Yahoo! Placemaker isn't strictly designed as a geocoder, in practice it
can be useful for things like "did you mean location X" in a regular search
engine.

GeoNames:

>>> from geocoders.geonames import geocode # No need for a geocoder factory
>>> geocode('new york')
(u'New York', (40.714269100000003, -74.005972900000003))
>>> geocode('oneuth')
(None, (None, None))

Multimap:

>>> from geocoders.multimap import geocoder
>>> geocode = geocoder('MULTIMAP-API-KEY')
>>> geocode('new york')
('New York, State of New York, United States', ('43.00035', '-75.49990'))
>>> geocode('oneuth')
('Omeath, Louth', ('54.08790', '-6.26070'))

Reversing the order
-------------------

Some libraries use (longitude, latitude) co-ordinate pairs instead of the
(latitude, longitude) returned by the geocode functions. The geocoder factory
functions all take an optional lonlat=True argument if you need this
behaviour. Some examples:

Google:

>>> from geocoders.google import geocoder
>>> geocode = geocoder('GOOGLE-API-KEY', lonlat = True)
>>> geocode('new york')
(u'New York, NY, USA', (-74.005972900000003, 40.714269100000003))

GeoNames:

>>> from geocoders.geonames import geocoder # Using geocoder factory
>>> geocode = geocoder(lonlat = True)
>>> geocode('new york')
(u'New York', (-74.005972900000003, 40.714269100000003))
