from utils import make_nsfind, ET, geocoder_factory
import urllib

# http://developer.yahoo.com/geo/placemaker/guide/api_docs.html

def geocode(q, api_key):
    find = make_nsfind({
        'ns': 'http://wherein.yahooapis.com/v1/schema'
    })
    args = {
        'documentContent': q,
        'documentType': 'text/plain',
        'appid': api_key,
    }
    et = ET.parse(urllib.urlopen(
        'http://wherein.yahooapis.com/v1/document', urllib.urlencode(args))
    )
    place = find(et, 'ns:document/ns:placeDetails/ns:place')
    if place is None:
        return None, (None, None)
    else:
        name = find(place, 'ns:name').text.decode('utf8')
        lat = float(find(place, 'ns:centroid/ns:latitude').text)
        lon = float(find(place, 'ns:centroid/ns:longitude').text)
        return name, (lat, lon)

geocoder = geocoder_factory(geocode)
