Basket Client
-------------

This is a client for Mozilla's email subscription service,
basket_. Basket is not a real subscription service, but it talks to a
real one and we don't really care who/what it is.

There are four API methods: subscribe, unsubscribe, user, and
update_user. View the basket documentation_ for details.

.. _basket: https://github.com/mozilla/basket

Usage
-----

Are you looking to integrate this on a site for email subscriptions?
All you need to do is:

    import basket
    
    basket.subscribe('<email>', '<newsletter>', <kwargs>)

You can pass additional fields as keyword arguments, such as format
and country. For a list of available fields and newsletters, see the
basket documentation_.

.. _documentation: https://github.com/mozilla/basket/tree/master/apps/news

Are you checking to see if a user was successfully subscribed? You can
use the `debug-user` method like so:

    import basket
    
    basket.debug_user('<email>', '<supertoken>')

And it return full details about the user. <supertoken> is a special
token that grants you admin access to the data. Check with James Long
(jlong@mozilla.com) to get it.

Settings
========

BASKET_URL
  URL to basket server, e.g. `https://basket.mozilla.com`
