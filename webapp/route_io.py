"""Helpers for keeping CGI route responses clean."""
from contextlib import contextmanager
import os
import sys


@contextmanager
def redirect_stdout_to_stderr():
    """Send all process stdout, including child-process output, to stderr."""
    sys.stdout.flush()
    saved_stdout_fd = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved_stdout_fd, 1)
        os.close(saved_stdout_fd)
