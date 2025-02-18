"""
Benchmarks for common micro-optimizations.
"""

import time
from contextlib import contextmanager


class Timer:
    def __init__(self, name: str):
        self.name = name
        self.elapsed = 0

    def __enter__(self):
        self.start = time.time()
        print(f"Starting: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Elapsed time: {time.time() - self.start:.3f}s")
        self.elapsed = time.time() - self.start

    def delta(self, *others: "Timer"):
        sorted_timers = sorted([self, *others], key=lambda x: x.elapsed)
        fastest_timer = sorted_timers[0].name
        fastest_time = sorted_timers[0].elapsed
        for timer in sorted_timers[1:]:
            delta = timer.elapsed - fastest_time
            try:
                print(
                    f"'{fastest_timer}' is faster than '{timer.name}' "
                    f"by: {delta:.3f}s ({delta / fastest_time:.2%})"
                )
            except ZeroDivisionError:
                print(
                    f"'{fastest_timer}' is faster than '{timer.name}' by: {delta:.3f}s"
                )


def list_function_vs_brackets():
    print("Benchmarking list function vs brackets...")

    # Believe it or not, using brackets to create an empty list is faster
    # than calling list(). This is because `list` is an identifier, one that
    # can be reassigned, and so the interpreter has to look up the name in the
    # global scope. Using brackets, on the other hand, is a language construct
    # and doesn't require a lookup.

    with Timer("list function") as a:
        for i in range(5_000_000):
            _ = list()

    with Timer("list brackets") as b:
        for i in range(5_000_000):
            _ = []

    a.delta(b)


class Foo:
    def method(self):
        pass


def remove_dot_method_accessor():
    print("Benchmarking method accessor removal...")

    # In Python 2.X, removing the dot-accessor (localizing a method) was a
    # common micro-optimization.  However it seems like the benefits have been
    # drastically reduced in Python 3.X.

    foo = Foo()

    with Timer("keep dot accessor") as a:
        for _ in range(5_000_000):
            foo.method()

    with Timer("remove dot accessor") as b:
        method = foo.method
        for _ in range(5_000_000):
            method()

    a.delta(b)


import math


