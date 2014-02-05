=========
 Testing
=========

Test Coverage
-------------

You can combine `nose` testing with the `coverage` module to get the
code coverage of the tests. To get a coverage report for the 'users'
package run::

  dj test -x --logging-clear-handlers --with-coverage --cover-package=users

You can request to cover multiple packages in one run::

  dj test -x --logging-clear-handlers --with-coverage --cover-package=users,phonebook
