=================
Invitation System
=================

Mozillians has an inivitation system that let's vouched users invite others to
join Mozillians.  These users who join are automatically vouched.


The Model
---------

The invite model stores the following:

.. py:attribute:: Invite.inviter

   This is the ``uid`` of the vouched Mozillian who is doing the inviting.

.. py:attribute:: Invite.recipient

   This is the email address of where the invitation is sent.

.. py:attribute:: Invite.code

   This is the randomly generated invite code.  This code is used in the
   :ref:`registration` system.

.. py:attribute:: Invite.redeemer

   This is the ``uid`` of the newly created user who has redeemed the invite.

.. py:attribute:: Invite.redeemed

   This is the date the invite was redeemed.

.. py:attribute:: Invite.created

   This is the date the invite was created.
