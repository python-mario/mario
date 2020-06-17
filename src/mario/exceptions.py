class MarioException(Exception):
    """Base class for all Mario package exceptions."""


class IncompleteFrameError(MarioException):
    """Received an incomplete frame."""
