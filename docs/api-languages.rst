.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _api-languages:

==================
Languages
==================

The ``languages`` method of the :doc:`Mozillians API </api>` returns information about languages.

**Requires Authentication**
    Yes

**Authorized Applications**
    Mozilla Corporation sites

Endpoint
--------

    ``https://mozillians.org/api/v1/languages/``

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

**Get languages, sorted by the number of members who speak the language, ordered from most to fewest members, limited to 3 results:**

    Request::

        /api/v1/languages/?app_name=foobar&app_key=12345&order_by=-number_of_members&limit=3

    Response::

        {
            "meta": {
                "limit": 3,
                "next": "/api/v1/languages/?order_by=-number_of_members&app_name=foobar&app_key=12345&limit=3&offset=3",
                "offset": 0,
                "previous": null,
                "total_count": 749
            },
            "objects": 
            [
                {
                    "id": "471",
                    "name": "english",
                    "number_of_members": 2159,
                    "resource_uri": "/api/v1/languages/471/",
                    "url": "https://mozillians.org/language/english/"
                },
                {
                    "id": "18",
                    "name": "french",
                    "number_of_members": 1513,
                    "resource_uri": "/api/v1/languages/18/",
                    "url": "https://mozillians.org/language/french/"
                },
                {
                    "id": "1907",
                    "name": "vulcan",
                    "number_of_members": 183,
                    "resource_uri": "/api/v1/languages/1907/",
                    "url": "https://mozillians.org/language/vulcan/"
                }
            ]
        }

**Get languages, ordered from most to fewest members and then by language name**::

    /api/v1/languages/?app_name=foobar&app_key=12345&order_by=-number_of_members,name

**Get language having id 509**::

    /api/v1/languages/509/?app_name=foobar&app_key=12345
