from __future__ import generator_stop


def run(program, items):
    for how, what in program:

        items = list(items)

        if how == "map":

            # items = map(what, items)
            items = (what(item) for item in items)

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

    main([("map", str.upper), ("map", len), ("apply", sum)], ["a", "bb", "ccc", "dddd"])
