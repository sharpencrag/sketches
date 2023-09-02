"""Base class definitions for action system"""
from __future__ import annotations
from abc import ABCMeta, abstractmethod
import contextlib
from typing import Callable, Any, Union, List, Dict, Optional
from enum import Enum, auto

from event_system import events

__all__ = ["Action", "ActionGroup", "ActionStatus", "make_action"]


class ActionStatus(Enum):
    """Status codes for actions.

    Return these values from an action's `callback` method to indicate
    how the action was resolved.  If the value is CANCEL, the entire action
    queue (children and sibling Actions) will be stopped. If the value is SKIP,
    the action and its children will be skipped, but sibling actions will
    continue to run.

    ERROR and SUCCESS are also available, but are not handled in any special
    way by the action system.

    Returning any other value from `callback` is considered a success.
    """
    CANCEL = auto()
    SKIP = auto()
    ERROR = auto()
    SUCCESS = auto()


class Action(metaclass=ABCMeta):
    """Base class for actions.

    Actions can be organized hierarchically, with each action having zero or more
    child actions.

    Actions can also have zero or more accessory actions, which are logically
    grouped but can be run independently of the action (think: a "save" with an
    accessory "save as").

    Accessory actions are mostly useful in a GUI context.

    By default, running an action also runs its children but not its accessories.

    The Action class provides two additional organizational tools:
        - a primary tag
        - a list of secondary tags.

    Tags can be used for grouping, visual organization, and searching.

    When subclassing Action, you must override the `run` method, which is the
    primary functionality of the action.

    You can also override the `configure` method, which is called after the
    action is initialized.  This is useful for setting up the action's initial
    state, setting up callbacks, connecting events, etc.  Any additional
    arguments passed to the action's constructor will be passed to `configure`.

    Finally, you can override the "is_valid" method, which can be used to
    dynamically determine whether a given action is valid at runtime.
    """

    started = events.EventHook()
    skipped = events.EventHook()
    completed = events.EventHook()
    failed = events.EventHook()
    cancelled = events.EventHook()

    def __init__(
        self,
        *args,
        name: str,
        child_actions: Optional[List[Action]]=None,
        accessory_actions: Optional[List[Action]]=None,
        primary_tag: Optional[Any]=None,
        secondary_tags: Optional[List[Any]]=None,
        enabled: bool=True,
        valid: bool=True,
        **kwargs
    ):
        super(Action, self).__init__()
        self.name = name
        self.payload = None

        # internal caches
        self._enabled = enabled
        self._parent = None
        self._valid = valid

        # accessory and child actions
        self.accessory_actions = list()
        if accessory_actions:
            self.add_accessory_actions(accessory_actions)
        self.child_actions = list()
        if child_actions:
            self.add_child_actions(child_actions)

        # tagging and search fields
        self.primary_tag = primary_tag
        self.secondary_tags = secondary_tags or list()

        # post-init configuration - this should be customized in subclasses:
        self.configure(*args, **kwargs)

    # INTERNAL INTERFACE

    def __call__(self, *args, **kwargs):
        self.run(*args, **kwargs)

    def __repr__(self):
        return f"<Action \"{self.name}\" at {hex(id(self))}>"

    def __add_actions(self, action_list, actions):
        """add an iterable of actions to a mutable action list"""
        for action in actions:
            self.__add_action(action_list, action)

    def __add_action(self, action_list, action, position=None):
        """add a single action to one of the action lists"""
        position = position or len(action_list)
        if action not in action_list:
            action._parent = self
            action_list.insert(position, action)

    @contextlib.contextmanager
    def __disable_temp(self):
        """Temporarily disable this action."""
        previous_enabled = self._enabled
        self._enabled = False
        yield
        self._enabled = previous_enabled

    # PUBLIC INTERFACES - override at your own risk

    def execute(self, standalone=False):
        """Run this action's callback.

        If standalone is True, only this action will be run, not any children.
        Accessory actions must always be called separately.
        """
        if standalone:
            return self.execute_standalone()
        else:
            return self.execute_with_children()

    def execute_with_children(self):
        """Run this action's callback, as well as any descendants."""

        result = self.execute_standalone()

        if result is ActionStatus.CANCEL:
            for action in self.descendants:
                action.cancelled.emit(action)
            return result

        if result is ActionStatus.SKIP:
            for action in self.descendants:
                action.skipped.emit(action)
            return result

        for action in self.descendants:
            child_status = action.execute_standalone()
            if child_status is ActionStatus.CANCEL:
                break
            elif child_status is ActionStatus.SKIP:
                with self.__disable_temp():
                    continue

        return result

    def execute_standalone(self) -> Union[ActionStatus, None, Any]:
        if not self.enabled:
            self.skipped.emit(self)
            return ActionStatus.SKIP

        self.started.emit(self)

        # run the callback and store the return value
        try:
            result = self.run()
        except Exception as e:
            self.failed.emit(self, e)
            raise
        else:
            if result is ActionStatus.CANCEL:
                self.cancelled.emit(self)
            elif result is ActionStatus.SKIP:
                self.skipped.emit(self)
            else:
                self.payload = result
                self.completed.emit(self, self.payload)
            return result

    def add_child_actions(self, actions):
        """Add an iterable of child actions"""
        self.__add_actions(self.child_actions, actions)

    def add_child_action(self, action, position=None):
        """Add a single child action.

        If a position is provided, the action will be inserted into the list
        rather than appended to the end.
        """
        self.__add_action(self.child_actions, action, position)

    def add_accessory_actions(self, actions):
        """Add an iterable of accessory actions."""
        for action in actions:
            self.add_accessory_action(action)

    def add_accessory_action(self, action, position=None):
        """Add a single accessory action."""
        self.__add_action(self.accessory_actions, action, position)

    @property
    def ancestors(self):
        """Return a list of parents, grandparents, etc."""
        this_parent = self.parent
        if not this_parent:
            return []
        ancestors = [this_parent]
        for ancestor in ancestors:
            parent = ancestor.parent
            if parent:
                ancestors.append(parent)
        return ancestors

    @property
    def descendants(self):
        """Return a list of children, grandchildren, etc."""
        children = list(self.child_actions)
        for child in children:
            children.extend(child.child_actions)
        return children

    @property
    def parent(self):
        """Any action can have exactly one parent in its hierarchy."""
        return self._parent

    @property
    def valid(self):
        """Whether this action is valid.

        If an action is invalid, its children are also invalid.
        """
        if self.is_valid():
            if not self.parent:
                return True
            if self.parent.valid:
                return True
        return False

    @property
    def enabled(self):
        """Whether this action should be run.

        If an action is disabled, its children are also disabled.
        """
        if self._enabled:
            if not self.parent:
                return True
            if self.parent.enabled:
                return True
        return False

    @enabled.setter
    def enabled(self, value):
        """set this action"s enabled state.  Enabling or disabling an action
        will also enable or disable all of its children"""

        self._enabled = value

        for descendant in self.descendants:
            # ONLY use the "private" attribute here to avoid recursion
            descendant._enabled = value

        if value:
            for ancestor in self.ancestors:
                ancestor._enabled = True

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    # RE-IMPLEMENT IN SUBCLASSES

    def configure(self, *args, **kwargs):
        """Subclasses can override to configure the action after initialization."""
        pass

    def is_valid(self):
        """Subclasses can override to provide a dynamic validity check."""
        return self._valid

    @abstractmethod
    def run(self, *args, **kwargs) -> Union[ActionStatus, Any]:
        """Subclasses must provide a run method for this action.

        Return ActionStatus.CANCEL or ActionStatus.SKIP to cancel or skip the
        action and its children.

        If you return ActionStatus.CANCEL, any sibling actions will also be
        cancelled.  (Think, a "cancel" button in a dialog - the assumption is
        that all active actions should be cancelled.)

        The return value of this method will be stored in the `payload` attr
        of the action.
        """
        pass


class ActionGroup(Action):
    """An action that acts as a container for other actions."""
    def run(self):
        pass


def make_action(callback: Callable, name: Optional[str]=None) -> Action:
    """Return an Action instance for the given callback.

    This is useful for making quick actions that don't require customization.
    """
    class _Action(Action):
        def run(self, *args, **kwargs):
            return callback(*args, **kwargs)
    return _Action(name=name or callback.__name__)
