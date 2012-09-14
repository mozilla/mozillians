=================
Invitation System
=================

Mozillians has an inivitation system that let's vouched users invite others to
join Mozillians.  These users who join are automatically vouched.


Inviting en-masse
-----------------

Let's say you have a large list of contributors to invite to your phonebook,
well we thought of that.

You can format a file (``myfriends.txt``) with one email address per line::

    bob@thebobcats.com
    juno@reactor.org
    diane@hunters.org

And feed it on the admin node like so::

    ./manage.py cron invite myfriends.txt

And voila!  Invitations will be mailed to your friends.

This creates one :py:class:`~phonebook.models.Invite` and sets the
:py:attr:`~phonebook.models.Invite.receiver` to ``ZUUL``.  This also sends an
invitation email to each recipient.
