"""Tests for NexusLambdaAuthorizer module."""

import pytest


@pytest.mark.xfail
def test_that_you_wrote_tests():
    """Test that you wrote tests."""
    from textwrap import dedent

    assertion_string = dedent(
        """\
    No, you have not written tests.

    However, unless a test is run, the pytest execution will fail
    due to no tests or missing coverage. So, write a real test and
    then remove this!
    """
    )
    assert False, assertion_string


def test_nexus_lambda_authorizer_importable():
    """Test nexus_lambda_authorizer is importable."""
    import nexus_lambda_authorizer  # noqa: F401
