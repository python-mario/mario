import itertools


def run(program, items):
    for how, what in program:

        if how == "map":
            items = map(what, items)

        elif how == "apply":
            items = what(items)

        elif how == "filter":
            items = filter(what, items)

        else:
            raise ValueError

    return items


def main(program, items):

    result = run(program, items)

    try:
        for item in result:
            print(item)
    except TypeError:
        print(result)


if __name__ == "__main__":

    main(
        program=[
            ("map", str.upper),
            ("map", len),
            ("apply", lambda it: itertools.chain.from_iterable(itertools.tee(it))),
            ("map", lambda x: x + 1),
            ("filter", lambda x: x > 4),
            ("map", lambda x: x * 10),
        ],
        items=["a", "bb", "ccc", "dddd", "eeeee", "ffffff"],
    )