def math_ceil_vs_division_trick():
    print("Benchmarking math.ceil vs division trick...")

    # Using math.ceil is slower than using this "division trick" to round up.
    # This is almost entirely because of the overhead of function calls and
    # attribute lookup.

    with Timer("math.ceil") as a:
        for i in range(5_000_000):
            _ = math.ceil(i / 80)

    with Timer("division trick") as b:
        for i in range(5_000_000):
            _ = -(-i // 80)

    a.delta(b)


FOO = "foo"


def localize_global():
    print("Benchmarking namespace localization...")

    # Similar to method accessor removal, localizing a global variable
    # can be a micro-optimization. However, the benefits are exceedingly
    # minimal.

    def null(val):
        pass

    with Timer("look up global") as a:
        for _ in range(5_000_000):
            null(FOO)

    foo = FOO

    with Timer("look up local") as b:
        for _ in range(5_000_000):
            null(foo)

    with Timer("worst case") as c:
        for _ in range(5_000_000):
            foo = FOO
            null(foo)

    a.delta(b, c)


def function_call_overhead():
    print("Benchmarking function call overhead...")

    # Calling a function is not free. There is an overhead associated with
    # both calling and returning from a function.  For code with very large
    # numbers of function calls, this overhead can add up.

    def null(x):
        pass

    def null_many_times(x, n):
        for _ in range(n):
            pass

    with Timer("call function one time") as a:
        _ = null_many_times(0, 5_000_000)

    with Timer("call function many times") as b:
        for i in range(5_000_000):
            _ = null(i)

    a.delta(b)


def class_instantiation_overhead():
    print("Benchmarking class instantiation overhead...")

    # Instantiating a class is not free.  While classes and dataclasses are
    # great for organizing data, for very large numbers of instances, the
    # overhead of instantiating a class can add up.

    # These benchmarks compare class instantiation with and without slots, and
    # dataclass instantiation with and without slots.

    from dataclasses import dataclass

    class Foo:
        def __init__(self, a, b, c):
            self.a = a
            self.b = b
            self.c = c

    class FooSlots:
        __slots__ = ["a", "b", "c"]

        def __init__(self, a, b, c):
            self.a = a
            self.b = b
            self.c = c

    @dataclass
    class Foo2:
        a: int
        b: int
        c: int

    @dataclass(slots=True)
    class Foo2Slots:
        a: int
        b: int
        c: int

    with Timer("class instantiation") as a:
        for i in range(5_000_000):
            _ = Foo(1, 2, 3)

    with Timer("class instantiation (with slots)") as b:
        for i in range(5_000_000):
            _ = FooSlots(1, 2, 3)

    with Timer("dataclass instantiation") as c:
        for i in range(5_000_000):
            _ = Foo2(1, 2, 3)

    with Timer("dataclass instantiation (with slots)") as d:
        for i in range(5_000_000):
            _ = Foo2Slots(1, 2, 3)

    a.delta(b, c, d)


def function_call_overhead_vs_generator():
    print("Benchmarking function call overhead...")

    # This is another way to look at function call overhead.  In one case,
    # we're calling a function many times and appending the result to a list.
    # In the other case, we're calling a function many times and yielding the
    # result.

    # The generator version is faster for a few reasons, including the ability
    # to use a list comprehension to construct the list, which is faster than
    # appending to a list in a for loop.

    def get_x(x):
        return x

    def get_x_many_times(x, n):
        for _ in range(n):
            yield x

    with Timer("call function one time") as a:
        _ = [y for y in get_x_many_times(1, 5_000_000)]

    with Timer("call function many times and append") as b:
        _ = list()
        for i in range(5_000_000):
            _.append(get_x(1))

    with Timer("call function many times, list comp") as c:
        _ = [get_x(1) for _ in range(5_000_000)]

    a.delta(b, c)


def preallocate_many_small_list():
    print("Benchmarking preallocation of many small list...")

    # Every time you append to a list, Python has to re-allocate memory for
    # the list depending on its size.  Pre-allocating a list of known size with
    # empty values and assigning to each position in the list can be faster
    # than appending to a list.

    # This benchmark looks at pre-allocating a very small list to see if there
    # is any benefit.

    with Timer("preallocate") as a:
        _ = [0] * 5
        for i in range(5_000_000):
            for j in range(5):
                _[j] = 1

    with Timer("append") as b:
        _ = [0] * 5
        for i in range(5_000_000):
            for j in range(5):
                _.append(1)

    a.delta(b)


def preallocate_one_large_list():
    print("Benchmarking preallocation of one large list...")

    # This benchmark looks at pre-allocating a very small list to see if there
    # is any benefit.

    with Timer("preallocate") as a:
        _ = [0] * 5_000_000
        for i in range(5_000_000):
            _[i] = 1

    with Timer("append") as b:
        _ = []
        for i in range(5_000_000):
            _.append(1)

    a.delta(b)


def list_comprehension_vs_append_vs_map():
    print("Benchmarking list comprehension vs list append vs map...")

    # List comprehensions and `map` are generally faster than appending to a
    # list in a for loop.

    # `map` is typically a tiny bit faster than list comprehensions, but the
    # difference is extremely minimal, even with many millions of calls.

    def get_x(x):
        return x

    with Timer("list comprehension") as a:
        _ = [get_x(i) for i in range(5_000_000)]

    with Timer("map") as b:
        _ = list(map(get_x, range(5_000_000)))

    with Timer("for loop with append") as c:
        _ = []
        for i in range(5_000_000):
            _.append(get_x(i))

    a.delta(b, c)


def dict_comprehension_vs_setitem():
    print("Benchmarking dict comprehension vs dict.__setitem__...")

    # Dict comprehensions are generally faster than using a for loop with
    # dict.__setitem__ (dict[key] = value).

    with Timer("dict comprehension") as a:
        _ = {i: i for i in range(5_000_000)}

    with Timer("for loop with dict.__setitem__") as b:
        _ = {}
        for i in range(5_000_000):
            _[i] = i

    a.delta(b)


def list_vs_tuple_instantiation_overhead_many_small_sequences():
    print("Benchmarking list vs tuple overhead with many small sequences...")

    # The performance difference between instantiating a list and a tuple is
    # pretty small, but tuples get the edge.

    with Timer("list instantiation") as a:
        for i in range(5_000_000):
            _ = [1, 2, 3]

    with Timer("tuple instantiation") as b:
        for i in range(5_000_000):
            _ = (1, 2, 3)

    a.delta(b)


def list_vs_tuple_instantiation_overhead_one_large_sequence():
    print("Benchmarking list vs tuple overhead with one large sequence...")

    # The performance difference between instantiating a single very large
    # list or tuple is essentially non-existent.

    with Timer("list instantiation") as a:
        _ = [1] * 5_000_000

    with Timer("tuple instantiation") as b:
        _ = (1,) * 5_000_000

    a.delta(b)


def list_vs_tuple_concat_overhead_many_small_sequences():
    print("Benchmarking list vs tuple concat overhead with many small sequences...")

    # Concatenating tuples is significantly faster than concatenating lists,
    # especially with many small sequences.

    with Timer("list concatenation") as a:
        for i in range(5_000_000):
            _ = [1] + [2] + [3]

    with Timer("tuple concatenation") as b:
        for i in range(5_000_000):
            _ = (1,) + (2,) + (3,)

    a.delta(b)


def list_vs_tuple_concat_overhead_one_large_sequence():
    print("Benchmarking list vs tuple concat overhead with one large sequence...")

    # If you're concatenating a few large sequences, the performance difference
    # between lists and tuples is negligible.

    a = [1] * 500_000
    b = [2] * 500_000
    c = [3] * 500_000
    with Timer("list concatenation") as timer_a:
        _ = a + b + c

    a = (1,) * 500_000
    b = (2,) * 500_000
    c = (3,) * 500_000
    with Timer("tuple concatenation") as timer_b:
        _ = a + b + c

    timer_a.delta(timer_b)


def list_vs_tuple_extend_append_overhead_many_small_sequences():
    print("Benchmarking list extend/append & tuple concat with many small sequences...")

    # Extending a list is faster than appending to a list, but both are slower
    # than concatenating tuples, even though tuples are immutable and require
    # memory copying.

    with Timer("list extend") as a:
        for i in range(1_000_000):
            [1].extend([2, 3, 4, 5])

    with Timer("list append") as b:
        for i in range(1_000_000):
            for j in [2, 3, 4, 5]:
                [1].append(j)

    with Timer("tuple concat") as c:
        for i in range(1_000_000):
            _ = (1,) + (2, 3, 4, 5)

    a.delta(b, c)


def list_vs_tuple_extend_append_overhead_one_large_sequence():
    print("Benchmarking list extend/append & tuple concat with one large sequence...")

    # In the case of few large sequences, the performance difference between
    # list.extend and tuple concatenation is negligible, but list.append is
    # significantly slower.

    a = [1] * 500_000
    b = [2] * 500_000
    with Timer("list extend") as timer_a:
        a.extend(b)

    a = [1] * 500_000
    b = [2] * 500_000
    with Timer("list append") as timer_b:
        for i in b:
            a.append(i)

    a = (1,) * 500_000
    b = (2,) * 500_000
    with Timer("tuple concat") as timer_c:
        _ = a + b

    timer_a.delta(timer_b, timer_c)


def string_concatenation_many_small_strings():
    print("Benchmarking string concatenation to create many short strings...")

    # The Python 2.X wisdom was to always use `str.join` instead of string
    # concatenation.  However, in Python 3.X, the performance seems to be
    # tipped in the favor of concatenation, at least with many small strings.
    # Format-strings are also a tiny bit faster than `str.join`.

    with Timer("string concatenation") as a:
        for i in range(5_000_000):
            _ = "a" + "b" + "c" + "d" + "e"

    with Timer("string join") as b:
        for i in range(5_000_000):
            _ = "".join(["a", "b", "c", "d", "e"])

    with Timer("f-string") as c:
        for i in range(5_000_000):
            _ = f"{'a'}{'b'}{'c'}{'d'}{'e'}"

    a.delta(b, c)


def string_concatenation_one_long_string_from_many_small_strings():
    print("Benchmarking string concatenation to create one long string...")

    # The 2.X wisdom inverts when constructing one very long string from many
    # small strings.  In this case, `str.join` is faster than string concatenation,
    # but only by a hair. Format-strings are incredibly slow in this case because
    # the string is being re-allocated and copied many times.

    from itertools import cycle
    from string import ascii_lowercase

    infinite_alphabet = cycle(ascii_lowercase)

    with Timer("string concatenation") as a:
        _ = ""
        for i in range(500_000):
            _ += next(infinite_alphabet)

    with Timer("string join") as b:
        _ = "".join(next(infinite_alphabet) for _ in range(500_000))

    with Timer("f-string") as c:
        s = ""
        for i in range(500_000):
            s = f"{s}{next(infinite_alphabet)}"

    a.delta(b, c)


def string_concatenation_one_long_string_from_many_long_strings():
    print("Benchmarking string concatenation to create one long string...")

    # When the string are long but the number of concatenations is small, the
    # performance differences evaporate.

    from itertools import cycle
    from string import ascii_lowercase

    infinite_alphabet = cycle(ascii_lowercase)

    one_long_string = "".join(next(infinite_alphabet) for _ in range(5_000_000))
    three_long_strings = [one_long_string] * 3

    with Timer("string concatenation") as a:
        s = ""
        for string in three_long_strings:
            s += string

    with Timer("string join") as b:
        s = "".join(three_long_strings)

    with Timer("f-string") as c:
        s = ""
        for string in three_long_strings:
            s = f"{s}{string}"

    a.delta(b, c)


def list_of_obj_vs_obj_of_lists_known_len_known_values():
    print("Benchmarking list-of-obj vs obj-of-lists with known len and contents...")

    # In order to avoid the overhead of creating many objects, one approach is
    # to use a single object with lists of values representing individual
    # pieces of related data. In other languages, this is called a "structure
    # of arrays" (SoA) as opposed to an "array of structures" (AoS).

    # This benchmark compares the performance creating a list of objects vs
    # creating an object of lists, if you know the length and values of the
    # objects ahead of time.

    # The SoA approach is around 1000% faster than the AoS approach in this
    # example.

    class Foo:
        def __init__(self):
            self.a = 1
            self.b = 2
            self.c = 3

    class Foos:
        def __init__(self):
            self.a = [1] * 1_000_000
            self.b = [2] * 1_000_000
            self.c = [3] * 1_000_000

    with Timer("list of objects") as a:
        _ = [Foo() for _ in range(1_000_000)]

    with Timer("object of lists") as b:
        _ = Foos()

    a.delta(b)


def list_of_obj_vs_obj_of_lists_unknown_length_known_values():
    print("Benchmarking list of objects vs object of lists with unknown contents...")

    # This benchmark iteratively populates the objects with known values.
    # Once we have to rely on list.append to populate the object, the performance
    # benefits are reduced but not eliminated.

    class Foo:
        def __init__(self, a, b, c):
            self.a = a
            self.b = b
            self.c = c

    class Foos:
        def __init__(self):
            self.a = list()
            self.b = list()
            self.c = list()

    with Timer("list of objects") as a:
        list_of_foos = list()
        for _ in range(1_000_000):
            list_of_foos.append(Foo(1, 2, 3))

    with Timer("object of lists") as b:
        object_of_foos = Foos()
        for _ in range(1_000_000):
            object_of_foos.a.append(1)
            object_of_foos.b.append(2)
            object_of_foos.c.append(3)

    a.delta(b)


def list_of_obj_vs_obj_of_lists_unknown_length_unknown_values():
    print("Benchmarking list-of-obj vs obj-of-lists with unknown len or contents...")

    # This benchmark iteratively populates the objects, but the values must be
    # assigned after the object is created.

    class Foo:
        def __init__(self, a=None, b=None, c=None):
            self.a = a
            self.b = b
            self.c = c

    class Foos:
        def __init__(self):
            self.a = list()
            self.b = list()
            self.c = list()

    with Timer("list of objects") as a:
        list_of_foos = list()
        for _ in range(1_000_000):
            f = Foo()
            f.a = 1
            f.b = 2
            f.c = 3
            list_of_foos.append(f)

    with Timer("object of lists") as b:
        object_of_foos = Foos()
        for _ in range(1_000_000):
            object_of_foos.a.append(1)
        for _ in range(1_000_000):
            object_of_foos.b.append(2)
        for _ in range(1_000_000):
            object_of_foos.c.append(3)

    a.delta(b)


def list_of_dataclass_vs_obj_of_lists():
    print("Benchmarking list-of-dataclass vs obj-of-lists...")

    # This extends the benchmark for AoS vs SoA to include dataclasses.  The
    # performance of dataclasses is similar to that of regular classes.

    from dataclasses import dataclass

    @dataclass
    class Foo:
        a: int
        b: int
        c: int

    @dataclass(slots=True)
    class Foo2:
        a: int
        b: int
        c: int

    class Foos:
        def __init__(self):
            self.a = list()
            self.b = list()
            self.c = list()

    class Foos2:
        __slots__ = ["a", "b", "c"]

        def __init__(self):
            self.a = list()
            self.b = list()
            self.c = list()

    with Timer("list of dataclass") as a:
        list_of_foos = list()
        for _ in range(1_000_000):
            list_of_foos.append(Foo(1, 2, 3))

    with Timer("list of dataclass (with slots)") as b:
        list_of_foos = list()
        for _ in range(1_000_000):
            list_of_foos.append(Foo2(1, 2, 3))

    with Timer("object of lists") as c:
        object_of_foos = Foos()
        for _ in range(1_000_000):
            object_of_foos.a.append(1)
            object_of_foos.b.append(2)
            object_of_foos.c.append(3)

    with Timer("object of lists (with slots)") as d:
        object_of_foos = Foos2()
        for _ in range(1_000_000):
            object_of_foos.a.append(1)
            object_of_foos.b.append(2)
            object_of_foos.c.append(3)

    a.delta(b, c, d)


def access_list_of_obj_vs_obj_of_lists():
    print("Benchmarking attr access list-of-obj vs obj-of-lists...")

    # This benchmark compares the performance of accessing attributes of objects
    # in a list vs accessing elements of lists in an object.

    class Foo:
        __slots__ = ["a", "b", "c"]

        def __init__(self):
            self.a = 1
            self.b = 2
            self.c = 3

    class Foos:
        __slots__ = ["a", "b", "c"]

        def __init__(self):
            self.a = [1] * 1_000_000
            self.b = [2] * 1_000_000
            self.c = [3] * 1_000_000

    list_of_foos = [Foo() for _ in range(1_000_000)]
    object_of_foos = Foos()

    with Timer("access list of objects") as a:
        for foo in list_of_foos:
            _ = foo.a, foo.b, foo.c

    with Timer("access object of lists") as b:
        for i in range(1_000_000):
            _ = object_of_foos.a[i], object_of_foos.b[i], object_of_foos.c[i]

    a.delta(b)


@contextmanager
def stars():
    print("*" * 30)
    yield
    print("*" * 30)


if __name__ == "__main__":
    pass

    # un-comment the following to run the benchmarks

    # with stars():
    #     remove_dot_method_accessor()
    # with stars():
    #     math_ceil_vs_division_trick()
    # with stars():
    #     localize_global()
    # with stars():
    #     list_function_vs_brackets()
    # with stars():
    #     list_vs_tuple_instantiation_overhead_many_small_sequences()
    # with stars():
    #     list_vs_tuple_instantiation_overhead_one_large_sequence()
    # with stars():
    #     list_vs_tuple_concat_overhead_many_small_sequences()
    # with stars():
    #     list_vs_tuple_concat_overhead_one_large_sequence()
    # with stars():
    #     list_vs_tuple_extend_append_overhead_many_small_sequences()
    # with stars():
    #     list_vs_tuple_extend_append_overhead_one_large_sequence()
    # with stars():
    #     preallocate_many_small_list()
    # with stars():
    #     preallocate_one_large_list()
    # with stars():
    #     function_call_overhead()
    # with stars():
    #     function_call_overhead_vs_generator()
    # with stars():
    #     class_instantiation_overhead()
    # with stars():
    #     list_comprehension_vs_append_vs_map()
    # with stars():
    #     dict_comprehension_vs_setitem()
    # with stars():
    #     string_concatenation_many_small_strings()
    # with stars():
    #     string_concatenation_one_long_string_from_many_small_strings()
    # with stars():
    #     string_concatenation_one_long_string_from_many_long_strings()
    # with stars():
    #     list_of_obj_vs_obj_of_lists_known_len_known_values()
    # with stars():
    #     list_of_obj_vs_obj_of_lists_unknown_length_known_values()
    # with stars():
    #     list_of_obj_vs_obj_of_lists_unknown_length_unknown_values()
    # with stars():
    #     list_of_dataclass_vs_obj_of_lists()
    # with stars():
    #     access_list_of_obj_vs_obj_of_lists()
