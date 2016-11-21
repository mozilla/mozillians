==================
Basket integration
==================

In order to facilitate mass emailing and subscribing to Mozilla newsletters,
Mozillians.org is integrated with `Basket <https://basket.readthedocs.io/>`_.

How does it work?
-----------------

HTTP API calls
^^^^^^^^^^^^^^

Basket exposes an HTTP API that allows consumers to interact with Mozilla's newsletters.
Specifically we are using `basket-client <https://github.com/mozilla/basket-client>`_
a Python implementation that makes it easier to integrate with django apps.

The Basket endpoints that Mozillians.org is using are the following:

* `Lookup user <https://basket.readthedocs.io/newsletter_api.html#news-lookup-user>`_

  * Retrieve user information based on their email

* `Subscribe user <https://basket.readthedocs.io/newsletter_api.html#news-subscribe>`_

  * Subscribe user to the defined newsletters

* `Unsubscribe user <https://basket.readthedocs.io/newsletter_api.html#news-unsubscribe>`_

  * Unsubscribe user from the defined newsletters

Mozillians.org newsletters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In Mozillians.org we maintain 2 newsletters

* ``mozilla-phone`` for all our vouched users
* ``mozillians-nda`` for all the members of the NDA group

Implementation architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to avoid blocking the user HTTP request/response cycle we are heavily using
celery to make all the Basket API interactions asynchronous. That means that all Basket API calls
are being done in the background and not necessarily in the exact time that an action
triggered the API call.

.. note::
   All Basket API related code is behind `waffle <https://waffle.readthedocs.io/en/v0.11/>`_
   switches. That means that in order to enable Basket integration, ``BASKET_SWITCH_ENABLED``
   should be enabled. Same way you can disable all Basket API calls by disabling this switch.

Our celery tasks are implemented as `chains <http://docs.celeryproject.org/en/latest/userguide/canvas.html#chains>`_
of subtasks. This way we can easily re-use generic chunks of code and abort the chain of tasks in case something
goes wrong. Here are our task definitions.

* ``subscribe_user_to_basket(instance_id, newsletters=[])``

  * Lookup user in Basket
  * Based on the lookup results subscribe user to newsletters defined

* ``unsubscribe_from_basket_task(email, newsletters=[])``

  * Lookup user in Basket
  * Based on the lookup results unsubscribe user from newsletters defined

* ``update_email_in_basket(old_email, new_email)``

  * Lookup user's old email in Basket
  * Based on the lookup results unsubscribe old email from all the mozillians.org newsletters that user is subscribed
  * Subscribe new email to the newsletters defined above

Newsletter policies
^^^^^^^^^^^^^^^^^^^

When a Mozillian:

* becomes a member of the NDA group, we trigger a subscription to ``mozillians-nda``.
* leaves the NDA group, we trigger an unsubscription from ``mozillians-nda``.
* become vouched, we trigger a subscription to ``mozilla-phone``.
* changes their primary email, we trigger an email change in basket. 

Administrative actions
^^^^^^^^^^^^^^^^^^^^^^

In order to allow Mozillians.org admins manage basket subscriptions we expose the following tasks
as admin actions:

* ``subscribe_user_to_basket``
* ``unsubscribe_from_basket_task``

.. note::
   There is no logic implemented behind these admin actions. That means that admins are explicitly
   allowed to subscribe/unsubscribe mozillians even when policies are not met.

Deployment details
^^^^^^^^^^^^^^^^^^^

All three Mozillians.org environments (dev/stage/prod) are Basket enabled. For development purposes,
mozillians-dev and mozillians-stage are pointing to a sandboxed basket instance (basket-dev).
