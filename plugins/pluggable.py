"""
Provides a basic framework for working with plugins.

A "plugin" can either be a subclass of the Plugin abstract class provided in
this module, or it can be any other object (including an entire module) that
adheres to the plugin design contract.

A plugin must have:
    * a name attribute
    * methods or functions for loading and unloading the plugin
    * a method or function for running the plugin

Most of the special sauce for plugins comes from the PluginManager class.
PluginManagers mediate the loading, unloading, and running of plugins while
providing event hooks for extended functionality.

This module also provides a few common plugin discovery functions.

Example:
    # The finder will look in the current directory under a sibling "plugins"
    # folder for any plugins:

    my_plugins = in_plugins_dir(__file__)

    # Alternatively, if you have a specific module or package where you
    # define plugins, use this pattern to load any plugins in that module:

    import plugins_module
    my plugins = in_module(plugins_module)

"""
import abc
import os
import importlib
import importlib.util
import inspect
import pkgutil
from pathlib import Path
from functools import wraps

from typing import Callable, Iterable, List, Optional, Iterable, Tuple, Dict

from event_system import events
from python_utils.inspections import membership


__all__ = ["Plugin", "PluginManager", "in_dir", "in_module", "in_plugins_dir",
           "in_package", "finder_callback"]


# type alias -- a function that returns a list of plugins
Finder = Callable[..., Iterable["Plugin"]]


class AbstractAttribute:
    """An abstract class attribute.

    Use this in an abstract base class when an attribute MUST be overridden by
    subclasses, and is not intended to be used as a property.
    """

    __isabstractmethod__ = True

    def __init__(self, doc: str=""):
        self.__doc__ = doc

    def __get__(self, obj, cls):
        return self


class Plugin(metaclass=abc.ABCMeta):
    """Defines the design contract for plugin objects.

    Each plugin must include a name attribute and functions for loading,
    unloading, and running the plugin.

    The load and unload functions must accept a plugin-manager object as
    their only argument.

    Plugins can either be subclassed from this abstract
    class, or made from scratch, so long as they follow this design contract.

    Attributes:
        name (str): A mandatory attribute of every plugin class.

        order (Any): An optional value that can be used to sort the plugin
            if ordering is important.

    """

    name = AbstractAttribute("The unique name of your plugin")

    #: An optional value that can be used to sort the plugin if ordering is
    #: important.
    order: int

    @abc.abstractmethod
    def load(self, manager):
        """Loads the plugin.
        Args:
            manager (PluginManager)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def unload(self, manager):
        """Un-loads the plugin.
        Args:
            manager (PluginManager)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def run(self, *args, **kwargs):
        """Runs the plugin."""
        raise NotImplementedError

    @staticmethod
    def is_plugin(obj):
        """True if the given object fits the plugin design contract.

        Args:
            obj (callable)
        """
        try:
            return (
                # type(obj) is not type  # prevents plugin classes from being plugins
                obj is not Plugin
                and all(callable(x) for x in (obj.load, obj.run, obj.unload))
                and obj.name is not None
            )
        except AttributeError:
            return False

    def __repr__(self):
        """Code representation of the Plugin:
        <Plugin "name" at 0x0000>
        """
        return "<{classname} \"{plugin_name}\" at {hex_id}>".format(
            classname=type(self).__name__,
            plugin_name=self.name,
            hex_id=hex(id(self))
        )

def make_plugin(
    runner: Callable,
    loader: Optional[Callable]=None,
    unloader: Optional[Callable]=None,
    name: Optional[str]=None,
    order: Optional[int]=None
    ) -> Plugin:
    """Factory: make a Plugin instance with default behavior.

    This is useful to make a plugin that doesn't need complex behavior or
    management.
    """
    name_ = name
    order_ = order

    class _Plugin(Plugin):

        name = name_ or runner.__name__

        if order_:
            order = order_

        def load(self, manager):
            if loader is not None:
                loader(manager)

        def unload(self, manager):
            if unloader is not None:
                unloader(manager)

        def run(self, *args, **kwargs):
            return runner(*args, **kwargs)

    return _Plugin()

