from tests import helpers


def test_eval_1_is_fast():
    """``eval `` should be very quick."""
    # This should ideally be below 0.1s.
    with helpers.Timer(max=0.6):
        output = helpers.run(["eval", "1"]).decode()

    assert output == "1\n"
