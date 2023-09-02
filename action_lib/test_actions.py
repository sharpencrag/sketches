import unittest
from unittest import mock

from action_lib.actions import Action, make_action, ActionStatus


class TestAction(unittest.TestCase):

    def test_make_action(self):
        def callback():
            pass
        action = make_action(callback)
        self.assertIsInstance(action, Action)
        self.assertEqual(action.name, 'callback')

    def test_make_action_with_name(self):
        def callback():
            pass
        action = make_action(callback, name='my_action')
        self.assertIsInstance(action, Action)
        self.assertEqual(action.name, 'my_action')

    def test_action_class_initialization(self):
        a = make_action(lambda: None, name='a')
        b = make_action(lambda: None, name='b')
        c = make_action(lambda: None, name='c')
        d = make_action(lambda: None, name='d')
        e = make_action(lambda: None, name='e')
        f = make_action(lambda: None, name='f')

        class A(Action):
            def run(self):
                pass

        action = A(
            name='my_action',
            accessory_actions=[a, b, c],
            child_actions=[d, e, f],
            primary_tag=8,
            secondary_tags=[9, 10, 11],
        )

        self.assertEqual(action.name, 'my_action')
        self.assertEqual(action.accessory_actions, [a, b, c])
        self.assertEqual(action.child_actions, [d, e, f])
        self.assertEqual(a.parent, action)
        self.assertEqual(action.primary_tag, 8)
        self.assertEqual(action.secondary_tags, [9, 10, 11])

    def test_action_config_arg_passthrough(self):
        class A(Action):
            def run(self):
                pass

            @mock.Mock()
            def configure(self_, *args, **kwargs):
                pass

        action = A(1, 2, 3, a=1, b=2, c=3, name='my_action')

        action.configure.assert_called_once_with(1, 2, 3, a=1, b=2, c=3)

class TestActionHierarchy(unittest.TestCase):

    def setUp(self):
        class ParentAction(Action):
            @mock.Mock()
            def run(self):
                pass

        class ChildAction(Action):
            @mock.Mock()
            def run(self):
                pass

        class SiblingAction(Action):
            @mock.Mock()
            def run(self):
                pass

        class GrandchildAction(Action):
            @mock.Mock()
            def run(self):
                pass

        self.grandchild = GrandchildAction(name='grandchild')
        self.child = ChildAction(name='child', child_actions=[self.grandchild])
        self.sibling = SiblingAction(name='sibling')
        self.parent = ParentAction(name='parent', child_actions=[self.child, self.sibling])

    def test_run_standalone(self):
        self.parent.execute_standalone()
        self.parent.run.assert_called_once()
        self.child.run.assert_not_called()
        self.sibling.run.assert_not_called()
        self.grandchild.run.assert_not_called()

    def test_run_with_children(self):
        self.parent.execute_with_children()
        self.parent.run.assert_called_once()
        self.child.run.assert_called_once()
        self.sibling.run.assert_called_once()
        self.grandchild.run.assert_called_once()

    def test_disable_child(self):
        self.child.enabled = False
        self.parent.execute_with_children()
        self.parent.run.assert_called_once()
        self.child.run.assert_not_called()
        self.sibling.run.assert_called_once()
        self.assertFalse(self.grandchild.enabled)
        self.grandchild.run.assert_not_called()

    def test_disable_grandchild_does_not_propagate(self):
        self.grandchild.enabled = False
        self.parent.execute_with_children()
        self.parent.run.assert_called_once()
        self.child.run.assert_called_once()
        self.sibling.run.assert_called_once()
        self.grandchild.run.assert_not_called()

    def test_enable_grandchild_propagates(self):
        self.parent.enabled = False
        self.parent.execute_with_children()
        self.parent.run.assert_not_called()
        self.child.run.assert_not_called()
        self.sibling.run.assert_not_called()
        self.grandchild.run.assert_not_called()

        self.grandchild.enabled = True
        self.assertTrue(self.parent.enabled)
        self.assertTrue(self.child.enabled)
        self.parent.execute_with_children()
        self.parent.run.assert_called_once()
        self.child.run.assert_called_once()
        self.sibling.run.assert_not_called()
        self.grandchild.run.assert_called_once()

    def test_is_valid_child(self):
        self.assertTrue(self.parent.valid)
        self.assertTrue(self.child.valid)
        self.assertTrue(self.sibling.valid)
        self.assertTrue(self.grandchild.valid)

        self.child._valid = False
        self.assertTrue(self.parent.valid)
        self.assertFalse(self.child.valid)
        self.assertTrue(self.sibling.valid)
        self.assertFalse(self.grandchild.valid)

    def test_action_success_event_hooks(self):
        @mock.Mock()
        def on_parent_action_start(action):
            pass

        @mock.Mock()
        def on_parent_action_complete(action):
            pass

        @mock.Mock()
        def on_child_action_start(action):
            pass

        @mock.Mock()
        def on_child_action_complete(action):
            pass

        self.parent.started.connect(on_parent_action_start)
        self.child.started.connect(on_child_action_start)
        self.parent.completed.connect(on_parent_action_complete)
        self.child.completed.connect(on_child_action_complete)

        self.parent.execute()

        on_parent_action_start.assert_called_once_with(self.parent)
        on_parent_action_complete.assert_called_once_with(self.parent, self.parent.run())
        on_child_action_start.assert_called_once_with(self.child)
        on_child_action_complete.assert_called_once_with(self.child, self.child.run())

    def test_action_skip_return_event_hook(self):
        class NewParent(Action):
            def run(self):
                return ActionStatus.SKIP

        @mock.Mock()
        def on_skip(action):
            pass

        @mock.Mock()
        def on_child_skip(action):
            pass

        @mock.Mock()
        def on_complete(action, status):
            pass

        self.parent = NewParent(name='parent', child_actions=[self.child, self.sibling])
        self.parent.completed.connect(on_complete)
        self.parent.skipped.connect(on_skip)
        self.child.skipped.connect(on_child_skip)
        self.parent.execute()

        on_skip.assert_called_once_with(self.parent)
        on_child_skip.assert_called_once_with(self.child)
        on_complete.assert_not_called()
        self.child.run.assert_not_called()

    def test_action_failure_event_hook(self):
        class NewParent(Action):
            def run(self):
                x = 1/0

        @mock.Mock()
        def on_fail(action, exception):
            pass

        @mock.Mock()
        def on_child_skip(action):
            pass

        self.parent = NewParent(name='parent', child_actions=[self.child, self.sibling])
        self.child.skipped.connect(on_child_skip)
        self.parent.failed.connect(on_fail)

        with self.assertRaises(ZeroDivisionError):
            self.parent.execute()

        on_fail.assert_called_once_with(self.parent, mock.ANY)
        self.child.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