class PluginManager:
    """Provides a framework for storing, loading, and running plugins.

    This class also provides event hooks for observing plugin activity.
    """

    #: emits right before a plugin is loaded via the manager.
    plugin_about_to_load = events.EventHook("plugin about to load")

    #: emits immediately after a plugin loads successfully via the manager.
    plugin_loaded = events.EventHook("plugin loaded")

    #: emits immediately after a plugin unloads successfully via the manager.
    plugin_about_to_unload = events.EventHook("plugin about to unload")

    #: emits right before a plugin unloads via the manager.
    plugin_unloaded = events.EventHook("plugin unloaded")

    #: emits when a plugin's load operation raises an exception.
    plugin_load_failed = events.EventHook("plugin load failed")

    #: emits when a plugin's unload action raises an exception.
    plugin_unload_failed = events.EventHook("plugin unload failed")

    #: emits just before a plugin is run.
    plugin_about_to_run = events.EventHook("plugin about to run")

    #: emits when a plugin's execution raises an exception.
    plugin_run_completed = events.EventHook("plugin run")

    #: emits when a plugin's execution raises an exception.
    plugin_run_failed = events.EventHook("plugin run failed")

    def __init__(
        self,
        plugins: Optional[Iterable]=None,
    ):
        """
        Args:
            plugins (iterable): A collection of plugin objects to immediately
                load into this manager when it is instantiated.
            finder (callable): A function that returns a list of plugins to
                load into this manager when it is instantiated.
        """
        self.plugins = dict()
        if plugins:
            self.load_plugins(plugins)

    def load_plugin(self, plugin):
        """Loads the given plugin.

        Raises:
            PluginAlreadyLoaded: if a plugin with the same name is already in
                the plugin manager.
            PluginLoadError: if the plugin's `load()` method fails.

        Returns:
            The returned value for the plugin's `load()` method.

        Args:
            plugin (Plugin)
        """

        self.plugin_about_to_load.emit(plugin)

        if plugin.name in self.plugins:
            raise PluginAlreadyLoaded(
                f"Plugin \"{plugin.name}\" already loaded!"
            )

        try:
            load_return = plugin.load(self)
        except Exception as e:
            self.plugin_load_failed.emit(plugin, e)
            raise PluginLoadError(
                f"Failed to load plugin {plugin.name}"
            ) from e
        else:
            self.plugins[plugin.name] = plugin
            self.plugin_loaded.emit(plugin)
            return load_return

    def load_plugins(self, plugins):
        """Loads several plugins.
        Args:
            plugins (iterable): Any collection of Plugin objects.
        """
        return [self.load_plugin(plugin) for plugin in plugins]

    @property
    def sorted_plugins(self):
        """Returns a sorted version of the manager's plugin dict.

        If no custom key callable is provided, the "order" attribute of the
        plugins will be used.  Any plugins without an "order" attribute will be
        placed at the end of the list.

        Args:
            key (callable): Any callable that accepts a Plugin object and
                returns a sortable value.
        """
        return dict(sorted(self.plugins.items(), key=_plugin_order))

    def unload_plugin(self, plugin):
        """Unloads the plugin from the manager.

        Args:
            plugin (Plugin)

        Raises:
            PluginNotLoaded: If a plugin with the given name does not exist in
                this manager.
            PluginUnloadError: If the plugin's `unload` method fails.
        """
        self.plugin_about_to_unload(plugin)
        if plugin.name not in self.plugins:
            raise PluginNotLoaded(
                f"Can't unload the plugin, it has not been loaded: {plugin.name}"
            )
        try:
            unload_return = plugin.unload(self)
        except Exception as e:
            self.plugin_unload_failed.emit(plugin, e)
            raise PluginUnloadError(
                f"Failed to unload plugin {plugin.name}"
            ) from e
        else:
            self.plugins.pop(plugin.name)
            self.plugin_unloaded.emit(plugin)
            return unload_return

    def unload_plugin_by_name(self, plugin_name):
        """Unloads a plugin by name.

        Args:
            plugin_name (str)

        Raises:
            PluginNotLoaded: If a plugin with the given name does not exist in
                this manager.
            PluginUnloadError: If the plugin's `unload` method fails.
        """
        return self.unload_plugin(self.plugins[plugin_name])

    def unload_all_plugins(self):
        """Unloads all plugins."""
        for plugin in list(self.plugins.values()):
            self.unload_plugin(plugin)

    def run_plugin(self, plugin: Plugin, *args, **kwargs):
        """Runs the plugin's `run` method.

        Args:
            plugin (Plugin)

        Raises:
            PluginNotLoaded if the given plugin cannot be found.
            PluginRunError if the plugin's `run` method fails.

        Returns:
            The return value from the plugin's `run` method.
        """
        self.plugin_about_to_run.emit(plugin)

        if plugin.name not in self.plugins:
            msg = ("The plugin is not loaded and can't be run: {}"
                   "".format(plugin.name))
            exc = PluginNotLoaded(msg)
            self.plugin_run_failed.emit(exc, plugin)
            raise exc

        try:
            return_value = plugin.run(*args, **kwargs)
        except Exception as e:
            raise PluginRunError from e

        self.plugin_run_completed.emit(plugin)
        return return_value

    def run_all_plugins(self, sort=False, *args, **kwargs):
        """Runs all plugins currently loaded in this manager."""
        plugins = self.plugins if not sort else self.sorted_plugins
        for plugin in plugins.values():
            self.run_plugin(plugin, *args, **kwargs)

    def run_plugin_by_name(self, name):
        """Runs the plugin, given its name as a string."""
        return self.run_plugin(self.plugins[name])

    def get_plugin_by_name(self, name):
        """Returns the plugin object, given its name as a string."""
        return self.plugins[name]

    def __getitem__(self, plugin_name):
        return self.plugins[plugin_name]


