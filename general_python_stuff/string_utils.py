import re
from itertools import takewhile


digit_end_regex = re.compile(r'(?:[^\d]*(\d+)[^\d]*)+')


def increment(string_val):
    """If the given string ends with a digit, add one to it.

    Args:
        string_val (str)

    Example:
        >>> increment("string123")
        'string124'
    """
    search = digit_end_regex.search(string_val)
    if search:
        next = str(int(search.group(1)) + 1)
        start, end = search.span(1)
        string_val = "".join([string_val[:max(end - len(next), start)],
                             next, string_val[end:]])
    else:
        string_val = "".join([string_val, "1"])
    return string_val


def longest_common_prefix(strings):
    """Find the longest common starting substring
    Args:
        strings (iterable)

    Example:
        >>> longest_common_prefix(["abc_hello", "abc_goodbye"])
        'abc_'
    """
    def all_chars_same(chars):
        return len(set(chars)) == 1
    common_chars = [substr_tuple[0] for substr_tuple
                    in takewhile(all_chars_same, zip(*strings))]
    return "".join(common_chars)


def camel_case_split(original_string):
    """Split a string based on camelCase or CapWords.

    Original capitalization is kept in the returned strings.

    Args:
        original_string (str)

    Returns: list

    Example:
        >>> camel_case_split("helloWorld")
        ['hello', 'World']
    """

    # the second-worst regex I've ever copied from the internet
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        original_string
    )
    return [m.group(0) for m in matches]


def ignore_case_replace(orignal_string, value_to_search, replace_value):
    """Replaces a substring regardless of its capitalization.

    Args:
        original_string (str)
        value_to_search (str)
        replace_value (str)

    Returns: str

    Example:
        >>> ignore_case_replace("AbC_123", "abc", "def")
        'def_123'
    """
    ignore_replace = re.compile(re.escape(value_to_search), re.IGNORECASE)
    return ignore_replace.sub(replace_value, orignal_string)
