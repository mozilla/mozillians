.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _apiv2-groups:

==================
Groups
==================

The ``groups`` method of the :doc:`Mozillians API </api/apiv2/index>` returns information about groups.

Endpoint
--------

    ``https://mozillians.org/api/v2/groups/``

Parameters
----------

    ``api-key``
        *Required* **string** - The application's API key

    ``name``
        *Optional* **string** - Return results matching given name

    ``curator``
        *Optional* **integer** - Return results matching given mozillians id

    ``functional_area``
        *Optional* **True/False** - Return results containing only groups that are functional areas

    ``members_can_leave``
        *Optional* **True/False** - Return results containing groups with ``members_can_leave`` policy

    ``accepting_new_members``
        *Optional* **True/False** - Return results containing only groups with ``accepting_new_members`` policy

    ``page``
        *Optional* **integer** - Return results contained in specific page


Return Codes
------------

    ====  ===========
    Code  Description
    ====  ===========
    200:  OK Success!
    403:  Wrong api-key or api-key not activated OR application not authorized
    ====  ===========

Examples
--------

**Get groups:**

    Request::

        /api/v2/groups?api-key=12345

    Response::

      {
            "count": 1628,
            "next": "https://mozillians.org/api/v2/groups/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 262,
                    "url": "https://mozillians.org/en-US/group/airmozilla/",
                    "name": "air mozilla",
                    "member_count": 17,
                    "_url": "https://mozillians.org/api/v2/groups/262/"
                },
                {
                    "id": 12520,
                    "url": "https://mozillians.org/en-US/group/air-mozilla-contributors/",
                    "name": "air mozilla contributors",
                    "member_count": 11,
                    "_url": "https://mozillians.org/api/v2/groups/12520/"
                },
                {
                    "id": 11427,
                    "url": "https://mozillians.org/en-US/group/alumni/",
                    "name": "alumni",
                    "member_count": 34,
                    "_url": "https://mozillians.org/api/v2/groups/11427/"
                },
                {
                    "id": 12400,
                    "url": "https://mozillians.org/en-US/group/amara/",
                    "name": "amara",
                    "member_count": 1,
                    "_url": "https://mozillians.org/api/v2/groups/12400/"
                }
            ]
        }


**Get details for group having id 509**::

    /api/v2/groups/509/?api-key=12345
