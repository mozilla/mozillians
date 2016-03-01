.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _apiv1-groups:

==================
Groups
==================

The ``groups`` method of the :doc:`Mozillians API </api/apiv1/index>` returns information about groups.

**Requires Authentication**
    Yes

**Authorized Applications**
    Mozilla Corporation sites

Endpoint
--------

    ``https://mozillians.org/api/v1/groups/``

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

**Get groups, sorted by the number of members in the group, ordered from most to fewest members, limited to 3 results:**

    Request::

        /api/v1/groups/?app_name=foobar&app_key=12345&order_by=-number_of_members&limit=3

    Response::

        {
            "meta": {
                "limit": 3,
                "next": "/api/v1/groups/?order_by=-number_of_members&app_name=foobar&app_key=12345&limit=3&offset=3",
                "offset": 0,
                "previous": null,
                "total_count": 749
            },
            "objects":
            [
                {
                    "id": "471",
                    "name": "do_not_have_beards",
                    "number_of_members": 2159,
                    "resource_uri": "/api/v1/groups/471/",
                    "url": "https://mozillians.org/group/do_not_have_beards/"
                },
                {
                    "id": "18",
                    "name": "have_beards",
                    "number_of_members": 1513,
                    "resource_uri": "/api/v1/groups/18/",
                    "url": "https://mozillians.org/group/have_beards/"
                },
                {
                    "id": "1907",
                    "name": "sometimes_beards",
                    "number_of_members": 183,
                    "resource_uri": "/api/v1/groups/1907/",
                    "url": "https://mozillians.org/group/sometimes_beards/"
                }
            ]
        }

**Get groups, ordered from most to fewest members and then by group name**::

    /api/v1/groups/?app_name=foobar&app_key=12345&order_by=-number_of_members,name

**Get group having id 509**::

    /api/v1/groups/509/?app_name=foobar&app_key=12345
