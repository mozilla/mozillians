.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _api:

===============
Mozillians API
===============

The Mozillians.org API is a REST API that provides detailed information about users and groups in Mozillians.org. This document explains how to use the Mozillians.org API to enhance your application.

   .. note::

      All endpoints of the API require authentication. Users can restrict visibility of their personal data by editing their profiles.


Using API Data
--------------

The Mozillians.org API exposes personal data about people who have created profiles on Mozillians.org and who have chosen to expose that data to Mozilla's community or corporation sites. Applications that consume Mozillians.org API data must protect all data retrieved from the Mozillians.org API as specified by `Mozilla's websites privacy policy <http://www.mozilla.org/en-US/privacy/policies/websites/>`_. Furthermore, they must follow these guidelines:

#. **Do not store copies of Mozillians.org data.** If your application requires data served by the Mozillians.org API, it should request that data from the API, and should not make durable/permanent local copies of data retrieved from the API. Any exception to this rule requires a data safety review.
#. **Do not expose Mozillians.org data to an audience it was not intended for.** Mozillians.org data is visible, by default, to vouched members of Mozillians.org. Your application must not expose it to a wider audience unless specifically allowed by per-field privacy level or following a data safety review.
#. **Respect per-field privacy levels.** Certain fields retrieved from the Mozillians.org API may be subject to user-configured privacy levels. These privacy levels may be less restrictive than the default ("public") or more restrictive ("privileged"). *In future releases of the API*, a particular field's privacy level may accompany the field in the API response. Your application must respect and enforce any privacy level present in an API response.

If you believe an application is misusing Mozillians.org API data, please `file a bug <https://bugzilla.mozilla.org/enter_bug.cgi?product=Participation%20Infrastructure&component=Phonebook>`_.

.. toctree::
   :maxdepth: 2

   apiv1/index
   apiv2/index
