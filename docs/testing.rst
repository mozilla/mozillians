=========
 Testing
=========

Testing Mozillians Code
-----------------------

* To run mozillians.org tests::

  $ ./manage.py test

* If you need a fresh test database::

  $ FORCE_DB=1 ./manage.py test

* To run all tests in a class::

  $ ./manage.py test mozillians.users.tests.test_models:UserProfileTests

* If you want to run a single test::

  $ ./manage.py test mozillians.users.tests.test_models:UserProfileTests.test_get_attribute_with_public_level

  to run only `test_get_attribute_with_public_level` test from the `UserProfileTests` class in the `mozillians/users/tests/test_models.py` test file.


Test Coverage
-------------

You can combine `nose` testing with the `coverage` module to get the
code coverage of the tests. To get a coverage report for the 'users'
package run::

  $ coverage run --omit='*migrations*' manage.py test --noinput
  $ coverage xml --omit='*migrations*' $(find mozillians -name '*.py')

Then visit `htmlcov/index.html` to get the coverage results.


Test Cases for NDA renewal feature
----------------------------------

**Verify that the inviter, who is also a group curator is able to renew a user membership 2 weeks before it expires**
    **Preconditions:**
        #. Create a closed group with terms in mozillians.org
        #. Set the membership to expire after several days (>14)
        #. Login as group curator and invite a mozillian to the closed group
        #. Login as the mozillian who was invited by curator and accept the invitation to the group and the terms

            * The mozillian becomes a group member

    **Steps:**
        #. Verify that the group member will receive an email notification 2 weeks before their membership expires
        #. Verify that the inviter will receive an email notification 2 weeks before user's membership expires
        #. Login to mozillians.org as the inviter (and also group curator)
        #. Navigate to group's page
        #. Select “Renewals” option in filter dropdown, then click Filter button
        #. Click "Confirm Request" for user's membership renewal request
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        The user continues to be a member of the group, as the membership was renewed by inviter


**Verify that a group curator is able to renew a user membership 2 weeks before it expires, if the inviter is no longer a curator**
    **Preconditions:**
        #. Create a reviewed group with terms
        #. Set the membership to expire after several days (>14)
        #. Login as group curator and invite a mozillian to the closed group
        #. Login as the mozillian who was invited by curator and accept the invitation to the group and the terms

            * The mozillian becomes a group member

        #. Add a new curator to the group and remove the initial curator (who is also the inviter) from the group curators list
    **Steps:**
        #. Verify that the group member will receive an email notification 2 weeks before their membership expires
        #. Verify that the group curator will receive an email notification 2 weeks before user's membership expires
        #. Verify that the inviter will not receive an email notification 2 weeks before user's membership expires, as he/she is not a group curator anymore
        #. Login to mozillians.org as the group curator
        #. Navigate to group's page
        #. Select “Renewals” option in filter dropdown, then click Filter button
        #. Click "Confirm Request" for user's membership renewal request
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        The user continues to be a member of the group, as the membership was renewed by curator


**Verify the status of a user whose membership to an open group without terms reached expiration date**
    **Preconditions:**
        #. Create an open group
        #. Set the membership to expire after several days (>14)
        #. Have a user who joined the group
    **Steps:**
        #. Login to mozillians.org as the curator of the open group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is no longer displayed in Group members section (it was removed)
    **Expected:**
        The user is not a group member.
        The user will receive an email “Removed from Mozillians group “X””


**Verify the status of a user whose membership to a reviewed group without terms reached expiration date**
    **Preconditions:**
        #. Create a reviewed group with no terms
        #. Set the membership to expire after several days (>14)
        #. Have a user added to the group
    **Steps:**
        #. Verify that the user will receive an email notification when the membership reached the expiration date (“Status changed for Mozillians group “X””)
        #. Login to mozillians.org as the curator of the reviewed group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is no longer displayed in Group members section
        #. Select “Pending Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
        #. Click “Confirm Request” for that user
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        After step 8: The user should receive an email saying “Accepted to Mozillians group “X””
        After step 10: The user is a member of the group again


**Verify the status of a user whose membership to a reviewed group with terms reached expiration date**
    **Preconditions:**
        #. Create a reviewed group with terms
        #. Set the membership to expire after several days (>14)
        #. Have a user added to the group
    **Steps:**
        #. Verify that the user will receive an email notification when the membership reached the expiration date (“Status changed for Mozillians group “X””)
        #. Login to mozillians.org as the curator of the reviewed group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is no longer displayed in Group members section
        #. Select “Pending Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
        #. Click “Confirm Request” for that user
        #. Select “Pending Terms” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        After step 8: The user should receive an email saying “Accepted to Mozillians group “X””
        After step 10: If the user accepts the terms, he/she will be member of the group again


**Verify the status of a user whose membership to a closed group without terms reached expiration date**
    **Preconditions:**
        #. Create a closed group with no terms.
        #. Set the membership to expire after several days (>14).
        #. Have a user added to the group.
    **Steps:**
        #. Verify that the user will receive an email notification when the membership reached the expiration date (“Status changed for Mozillians group “X””)
        #. Login to mozillians.org as the curator of the reviewed group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is no longer displayed in Group members section
        #. Select “Pending Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
        #. Click “Confirm Request” for that user
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        After step 8: The user should receive an email saying “Accepted to Mozillians group “X””
        After step 10: The user is a member of the group again


**Verify the status of a user whose membership to a closed group with terms reached expiration date**
    **Preconditions:**
        #. Create a closed group with terms
        #. Set the membership to expire after several days (>14)
        #. Have a user added to the group
    **Steps:**
        #. Verify that the user will receive an email notification when the membership reached the expiration date (“Status changed for Mozillians group “X””)
        #. Login to mozillians.org as the curator of the closed group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is no longer displayed in Group members section
        #. Select “Pending Members” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
        #. Click “Confirm Request” for that user
        #. Select “Pending Terms” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is displayed in Group members section
    **Expected:**
        After step 8: The user should receive an email saying “Accepted to Mozillians group “X””
        After step 10: If the user accepts the terms, he/she will be member of the group again


**Verify the status of a user whose request to join a group (with membership set to expire) was never accepted by the curator**
    **Precondition:**
        #. Create a reviewed group with no terms
        #. Set the membership to expire in a few days
        #. Have a user who submitted a request to join the group
    **Steps:**
        #. Login to mozillians.org as the curator of the group, when the membership reached the expiration date
        #. Navigate to group page
        #. Select “All” option in filter dropdown, then click Filter button
        #. Verify that the user added in precondition is not displayed in Group members section (the user was removed)
    **Expected:**
        The user is not a member of the group
        The user will receive an email “Removed from Mozillians group “X””