def _plugin_order(plugin_tuple):
    """Gets a tuple for sorting plugins.

    Plugins with an order attribute will be sorted by that attribute.  Plugins
    without an order attribute will be sorted alphabetically AFTER plugins with
    an order attribute.

    Args:
        plugin_tuple (tuple): A name, plugin pair

    Returns:
        tuple of (int, Any) with the int either a 0 if the plugin has an
            order attribute, or a 1 if it doesn't.  This ensures that plugins
            without an order attribute are sorted at the end of the list
            alphabetically.
    """
    name, plugin = plugin_tuple
    try:
        return (0, plugin.order, name)
    except AttributeError:
        return (1, name)


# ------------------------------------------------------- Plugin Discovery -- #

def _plugin_members(obj):
    """Gets all members that fit the plugin design contract.

    Args:
        obj (Any): a python object that might have plugins as attributes.
            This object must have a __dict__.

    Returns:
        list of objects that fit the Plugin design contract.  If the provided
        object IS a plugin, it is returned in a single-element list.
    """
    if Plugin.is_plugin(obj):
        return [obj]
    return list(membership.members(obj, predicate=Plugin.is_plugin).values())


def in_dir(directory, recursive=False, predicate=None):
    """Discovers all plugins in a given directory's python modules.

    If the modules themselves are organized as plugins, they will be returned.

    Returns:
        list of Plugins
    """
    dir_base_name = os.path.basename(directory)
    modules = list()
    if not recursive:
        for file_ in os.listdir(directory):
            mod_path = os.path.join(directory, file_)
            if (os.path.isfile(mod_path)
                    and not file_.endswith("__init__.py")
                    and file_.endswith(".py")
                    and (not predicate or predicate(file_))):
                modules.append(mod_path)
    else:
        for root, dirs, files in os.walk(directory):
            for file_ in files:
                if (not file_.endswith("__init__.py")
                        and file_.endswith(".py")
                        and (not predicate or predicate(file_))):
                    modules.append(os.path.join(root, file_))

    plugins = list()

    for module in modules:
        mod_name = "__plugin_{directory}_{module}".format(
            directory=dir_base_name,
            module=os.path.splitext(os.path.basename(module))[0]
        )
        spec = importlib.util.spec_from_file_location(mod_name, module)
        if not spec or not spec.loader:
            continue
        module_obj = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module_obj)
        plugins.extend(in_module(module_obj))
    return plugins


