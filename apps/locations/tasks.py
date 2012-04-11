from celery.decorators import task
from geopy import geocoders
from geopy.geocoders.google import GQueryError

import commonware.log


log = commonware.log.getLogger('m.tasks')


@task
def geocode_address(address_id):
    """Geocodes an address that a user submitted."""
    # HACK: Prevents circular dependancy ImportError.
    from locations.models import Address
    address = Address.objects.get(id=address_id)
    address_string = address.formatted('street', 'city', 'province',
                                       'postal_code', 'country')

    if not address_string.strip():
        point = None
    else:
        geo = geocoders.Google()
        try:
            results = geo.geocode(address_string, exactly_one=False)

            place, (lat, lng) = results[0]
            point = 'POINT(%s %s)' % (lng, lat)
        except GQueryError:
            point = None

    address.point = point
    # Don't queue this task again on save
    address.save(update_point=False)
