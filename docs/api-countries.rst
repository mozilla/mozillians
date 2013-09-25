.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _api-countries:

==================
Countries
==================

The ``countries`` method of the :doc:`Mozillians API </api>` returns information about countries.

**Requires Authentication**
    Yes

**Authorized Applications**
    Mozilla Corporation sites

Endpoint
--------

    ``https://mozillians.org/api/v1/countries/``

Parameters
----------

    ``app_key``
        *Required* **string** - The application's API key

    ``app_name``
        *Required* **string** - The application's name

    ``order_by``
        *Optional* **string** - The attribute to sort responses by, and the order to display them in

    ``limit``
        *Optional* **integer** - Return some number of results **Max: 500, Default: 20**

    ``offset``
        *Optional* **integer** - Skip some number of results **Default: 0**

    ``format``
        *Optional* **string (json/jsonp)** - Format of the response **Default: json**

Return Codes
------------

    ====  ===========
    Code  Description
    ====  ===========
    200:  OK Success!
    401:  Wrong app_name or app_key OR application not activated OR application not authorized 
    ====  ===========

Examples
--------

**Get countries, sorted by the number of Mozillians in the country, ordered from most to fewest Mozillians, limited to 3 results:**

    Request::

        /api/v1/countries/?app_name=foobar&app_key=12345&order_by=-population&limit=3

    Response::

        {
            "meta": {
                "limit": 3,
                "next": "/api/v1/countries/?order_by=-population&app_name=foobar&app_key=12345&limit=3&offset=3",
                "offset": 0,
                "previous": null,
                "total_count": 749
            },
            "objects": 
            [
                {
                    "population": 259,
                    "country": "us",
                    "country_name": "United States"
                },
                {
                    "population": 113,
                    "country": "in",
                    "country_name": "India"
                },
                {
                    "population": 104,
                    "country": "ca",
                    "country_name": "Canada"
                }
            ]
        }

**Get countries, ordered from most to fewest Mozillians, then by country abbreviation**::

    /api/v1/countries/?app_name=foobar&app_key=12345&order_by=-population,country
