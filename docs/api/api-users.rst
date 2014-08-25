.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _api-users:

==================
Users
==================

The ``users`` method of the :doc:`Mozillians API <api>` returns user profile information.

**Requires Authentication**
    Yes

**Authorized Applications**
    Community sites (only for determining vouched status), Mozilla Corporation sites

Endpoint
--------

    ``https://mozillians.org/api/v1/users/``

Parameters
----------

    ``app_key``
        *Required* **string** - The application's API key

    ``app_name``
        *Required* **string** - The application's name

    ``is_vouched``
        *Optional* **string (true/false)** - Return only vouched/unvouched users

    ``username``
        *Optional* **string** - Return user with matching username

    ``ircname``
        *Optional* **string** - Return user with matching ircname

    ``email``
        (For Community sites)
            *Required* **string** - Return user with matching email
        (For Mozilla Corporation sites)
            *Optional* **string** - Return user with matching email

    ``country``
        *Optional* **string** - Return users with matching country

    ``region``
        *Optional* **string** - Return users with matching region

    ``city``
        *Optional* **string** - Return users with matching city 

    ``skills``
        *Optional* **string (comma-separated list)** - Return users with matching skills

    ``languages``
        *Optional* **string (comma-separated list)** - Return users with matching languages

    ``accounts``
        *Optional* **string** - Return users with matching external account identifier

    ``groups``
        *Optional* **string (comma-separated list)** - Return users with matching groups

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

**Look up a user by email address:**

    Request::

        /api/v1/users/?app_name=foobar&app_key=12345&email=test@example.com 

    Response *(Community site)*::

        {
            "meta":
            {
                "limit": 20,
                "next": null,
                "offset": 0,
                "previous": null,
                "total_count": 1
            },
            "objects":
            [
                {
                    "email": "test@example.com",
                    "is_vouched": true
                }
            ]
        }

    Response *(Mozilla Corporation site)*::

        {
            "meta": 
            {
                "limit": 20,
                "next": null,
                "offset": 0,
                "previous": null,
                "total_count": 1
            },
            "objects": 
            [
                {
                    "allows_community_sites": true,
                    "allows_mozilla_sites": true,
                    "bio": "I've been a web typographer for 12 years.",
                    "city": "Topeka",
                    "country": "United States",
                    "date_mozillian": "2008-12-01",
                    "date_vouched": 2011-06-25T13:16:40,
                    "email": "test@example.com",
                    "full_name": "John Doe",
                    "groups": "[(u'widgets',), (u'chocolate',)]",
                    "id": "42",
                    "ircname": "",
                    "is_vouched": true,
                    "languages": "[(u'hindi',), (u'english',)]",
                    "photo": "https://mozillians.org/media/uploads/userprofile/3c5fcc399-bf2f-6caf-96fb-b40d9a03037269.jpg",
                    "region": "Kansas",
                    "resource_uri": "/api/v1/users/42/",
                    "skills": "[(u'card tricks',), (u'css3',), (u'skydiving instructor',)]",
                    "timezone": "America/Topeka",
                    "url": "https://mozillians.allizom.org/u/john_doe/",
                    "username": "john_doe",
                    "vouched_by": 808,
                    "website": "http://johndozer.geocities.com"
                }
            ]
        }

**Filter API responses:**

    By *country*::

        /api/v1/users/?app_name=foobar&app_key=12345&country=Greece

    By *ircname*::

        /api/v1/users/?app_name=foobar&app_key=12345&ircname=mr_amazing

    By *group* AND *language*::

        /api/v1/users/?app_name=foobar&app_key=12345&groups=beards&languages=french

