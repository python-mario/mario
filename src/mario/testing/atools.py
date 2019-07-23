import functools


async def async_drop_falsy(items):
    async for x in items:
        if x:
            yield x


def drop_falsy(items):
    for x in items:
        if x:
            yield x


def my_max(items):
    print("hello")

    it = iter(items)

    try:
        current_max = next(it)
    except StopIteration as e:
        raise ValueError("Iterable was empty") from e
    for x in it:

        if x > current_max:
            current_max = x
    # pylint: disable=undefined-loop-variable
    return x


# def gen_max(items):
#     it = iter(items)
#     try:
#         current_max = next(it)
#     except StopIteration as e:
#         raise ValueError("Iterable was empty") from e
#     for x in it:

#         if x > current_max:
#             current_max = x
#     yield x


def gen_max(items):
    yield from [my_max(items)]


def wrap_sync_fold(function):
    @functools.wraps(function)
    def wrap(items):
        yield from [function(items)]

    return wrap


wrapped_max = wrap_sync_fold(my_max)

wrapped_drop_falsy = wrap_sync_fold(drop_falsy)
