import time
import sys
import traceback
from functools import wraps
from itertools import count

# TODO: I think the exception handling is broken in py3, and there isn't test coverage


COUNTER = count()


class BenchmarkSuite_Meta(type):
    """Very basic metaclass that adds a unique _order attribute to a class.
    This allows BenchmarkSuite classes and subclasses to be ordered based on
    their position in source code."""
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls._order = COUNTER.__next__()


class BenchmarkSuite(metaclass=BenchmarkSuite_Meta):
    """Organizes a collection of benchmarks into a single, runnable suite.
    Each suite has optional set-up and tear-down methods both for the entire
    suite, and for each individual benchmark. By default, there are no
    mechanisms in this module to run a benchmark outside of a suite, but the
    invidividual pieces exist for easy expansion."""

    def set_up_suite(self):
        """Runs once per suite, before any benchmarks are run"""
        pass

    def tear_down_suite(self):
        """Runs once per suite, after all benchmarks for the suite are run"""
        pass

    def set_up_benchmark(self):
        """Runs once per benchmark, before the benchmark-decorated function"""
        pass

    def tear_down_benchmark(self):
        """Runs once per benchmark, after the benchmark-decorated function"""
        pass

    @property
    def benchmarks(self):
        """Get all methods on an instance of this class that have been decorated
        to include the "is_benchmark" attribute"""
        bench_methods = [
            mthd for mthd in self.__class__.__dict__.values()
            if hasattr(mthd, "is_benchmark")
            and mthd.is_benchmark is True
            and mthd.condition is True
        ]
        return sorted(bench_methods, key=lambda x: x.order)

    def run(self, reporter=None):
        """Run all of the benchmarks in this suite.  "reporter" is a callable
        that takes a BenchmarkSuiteHandler object and produces some kind of
        useful output"""
        suite_reporter = reporter or DefaultSuiteReporter()
        suite_handler = BenchmarkSuiteHandler(
            self.set_up_suite, self.tear_down_suite, self
        )

        with suite_handler:
            for benchmark in self.benchmarks:
                benchmark_handler = BenchmarkHandler(
                    suite_handler, self.set_up_benchmark,
                    self.tear_down_benchmark, benchmark
                )
                with benchmark_handler:
                    benchmark(self)

        suite_reporter(suite_handler)


def benchmark(iterations=1, only_run_if=True):
    """Decorates a function to add an attribute flagging it as a benchmark and
    adding a unique "order" id that makes a benchmark run in the order it is
    defined in a module.

    This decorator also allows you to specify an iteration count for extremely
    fast benchmark operations or testing of caching mechanisms that require
    multiple runs of a function to demonstrate savings.

    Finally, a condition attribute is also included that can be used at runtime
    to exclude a function from running.  For instance, to make a benchmark that
    only runs when executed from a console:

    @benchmark(only_run_if=(__name__=="__main__"))
    def my_function(self):
        ...

    """
    def wrapped_outer(func):
        @wraps(func)
        def wrapped_inner(*args, **kwargs):
            for _ in range(iterations):
                ret_value = func(*args, **kwargs)
            return ret_value
        wrapped_inner.is_benchmark = True
        wrapped_inner.order = COUNTER.__next__()
        wrapped_inner.condition = only_run_if
        wrapped_inner.iterations = iterations
        return wrapped_inner
    return wrapped_outer


class TimedHandler:
    """Context Manager:
    Given a BenchmarkSuite or a benchmark-decorated function and its associated
    set-up and tear down functions:

    on entry: set up the benchmark or suite, start a timer, and yield this context manager
    on exit: stop the timer and tear down the benchmark or suite

    """

    def __init__(self, set_up, tear_down, target):
        self.target = target
        self.target_set_up = set_up
        self.target_tear_down = tear_down
        self.start_time = None
        self.total_time = None
        self.failed = False
        self.exception = None

    def __enter__(self):
        self.target_set_up()
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.total_time = time.time() - self.start_time
        if exc_type is not None:
            self.failed = True
            self.exception = (exc_type, exc_value, tb)
            self.traceback = traceback.format_exc()
        self.target_tear_down()
        return True


class BenchmarkSuiteHandler(TimedHandler):
    """Context Manager:
    Set up, time, and tear down a set of benchmarks.  This Handler object also
    collects each benchmark as it is run for reporting."""
    def __init__(self, *args):
        super().__init__(*args)
        self.benchmark_results = list()

    def add_result(self, benchmark_handler):
        self.benchmark_results.append(benchmark_handler)
        if self.failed is False and benchmark_handler.failed is True:
            self.failed = True


class BenchmarkHandler(TimedHandler):
    """Context Manager:
    Set up, time, and tear down an individual benchmark.  When this manager
    exits, the results of the benchmark are added to the Suite's handler"""
    def __init__(self, suite_handler, *args):
        super().__init__(*args)
        self.suite_handler = suite_handler

    def __exit__(self, exc_type, exc_value, tb):
        super().__exit__(exc_type, exc_value, tb)
        self.suite_handler.add_result(self)
        return True


