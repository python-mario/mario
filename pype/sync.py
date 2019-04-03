import itertools


def run(program, items):
    for how, what in program:

        if how == "map":
            items = map(what, items)

        elif how == "apply":
            items = what(items)

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
            ("apply", lambda it: filter(lambda x: x % 2 == 0, it)),
            ("map", lambda x: x + 1),
        ],
        items=["a", "bb", "ccc", "dddd"],
    )
