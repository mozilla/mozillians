=========
 Testing
=========

Vagrant Box Shortcuts
---------------------

If you are using the :doc:`installation-vagrant` there are a couple of shortcuts
to make your life easier:

- Alias `t`::

  ~4 dj test -x --logging-clear-handlers --with-nicedots'

- Alias `td` ::

  ~$ FORCE_DB=True t --noinput

- Alias `tf`::

  ~$ dj test --logging-clear-handlers --with-nicedots --failed

- Alias `tp`::

  ~$ tp='t --pdb --pdb-failure'


Test Coverage
-------------

You can combine `nose` testing with the `coverage` module to get the
code coverage of the tests. To get a coverage report for the 'users'
package run::

  dj test -x --logging-clear-handlers --with-coverage --cover-package=users

You can request to cover multiple packages in one run::

  dj test -x --logging-clear-handlers --with-coverage --cover-package=users,phonebook


