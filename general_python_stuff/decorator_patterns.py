# A decorator that can be bare or called with arguments

from typing import Any, Callable, TypeVar, Union

# Define a type variable that can be any callable
F = TypeVar('F', bound=Callable[..., Any])

def decorated(*args: Union[F, Any], **kwargs: Any) -> Union[Callable[[F], F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*func_args: Any, **func_kwargs: Any) -> Any:
            if kwargs:
                print(f"Calling function with arguments: {kwargs}")
            else:
                print("Calling function without arguments")
            return func(*func_args, **func_kwargs)
        return wrapper

    # If the decorator is used without parentheses and with a single callable argument
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])
    else:
        # If the decorator is called with parentheses, possibly with arguments
        return decorator

# Example usage:

@decorated
def function1() -> None:
    print("Function 1 executed")

@decorated(arg="foo")
def function2() -> None:
    print("Function 2 executed")
