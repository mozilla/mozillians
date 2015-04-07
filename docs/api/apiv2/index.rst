.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _api_v2:

======
API v2
======

Getting an API Key
------------------

With API v2 we created a dedicated API management page for all API needs. You can review, create and delete your API v2 keys by accessing this page.

* Visit your `edit profile page <https://mozillians.org/user/edit/>`_.
* Navigate to ``Services > Developers > Manage API keys`` or click `here <https://mozillians.org/apikeys>`_.

By default, vouched users are able to automatically get an API key with a ``PUBLIC`` access level. In order to get a key with elevated permissions
you'll have to file a `bug <https://bugzilla.mozilla.org/enter_bug.cgi?product=Participation%20Infrastructure&component=API%20Requests>`_.

Privacy
--------
API v2 is designed with users privacy in mind first. Each API key has a privacy level assigned to it. In order for the API consumer to access a ``user/group/skill`` detail,
the fields privacy level should be greater or equal to the fields privacy value. Else the field value in the response is empty.

Authentication
--------------
API consumers should either provide the api key as a get parameter ``api-key`` or as an HTTP header ``X-API-KEY``.

API Methods
-----------

.. toctree::
   :maxdepth: 2

   api-users
   api-groups
   api-skills
