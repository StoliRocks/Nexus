import pytest

from nexus_application_interface.api.ingestion.control import Control, Framework


class TestControl:
    @pytest.fixture
    def valid_framework(self):
        return Framework.from_dict({"name": "test-framework", "type": "AWS", "version": "1.0.0"})

    def test_invalid_document(self, valid_framework):

        with pytest.raises(ValueError, match="Bucket name is required and cannot be empty"):
            Control(
                bucket="",
                control_id="test-control",
                framework=valid_framework,
            )

        with pytest.raises(ValueError, match="Control ID is required and cannot be empty"):
            Control(
                bucket="XXXXXXXXXXX",
                control_id="",
                framework=valid_framework,
            )

        with pytest.raises(ValueError, match="Framework is required and cannot be empty"):
            Control(
                bucket="XXXXXXXXXXX",
                control_id="test-control",
                framework=None,
            )

        with pytest.raises(ValueError, match="Framework must be an instance of Framework class"):
            Control(
                bucket="XXXXXXXXXXX",
                control_id="test-control",
                framework=123,  # type: ignore
            )
