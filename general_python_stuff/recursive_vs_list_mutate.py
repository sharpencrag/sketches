"""This is a simple example of a recursive traversal vs an iterative one.

The iterative approach mutates a list as it traverses the tree, which is
often considered to be a Very Bad Thing.  However, in this case, it's
significantly faster than the recursive approach, and within the scope of our
single-threaded application, it's not going to cause any problems.

Safety is also enhanced by making a copy of the original list before iterating
over it.
"""

class Node(object):
    children = list()


def get_ancestors_recursive(node):
    ancestors = list()
    ancestors.extend(node.children)
    for child in node.children:
        ancestors.extend(get_ancestors_recursive(child))
    return ancestors


def get_ancestors_mutation(node):
    ancestors = list(node.children)
    for ancestor in ancestors:
        ancestors.extend(ancestor.children)
    return ancestors


if __name__ == "__main__":

    # build the tree
    top_node = Node()
    children = [Node(), Node(), Node()]
    grand_children = [Node(), Node()]
    great_grand_children = [Node(), Node(), Node(), Node()]

    all_ancestors = children + grand_children + great_grand_children
    top_node.children = children
    top_node.children[0].children = grand_children
    top_node.children[0].children[0].children = great_grand_children

    # make sure both approaches return the same results

    recursive = get_ancestors_recursive(top_node)

    assert all([node in all_ancestors for node in recursive])
    assert len(all_ancestors) == len(recursive)

    mutation = get_ancestors_mutation(top_node)

    assert all([node in all_ancestors for node in mutation])
    assert len(all_ancestors) == len(mutation)
