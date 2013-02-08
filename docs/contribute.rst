.. This Source Code Form is subject to the terms of the Mozilla Public
.. License, v. 2.0. If a copy of the MPL was not distributed with this
.. file, You can obtain one at http://mozilla.org/MPL/2.0/.

.. _contribute:

=================
How to Contribute
=================

Thank you for your interest in contributing to Mozillians! There are always bugs to file; bugs to fix in code; improvements to be made to the documentation; and more.

The below instructions are for software developers who want to work on Mozillians code.

Git workflow
------------
When you want to start contributing, you should `fork the main Mozillians repository`_ (https://github.com/mozilla/mozillians) on GitHub. Then..

* Clone it to your local machine::

    git clone git@github.com:YOUR_USERNAME/mozillians.git

* (Optional) Set your cloned fork to track upstream changes (changes to the main repository)::

    git remote add --track master upstream git://github.com/mozilla/mozillians

  * And then fetch and merge changes from the upstream branch::

      git fetch upstream
      git merge upstream/master

* (Optional) Set up a branch for a particular set of changes::

    git branch my_branch

  * And then switch to it::

      git checkout my_branch

* Commit changes to the code!

* When you're done, figure out how many commits you've made::

    git log

* Squash all those commits into a single commit that has a `good git commit message`_. (Example assumes you made 4 commits)::

    git rebase -i HEAD~4

* Use the interactive editor that pops up to pick/squash your commits::

    pick 01d1239 [fix bug 893291] Make it go to 11
    squash 32as32p added the library and made some minor changes
    squash 30ame3z build the template
    squash 91pcla8 ugh fix a semicolon bug in that last commit

* Push your changes to your fork::

    git push origin my_branch

* Issue a `pull request`_ on GitHub

* Wait to hear from one of the core developers

If you're asked to change your commit message, you can use these commands::

  git commit --amend
  # -f is doing a force push because you modified the history
  git push -f my-remote topic-branch

If you need more Git expertise, a good resource is the `Git book`_.

Server architecture
-------------------
**Dev**

- *URL:* http://mozillians-dev.allizom.org/
- *Deploy:* Automatic after code merge, if unit tests pass

**Stage**

- *URL:* http://mozillians.allizom.org/
- *Deploy:* Manual (Chief)

**Production**

- *URL:* http://www.mozillians.org/
- *Deploy:* Manual (Chief)

You can check the currently deployed git commit by checking https://www.mozillians.org/media/revision.txt.

Pushing to production
---------------------
In 2013 Mozillians code is released on Thursdays, after QA and developers agree that code is ready to push to production. The list of code scheduled for any particular release is here: https://wiki.mozilla.org/Mozillians#Releases

What to work on
---------------
Mozillians development follows a `schedule`_ and a `roadmap`_ managed by the `Mozillians product and development team`_. Bugs that the team has committed to work on are generally given a *target milestone* and are *assigned* to a developer. Other bugs are fair game; but they're not all aligned with the product's current evolution. So if you are not familiar with the project and its roadmap, you may want to find one of the core team in IRC and ask before working on a particular bug. 

- `All outstanding bugs`_ 
- `Good first bugs`_ 
- `Submit a bug`_ 

.. _Git book: http://git-scm.com/book
.. _good git commit message: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
.. _Mozillians product and development team: https://wiki.mozilla.org/Mozillians#Team
.. _schedule: https://wiki.mozilla.org/Mozillians#Schedule
.. _roadmap: https://wiki.mozilla.org/Mozillians/RoadMap
.. _All outstanding bugs: https://bugzilla.mozilla.org/buglist.cgi?product=Community%20Tools;component=Phonebook;resolution=---;list_id=5645789
.. _Good first bugs: https://bugzilla.mozilla.org/buglist.cgi?cmdtype=runnamed;namedcmd=good_first_mozillians_bugs;list_id=5645998
.. _fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork_select
.. _pull request: https://github.com/YOUR_USERNAME/mozillians/pull/new/master
.. _submit a bug: https://bugzilla.mozilla.org/enter_bug.cgi?alias=&assigned_to=nobody%40mozilla.org&blocked=&bug_file_loc=http%3A%2F%2F&bug_severity=normal&bug_status=NEW&cc=hoosteeno%40mozilla.com&cc=williamr%40mozilla.com&comment=&component=Phonebook&contenttypeentry=&contenttypemethod=autodetect&contenttypeselection=text%2Fplain&data=&defined_groups=1&dependson=&description=&flag_type-325=X&flag_type-37=X&flag_type-4=X&flag_type-607=X&flag_type-781=X&flag_type-787=X&flag_type-791=X&flag_type-800=X&form_name=enter_bug&keywords=&maketemplate=Remember%20values%20as%20bookmarkable%20template&op_sys=All&priority=--&product=Community%20Tools&qa_contact=&rep_platform=All&requestee_type-325=&requestee_type-4=&requestee_type-607=&requestee_type-781=&requestee_type-787=&requestee_type-791=&requestee_type-800=&short_desc=&status_whiteboard=&target_milestone=---&version=other