def in_module(module_obj):
    """Discovers all plugins in a given module object.

    Typically, these will be Plugin subclasses, which will be instantiated
    with no arguments and returned.

    Args:
        module_obj (module)

    Returns:
        list of instantiated Plugins
    """
    plugins = _plugin_members(module_obj)

    # instantiate any plugin classes
    for i, plugin in enumerate(plugins):
        if inspect.isclass(plugin):
            plugins[i] = plugin()

    return plugins


def in_package(package_obj):
    """Discovers all plugins in an importable python package.
    Args:
        package_obj (module)
    """
    """Discovers all plugins in an importable python package.
    Args:
        package_obj (module)
        namespace (dict, optional): a dictionary to store the imported modules
    """
    found_modules = pkgutil.iter_modules(package_obj.__path__)
    plugins = []
    for _, name, is_pkg in found_modules:
        full_name = "{}.{}".format(package_obj.__name__, name)
        if is_pkg:
            continue
        try:
            module = importlib.import_module(full_name)
            plugins.extend(in_module(module))
        except ImportError:
            pass
    return plugins


def in_plugins_dir(module_file, dir_name="plugins", recursive=False,
                   predicate=None):
    """Discovers all plugins in a sibling directory to the given file.

    The directory does not have to be an importable python package.

    Args:
        module_file (str): The path to a module file, typically provided
            as part of a finder callback. (see example)

        dir_name (str): The name of a sibling directory to the given
            module file.

        recursive (bool): True if you wish to recursively walk down the
            directory hierarchy to discover plugins.

        predicate (callable): A function that takes a file path as a str
            and returns a boolean.


    Example:
        # the package hierarchy looks like this:
        #     my_package /
        #         __init__.py
        #         my_module.py
        #         plugins /
        #             plugin_a.py
        #             plugin_b.py

        # in my_module.py

        class MyPluginManager(pluggable.PluginManager):
            finder = pluggable.finder_callback(
                pluggable.in_plugins_dir, __name__
            )
    """
    dir_ = os.path.split(module_file)[0]
    plugin_dir = os.path.join(dir_, dir_name)
    return in_dir(plugin_dir, recursive=recursive)


def in_env_path(env_variable, recursive=False, predicate=None):
    """Discovers all plugins directories in a PATH-like environment variable

    The directories do not have to be an importable python package.

    Args:
        env_variable (str): The name of an environment variable to read.
        predicate (callable): A function that takes a file path as a str
            and returns a boolean.
    """
    paths = os.environ[env_variable].split(os.pathsep)
    from itertools import chain
    return list(chain(in_dir(path, recursive=recursive, predicate=predicate)
                for path in paths))


def finder_callback(finder: Finder, *args, **kwargs):
    """FACTORY: Makes a callback that will be called with the given arguments.
    Args:
        finder (callable): A function or other callable that returns Plugins
        *args, **kwargs: Any positional or keyword arguments that you want to
            pass in to the callback when it is evaluated.
    """
    @wraps(finder)
    def cbk():
        return finder(*args, **kwargs)
    return cbk


# ------------------------------------------------------ Custom Exceptions -- #

class PluginLookupError(LookupError):
    """Raised when a plugin cannot be found on a manager."""
    pass


class PluginLoadError(Exception):
    """Raised when a plugin's load operation fails."""
    pass


class PluginUnloadError(Exception):
    """Raised when a plugin's unload operation fails."""
    pass


class PluginRunError(LookupError):
    """Raised when a plugin's run operation fails."""
    pass


class PluginAlreadyLoaded(Exception):
    """Raised when a plugin's name is already in use on a manager."""
    pass


class PluginNotLoaded(Exception):
    """Raised when a plugin is not loaded and is called upon."""
    pass
