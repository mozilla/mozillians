.. _registration:

============
Registration
============

Registration happens at ``/register``.  Data is taken from a form and if it
passes validation it will be submitted.

Fields
------
We are collecting the following fields:

* First Name
* Last Name
* Display Name
* IRC nickname
* Bio
* Photo
* Email Address
* Password

Password, Email and Last Name are required items that we need to send to LDAP.

Photos
------

Photos are transformed into JPEG for storage in the LDAP directory.

Validation
----------

We'll try to use as little validation as possible.  First and Last names should
be as flexible as possible to support all variety names:

* Bob Saget
* Madonna
* @ Johnson
* Dr. 8
* 49
* Jane Doe Smith

Are all perfectly valid names that we must support.

Email address, however can be validated.  As can IRC nickname.
