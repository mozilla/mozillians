.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _apiv1-skills:

==================
Skills
==================

The ``skills`` method of the :doc:`Mozillians API </api/apiv1/index>` returns information about skills.

**Requires Authentication**
    Yes

**Authorized Applications**
    Mozilla Corporation sites

Endpoint
--------

    ``https://mozillians.org/api/v1/skills/``

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

**Get skills, sorted by the number of members having the skill, ordered from most to fewest members, limited to 3 results:**

    Request::

        /api/v1/skills/?app_name=foobar&app_key=12345&order_by=-number_of_members&limit=3

    Response::

        {
            "meta": {
                "limit": 3,
                "next": "/api/v1/skills/?order_by=-number_of_members&app_name=foobar&app_key=12345&limit=3&offset=3",
                "offset": 0,
                "previous": null,
                "total_count": 749
            },
            "objects": 
            [
                {
                    "id": "471",
                    "name": "shaving",
                    "number_of_members": 2159,
                    "resource_uri": "/api/v1/skills/471/",
                    "url": "https://mozillians.org/skill/shaving/"
                },
                {
                    "id": "18",
                    "name": "trimming",
                    "number_of_members": 1513,
                    "resource_uri": "/api/v1/skills/18/",
                    "url": "https://mozillians.org/skill/trimming/"
                },
                {
                    "id": "1907",
                    "name": "growing",
                    "number_of_members": 183,
                    "resource_uri": "/api/v1/skills/1907/",
                    "url": "https://mozillians.org/skill/growing/"
                }
            ]
        }

**Get skills, ordered from most to fewest members and then by skill id**::

    /api/v1/skills/?app_name=foobar&app_key=12345&order_by=-number_of_members,id

**Get skill having id 509**::

    /api/v1/skills/509/?app_name=foobar&app_key=12345