class DefaultSuiteReporter:
    """When a BenchmarkSuite is run, it is passed into a "reporter" callable.
    This gives us a lot of flexibility, but in a large number of cases we just
    want easy-to-read, printed results to the console.  This class provides a
    callable instance that does exactly that:

    ****************************************
    Starting MyBenchmarkSuite

         foo_with_bar >> 0.12000 seconds
    bar_with_only_baz >> 0.18000 seconds
      foo_without_bar >> 0.08500 seconds

    Completed MyBenchmarkSuite in 0.38500 seconds
    *****************************************

    when instantiated, a DefaultSuiteReporter can include a "printer" which
    defaults to sys.stdout.write, but can be redirected to any callable

    """
    def __init__(self, printer=None):
        self.printer = printer or sys.stdout.write
        self.width = None
        self.suite_handler = None

    def __call__(self, suite_handler):
        """Given a BenchmarkSuiteHandler object (after benchmarks have been run
        and results collected) pretty-print the results of the benchmarks and
        the suite"""
        if not suite_handler.benchmark_results:
            return

        self.suite_handler = suite_handler
        caller_width = max(
            [len(result.target.__name__) for result in suite_handler.benchmark_results]
        )
        timecode_width = max(
            [len(self.time_format(result.total_time))
             for result in suite_handler.benchmark_results]
        )
        self.width = caller_width + timecode_width
        self.report_suite_started()
        for result in suite_handler.benchmark_results:
            self.report_benchmark(result)
        self.report_suite_completed()

        if not suite_handler.failed:
            return

        self.report_suite_failure_started()
        for result in suite_handler.benchmark_results:
            if result.failed:
                self.report_benchmark_failure(result)
        self.report_suite_failure_completed()

    @staticmethod
    def time_format(time_obj):
        return "{tot_time:3.6f} seconds".format(tot_time=time_obj)

    def report_suite_started(self):
        """Prints:

        *****************************
        Started MyBenchMarkSuite

        """
        self.printer(
            "{star_line}\n"
            "Started {target}\n\n".format(
                star_line=self.star_line(),
                target=self.suite_handler.target.__class__.__name__
            )
        )

    def report_suite_failure_started(self):
        """Prints:

        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
        MyBenchMarkSuite Errors:

        """
        self.printer(
            "{x_line}\n"
            "{target} Errors:\n\n".format(
                x_line=self.x_line(),
                target=self.suite_handler.target.__class__.__name__
            )
        )

    def report_suite_completed(self):
        """Prints:

        Completed MyBenchMarkSuite in 0.00400 seconds
        *****************************

        """
        msg = (
            "\nCompleted {target} in {tot_time}".format(
                target=self.suite_handler.target.__class__.__name__,
                tot_time=self.time_format(self.suite_handler.total_time),
            )
        )
        if self.suite_handler.failed:
            msg += " (WITH ERRORS)\nException tracebacks will be printed below:"
        msg = "{msg}\n{star_line}\n\n".format(msg=msg, star_line=self.star_line())
        self.printer(msg)

    def report_suite_failure_completed(self):
        """Prints:

        XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

        """
        self.printer("{x_line}\n".format(x_line=self.x_line()))

    def report_benchmark(self, benchmark_handler):
        """Prints:

              my_benchmark >> 0.01500 seconds

        (the gap on the left is formatted to align all benchmark results with
        one-another)

        """

        benchmark_name = benchmark_handler.target.__name__
        total_time = benchmark_handler.total_time
        formatted_time = self.time_format(total_time)
        msg = "{gap}{desc} >> {tot_time}".format(
            gap=(" " * self.gap_width(benchmark_name, formatted_time)),
            desc=benchmark_name,
            tot_time=formatted_time
        )
        if benchmark_handler.failed:
            msg += " (WITH ERRORS)"
        self.printer(msg)
        self.printer("\n")

    def report_benchmark_failure(self, benchmark_handler: BenchmarkHandler):
        """Prints:

        Exception caught in my_benchmark:

        """

        benchmark_name = benchmark_handler.target.__name__
        tb = benchmark_handler.traceback
        msg = "Exception caught in {name}:\n{tb}\n".format(name=benchmark_name, tb=tb)
        self.printer(msg)

    def gap_width(self, benchmark_name, formatted_time):
        """determine the necessary left-hand gap to line up all the benchmark
        timing results for a particular benchmark name"""
        return self.width - len(benchmark_name) - len(formatted_time)

    def star_line(self):
        """get a pretty line of stars, exactly the width of the longest line
        in the benchmark report"""
        return "*" * self.width

    def x_line(self):
        """get a pretty line of stars, exactly the width of the longest line
        in the benchmark report"""
        return "X" * self.width


def discover_suites_in_module(module=None):
    """Given a module object, find all BenchmarkSuite class definitions. If no
    module is provided, discover the suites in the current console context"""
    module = module or sys.modules["__main__"]
    suites = [suite for suite in module.__dict__.values()
              if isinstance(suite, type)
              and issubclass(suite, BenchmarkSuite)
              and suite is not BenchmarkSuite]
    return list(sorted(suites, key=lambda x: x._order))


def run_suites_in_module(module=None):
    """Given a module object, find and run all BenchmarkSuites using the
    default reporting and printing procedures.  If no module is provided, use
    the suites defined in the current console context"""
    suites = discover_suites_in_module(module)
    for suite in suites:
        suite().run()
