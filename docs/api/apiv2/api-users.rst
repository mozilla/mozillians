.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _apiv2-users:

==================
Users
==================

The ``users`` method of the :doc:`Mozillians API </api/apiv2/index>` returns user profile information.

Endpoint
--------

    ``https://mozillians.org/api/v2/users/``

Parameters
----------

    ``api-key``
        *Required* **string** - The application's API key

    ``is_vouched``
        *Optional* **string (True/False)** - Return only vouched/unvouched users

    ``username``
        *Optional* **string** - Return user with matching username

    ``full_name``
        *Optional* **string** - Return user with matching full name

    ``ircname``
        *Optional* **string** - Return user with matching ircname

    ``email``
        *Optional* **string** - Return user with matching primary/alternate email

    ``country``
        *Optional* **string** - Return users with matching country

    ``region``
        *Optional* **string** - Return users with matching region

    ``city``
        *Optional* **string** - Return users with matching city

    ``page``
        *Optional* **integer** - Return results contained in specific page

    ``language``
        *Optional* **string** - Return users speaking language matching language code

    ``group``
        *Optional* **string** - Return users who are members of given group name

    ``skill``
        *Optional* **string** - Return users with skill matching skill name


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

**Filter user by email address:**

    Request::

        /api/v2/users/?api-key=12345&email=test@example.com

    Response::

      {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
              {
                  "username": "test@example.com",
                  "is_vouched": true,
                  "_url": "https://mozillians.org/api/v2/users/1111/"
              }
          ]
      }

**Get details for a user:**

    Request::

        /api/v2/users/1111?api-key=12345

    Response::

      {
          "username": "test@example.com",
          "full_name": {
              "value": "Test Example",
              "privacy": "Public"
          },
          "email": {
              "value": "test@example.com",
              "privacy": "Mozillians"
          },
          "alternate_emails": [
              {
                  "email": "test2@example.com",
                  "privacy": "Mozillians"
              }
          ],
          "bio": {
              "html": "<p>Bio test</p>",
              "value": "Bio test",
              "privacy": "Public"
          },
          "photo": {
              "privacy": "Public",
              "150x150": "https://mozillians.org/media/uploads/sorl-cache/00/f7/00f760770a0bed60d936ee377788888.jpg",
              "500x500": "https://mozillians.org/media/uploads/sorl-cache/00/f7/00f760770a0bed60d936ee377788888.jpg",
              "value": "https://mozillians.org/media/uploads/sorl-cache/00/f7/00f760770a0bed60d936ee377788888.jpg",
              "300x300": "https://mozillians.org/media/uploads/sorl-cache/00/f7/00f760770a0bed60d936ee377788888.jpg"
          },
          "ircname": {
              "value": "testexample",
              "privacy": "Public"
          },
          "date_mozillian": {
              "value": "2012-11-01",
              "privacy": "Public"
          },
          "timezone": {
              "utc_offset": 180,
              "value": "Europe/Athens",
              "privacy": "Public"
          },
          "title": {
              "value": "",
              "privacy": "Public"
          },
          "story_link": {
              "value": "",
              "privacy": "Public"
          },
          "languages": {
              "value": [
                  {
                      "code": "el",
                      "english": "Greek",
                      "native": "Ελληνικά"
                  },
                  {
                      "code": "en",
                      "english": "English",
                      "native": "English"
                  }
              ],
              "privacy": "Public"
          },
          "external_accounts": [],
          "websites": [],
          "tshirt": {
              "privacy": "Privileged",
              "value": 9,
              "english": "Straight-cut Large"
          },
          "is_public": true,
          "is_vouched": true,
          "_url": "/api/v2/users/1111/",
          "url": "https://mozillians.org/en-US/u/testexample/",
          "city": {
              "value": "Buenos Aires",
              "privacy": "Public"
          },
          "region": {
              "value": "Ciudad de Buenos Aires",
              "privacy": "Public"
          },
          "country": {
              "code": "ar",
              "value": "Argentina",
              "privacy": "Public"
          }
      }


**Filter API responses:**

    By *country*::

        /api/v2/users/?api-key=12345&country=Greece

    By *ircname*::

        /api/v2/users/?api-key=12345&ircname=mr_amazing
