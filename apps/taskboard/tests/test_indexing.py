from common.tests import ESTestCase
from taskboard.models import Task
from taskboard.tests import create_and_index_task


class SearchTest(ESTestCase):
    def test_searching_tasks(self):
        """
        Create some tasks, try searching for them with direct matches
        close matches and capitalization errors.

        Montreal is purposefully miscapitalized.
        """
        tasky_task = {
            'contact': self.mozillian.get_profile(),
            'summary': 'Become Tofumatt',
            'instructions': 'Buy ducati move to montreal, buy soy latte,'
                            ' remove mirrors from said ducati for SPEED',
        }

        another_task = {
            'contact': self.mozillian.get_profile(),
            'summary': 'TPS Reports',
            'instructions': 'Did you get the memo about the new TPS reports?'
                            " Yeah i'm going to ask that you start or I"
                            ' will send you to monTreal',
        }

        with create_and_index_task(**tasky_task):
            self.assertTrue(
                (Task.search('soy latte')[0] ==
                    Task.objects.get(summary=tasky_task['summary'])),
                'We should be able to search for part of "instructions"'
            )

            self.assertTrue(
                (Task.search('Become Tofumatt')[0] ==
                    Task.objects.get(summary=tasky_task['summary'])),
                'We should be able to search for part of "instructions"'
            )

            with create_and_index_task(**another_task):
                self.assertTrue(
                    (len(Task.search('Montreal')) >= 2),
                    '`Montreal` should match 2 tasks'
                )

    def test_no_disabled_tasks(self):
        """
        Make a test, make sure it shows up. Make the same test but disabled,
        make sure it doesn't show up.
        """
        disabled_task = {
            'contact': self.mozillian.get_profile(),
            'summary': 'Learn to Fly',
            'instructions': 'You know, just learn to fly.',
        }
        with create_and_index_task(**disabled_task):
            self.assertTrue(
                (Task.search('learn to fly')[0] ==
                    Task.objects.get(summary=disabled_task['summary'])),
                'Enabled task should show up'
            )

        disabled_task.update(disabled=True)
        with create_and_index_task(**disabled_task):
            self.assertFalse(
                Task.search('learn to fly'),
                'Disabled task should not show up'
            )
