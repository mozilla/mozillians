from utils import make_nsfind, ET, geocoder_factory
import urllib

# http://developer.yahoo.com/maps/rest/V1/geocode.html

def geocode(q, api_key):
    find = make_nsfind({'ns': 'urn:yahoo:maps'})
    args = {'location': q, 'appid': api_key}
    url = 'http://local.yahooapis.com/MapsService/V1/geocode?%s' % urllib.urlencode(args)
    et = ET.parse(urllib.urlopen(url))

    result = find(et, '//ns:Result')
    if not result:
        return (None, (None, None))
    else:
        namebits = {}
        for field in ('Address', 'City', 'State', 'Zip', 'Country'):
            bit = find(result, 'ns:%s' % field)
            if bit is not None and bit.text:
                namebits[field] = bit.text.decode('utf8')

        if 'Address' in namebits:
            name = '%(Address)s, %(City)s, %(State)s %(Zip)s, %(Country)s' % namebits
        elif 'Zip' in namebits:
            name = '%(City)s, %(State)s %(Zip)s, %(Country)s' % namebits
        elif 'City' in namebits:
            name = '%(City)s, %(State)s, %(Country)s' % namebits
        elif 'State' in namebits:
            name = '%(State)s, %(Country)s' % namebits
        elif 'Country' in namebits:
            name = namebits['Country']
        else:
            return (None, (None, None))

        lat = float(find(result, 'ns:Latitude').text)
        lon = float(find(result, 'ns:Longitude').text)

        return (name, (lat, lon))

geocoder = geocoder_factory(geocode)
