"""Unit tests for agent tool utilities."""

import io
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw, ImageFont


@pytest.fixture(autouse=True)
def agent_env(monkeypatch):
    monkeypatch.setenv("INCOMING_BUCKET", "amzn-s3-demo-source-bucket")
    monkeypatch.setenv("RESULTS_BUCKET", "amzn-s3-demo-destination-bucket")
    monkeypatch.setenv("FRONTEND_BUCKET", "amzn-s3-demo-bucket1")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB-TEST-123")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def agent2_module():
    """Import agent2_annotation with boto3 mocked (strands installed in venv)."""
    agent_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "agent_package"
    )
    sys.path.insert(0, agent_path)

    # Save modules we'll remove so we can restore them later
    saved_modules = {}
    for mod in list(sys.modules.keys()):
        if "agent2_annotation" in mod or "steering_hooks" in mod:
            saved_modules[mod] = sys.modules.pop(mod)

    with patch("boto3.client") as mock_client, \
         patch("boto3.Session") as mock_session:
        mock_session.return_value.region_name = "us-east-1"
        mock_s3 = mock_client.return_value

        import agent2_annotation
        agent2_annotation.amazon_s3 = mock_s3
        yield agent2_annotation, mock_s3

    # Clean up: remove our imports so subsequent tests get fresh modules
    for mod in list(sys.modules.keys()):
        if "agent2_annotation" in mod or "steering_hooks" in mod:
            del sys.modules[mod]

    sys.path.pop(0)


# ============================================================
# _wrap_text Tests (Pure Function)
# ============================================================

class TestWrapText:
    @pytest.fixture
    def draw_and_font(self):
        img = Image.new("RGB", (500, 500), "white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        return draw, font

    def test_short_text_single_line(self, agent2_module, draw_and_font):
        agent2, _ = agent2_module
        draw, font = draw_and_font
        result = agent2._wrap_text("Hi", font, 400, draw)
        assert len(result) == 1
        assert result[0] == "Hi"

    def test_long_text_wraps(self, agent2_module, draw_and_font):
        agent2, _ = agent2_module
        draw, font = draw_and_font
        long_text = "This is a very long text that should definitely wrap to multiple lines when given a narrow width"
        result = agent2._wrap_text(long_text, font, 80, draw)
        assert len(result) > 1

    def test_empty_string(self, agent2_module, draw_and_font):
        agent2, _ = agent2_module
        draw, font = draw_and_font
        result = agent2._wrap_text("", font, 400, draw)
        assert result == [""]


# ============================================================
# get_text_regions Coordinate Conversion Tests
# ============================================================

class TestGetTextRegionsCoordinates:
    def test_converts_bounding_box_to_pixel_coords(self, agent2_module):
        agent2, mock_s3 = agent2_module

        # Create a 1000x800 test image
        test_image = Image.new("RGB", (1000, 800), "white")
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=img_bytes))
        }

        mock_textract = MagicMock()
        mock_textract.detect_document_text.return_value = {
            "Blocks": [{
                "BlockType": "LINE",
                "Text": "Drug Facts",
                "Geometry": {
                    "BoundingBox": {
                        "Left": 0.1,
                        "Top": 0.2,
                        "Width": 0.3,
                        "Height": 0.05,
                    }
                },
            }]
        }

        with patch("agent2_annotation.boto3.client", return_value=mock_textract):
            result = agent2.get_text_regions("amzn-s3-demo-source-bucket", "test.png")

        assert len(result["text_blocks"]) == 1
        block = result["text_blocks"][0]
        assert block["text"] == "Drug Facts"
        # Left*Width = 0.1*1000 = 100
        # Top*Height = 0.2*800 = 160
        # (Left+Width)*ImgWidth = 0.4*1000 = 400
        # (Top+Height)*ImgHeight = 0.25*800 = 200
        assert block["box"][0] == 100
        assert block["box"][1] == 160
        assert block["box"][2] == 400
        assert block["box"][3] == 200


# ============================================================
# draw_annotations Tests
# ============================================================

class TestDrawAnnotations:
    def test_empty_annotations_adds_sidebar(self, agent2_module):
        """Empty annotations → compliant label, output has sidebar."""
        agent2, mock_s3 = agent2_module

        test_image = Image.new("RGB", (400, 300), "white")
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        # Compliant badge
        badge = Image.new("RGBA", (100, 100), (0, 200, 0, 255))
        badge_buffer = io.BytesIO()
        badge.save(badge_buffer, format="PNG")
        badge_bytes = badge_buffer.getvalue()

        mock_s3.get_object.side_effect = [
            {"Body": MagicMock(read=MagicMock(return_value=img_bytes))},
            {"Body": MagicMock(read=MagicMock(return_value=badge_bytes))},
        ]

        result = agent2.draw_annotations("amzn-s3-demo-source-bucket", "test.png", [])

        assert "s3://" in result
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "image/png"

        # Verify output image is wider (sidebar added)
        output_img = Image.open(io.BytesIO(call_kwargs["Body"]))
        assert output_img.width > 400

    def test_image_annotations_draw_boxes(self, agent2_module):
        """Annotations with real boxes are drawn on the image."""
        agent2, mock_s3 = agent2_module

        test_image = Image.new("RGB", (400, 300), "white")
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()

        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=img_bytes))
        }

        annotations = [
            {"label": "Font too small", "box": [50, 100, 200, 150], "severity": "low"},
        ]

        result = agent2.draw_annotations("amzn-s3-demo-source-bucket", "test.png", annotations)

        assert "s3://" in result
        mock_s3.put_object.assert_called_once()
