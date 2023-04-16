from difflib import SequenceMatcher


# FUZZY STRING MATCHING

def fuzzy_ratio(string_one, string_two):
    """Get a degree of similarity between two strings.

    Args:
        string_one (str)
        string_two (str)

    Returns:
        float: A value between 0 and 1 representing the degree of match
            between the two strings, with 0 being no match, and 1 being
            an exact match.
    """

    return SequenceMatcher(None, string_one, string_two).ratio()


def fuzzy_substring_ratio(string_one, string_two):
    """Get the similarity between two strings, regardless of length

    For example, "dodg" and "doggedness" are not very similar in total,
    but if you compare "dodg" against the substring "dogg", they only
    have one letter difference.  This function scans the longer string
    for the best-case match of all substrings.

    Args:
        string_one (str)
        string_two (str)

    Returns:
        float: A value between 0 and 1 representing the degree of match
            between the two strings, with 0 being no match, and 1 being
            an exact match between the shorter string and any part of the
            longer string.
    """

    # exact match
    if string_one == string_two:
        return 1.0

    len_string_one = len(string_one)
    len_string_two = len(string_two)

    # always use the shorter string as the search term
    if len_string_one > len_string_two:
        string_one, string_two = string_two, string_one
        len_string_one = len_string_two

    # the built-in search for exact substring matches is very quick
    if string_one in string_two:
        return 1.0

    matcher = SequenceMatcher(None, string_one, string_two)
    match_blocks = matcher.get_matching_blocks()[:-1]

    # because we know how many potential match-blocks there are, we can
    # pre-allocate a list.  This is faster than appending.
    fuzzy_ratios = [None] * len(match_blocks)

    for i, ratio in enumerate(_blocks_to_ratios(match_blocks, len_string_one,
                                                string_one, string_two)):
        fuzzy_ratios[i] = ratio

    try:
        return max(fuzzy_ratios)
    except ValueError:
        # no matching blocks found
        return 0.0


def _blocks_to_ratios(block_triples, len_string_one, string_one, string_two):
    for string_one_index, string_two_index, block_len in block_triples:
        string_two_end = string_two_index + len_string_one
        string_two_substr = string_two[string_two_index:string_two_end]
        yield SequenceMatcher(None, string_one, string_two_substr).ratio()


def fuzzy_match(string_one, string_two, threshold=0.6):
    """Returns True if the strings are more similar than the threshold.

    Args:
        string_one (str)
        string_two (str)
        threshold (float): the degree of similarity that qualifies as a
            match

    Returns: bool
    """
    return fuzzy_ratio(string_one, string_two) >= threshold


def fuzzy_substring_match(string_one, string_two, threshold=0.6):
    """Returns True if a substring in the longer matches the shorter.

    Args:
        string_one (str)
        string_two (str)
        threshold (float): the degree of similarity that qualifies as a
            match
    """

    # exact match
    if string_one == string_two:
        return True

    len_string_one = len(string_one)
    len_string_two = len(string_two)

    # always use the shorter string as the search term
    if len_string_one > len_string_two:
        string_one, string_two = string_two, string_one
        len_string_one = len_string_two

    # the built-in search for exact substring matches is very quick
    if string_one in string_two:
        return True

    matcher = SequenceMatcher(None, string_one, string_two)
    match_blocks = matcher.get_matching_blocks()[:-1]
    for ratio in _blocks_to_ratios(match_blocks, len_string_one,
                                   string_one, string_two):
        if ratio >= threshold:
            return True

    return False


# SUBSTRING MATCHING

def substring_match(string_one, string_two):
    """Returns True if the shorter string is found in the longer one

    Args:
        string_one (str)
        string_two (str)

    Returns: bool
    """

    # exact match
    if string_one == string_two:
        return True

    # If it's not an exact match, and the lengths are the same, it's
    # a guaranteed no-match
    elif len(string_one) == len(string_two):
        return False

    len_string_one = len(string_one)
    len_string_two = len(string_two)

    # always use the shorter string as the search term
    if len_string_one > len_string_two:
        string_one, string_two = string_two, string_one

    if string_one in string_two:
        return True
    return False


def nonconsecutive_match(needles, haystack, anchored=False,
                         empty_returns_true=True):
    """Returns whether every character can be found in the search, in order.

    The characters do not have to be consecutive, but they must be in order.

    For example, "mm" can be found in "matchmove", but not "move2d"
    "m2" can be found in "move2d", but not "matchmove"

    Args:

        needles (string): An iterable of single items that must be
            found in the search space.

        haystack (string): The items to search through.

        anchored (bool): Whether the first item must match for the entire
            match to be valid.

        empty_returns_true (bool): whether an empty string counts as a
            match (see examples)

    Example:

        >>> nonconsecutive_match("m2", "move2d")
        True

        >>> nonconsecutive_match("m2", "matchmove")
        False

        >>> nonconsecutive_match("atch", "matchmove", anchored=False)
        True

        >>> nonconsecutive_match("atch", "matchmove", anchored=True)
        False

    Returns: bool
    """

    # LOW HANGING FRUIT
    if needles == haystack:
        return True

    if len(haystack) == 0 and needles:
        # "a" is not in ""
        return False

    elif len(needles) == 0 and haystack:
        # "" is in "blah"
        return empty_returns_true

    # Turn haystack into list of characters
    haystack = [letter for letter in str(haystack)]

    # ANCHORED SEARCH
    if anchored:
        if needles[0] != haystack[0]:
            return False
        else:
            # First letter matches, remove it for further matches
            needles = needles[1:]
            del haystack[0]

    # CONTINUE, UNANCHORED
    for needle in needles:
        try:
            needle_pos = haystack.index(needle)
        except ValueError:
            return False
        else:
            # Dont find string in same pos or backwards again
            del haystack[:needle_pos + 1]
    return True


def exact_match(string_one, string_two):
    """Convenience function for use where a function is required.

    Mostly just saves us writing a lambda or two.

    Args:
        string_one (str)
        string_two (str)

    Returns: bool
    """
    return string_one == string_two
