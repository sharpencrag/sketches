from typing import List, TypeVar, Hashable

T = TypeVar("T", bound=Hashable)

def partition(sequence: List[T]) -> List[List[T]]:
    stack = [(int(), [], slice(0, len(sequence)))]
    result = []

    while stack:
        index, current_partition, remaining = stack.pop()

        if remaining.stop - remaining.start == 0:
            result.append(current_partition)
        else:
            for i in range(index, remaining.stop - remaining.start):
                head = slice(remaining.start, remaining.start + i + 1)
                tail = slice(remaining.start + i + 1, remaining.stop)
                new_partition = current_partition + [sequence[head]]
                stack.append((i, new_partition, tail))

    return result
