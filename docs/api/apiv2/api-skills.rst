.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _apiv2-skills:

==================
Skills
==================

The ``skills`` method of the :doc:`Mozillians API </api/apiv2/index>` returns information about skills.

Endpoint
--------

    ``https://mozillians.org/api/v2/skills/``

Parameters
----------

    ``api-key``
        *Required* **string** - The application's API key

    ``page``
        *Optional* **integer** - Return results contained in specific page

    ``name``
        *Optional* **string** - Return results matching the given name


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

**Get skills:**

    Request::

        /api/v2/skills?api-key=12345

    Response::

      {
          "count": 7011,
          "next": "https://mozillians.org/api/v2/skills/?page=2",
          "previous": null,
          "results": [
              {
                  "id": 6124,
                  "url": "https://mozillians.org/en-US/skill/nodejs-3/",
                  "name": ".nodejs",
                  "member_count": 10,
                  "_url": "https://mozillians.org/api/v2/skills/6124/"
              },
              {
                  "id": 6162,
                  "url": "https://mozillians.org/en-US/skill/php-3/",
                  "name": ".php",
                  "member_count": 91,
                  "_url": "https://mozillians.org/api/v2/skills/6162/"
              },
              {
                  "id": 5295,
                  "url": "https://mozillians.org/en-US/skill/project-management-marketing-fundamentals-logistic/",
                  "name": ".project management .marketing fundamentals .logis",
                  "member_count": 28,
                  "_url": "https://mozillians.org/api/v2/skills/5295/"
              },
              {
                  "id": 5415,
                  "url": "https://mozillians.org/en-US/skill/0654598641/",
                  "name": "0654598641",
                  "member_count": 1,
                  "_url": "https://mozillians.org/api/v2/skills/5415/"
              }
          ]
      }


**Get details for skill having id 509**::

    /api/v2/skills/509/?api-key=12345
