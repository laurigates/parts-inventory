from pytest import approx

from parts_inventory.vision import Recognition


def test_recognition_from_full_json():
    rec = Recognition.from_json(
        {
            "name": "4.7k resistor",
            "kind": "component",
            "category": "resistors",
            "attributes": {"resistance": "4.7k", "tolerance": "1%"},
            "confidence": 0.91,
        }
    )
    assert rec.name == "4.7k resistor"
    assert rec.kind == "component"
    assert rec.attributes["tolerance"] == "1%"
    assert rec.confidence == 0.91
    assert rec.needs_closer_look is False


def test_recognition_defaults_and_closer_look():
    rec = Recognition.from_json(
        {
            "name": "resistor",
            "kind": "component",
            "category": "resistors",
            "confidence": 0.3,
            "needs_closer_look": True,
            "prompt_for_user": "Show the colour bands closer.",
        }
    )
    assert rec.attributes == {}
    assert rec.needs_closer_look is True
    assert "bands" in rec.prompt_for_user


def test_bbox_normalized_to_fractional_xywh():
    # [ymin, xmin, ymax, xmax] 0-1000 -> [x, y, w, h] fractional
    rec = Recognition.from_json(
        {
            "name": "x",
            "kind": "tool",
            "category": "c",
            "confidence": 0.5,
            "bbox": [100, 200, 600, 700],
        }
    )
    assert rec.bbox == approx([0.2, 0.1, 0.5, 0.5])


def test_bbox_missing_or_degenerate_is_none():
    base = {"name": "x", "kind": "tool", "category": "c", "confidence": 0.5}
    assert Recognition.from_json(base).bbox is None
    assert Recognition.from_json({**base, "bbox": [1, 2, 3]}).bbox is None  # wrong len
    assert (
        Recognition.from_json({**base, "bbox": [500, 500, 500, 500]}).bbox is None
    )  # zero area


def test_bbox_clamped_and_reordered():
    # out-of-range + reversed coords get clamped to 0-1 and ordered min->max
    rec = Recognition.from_json(
        {
            "name": "x",
            "kind": "tool",
            "category": "c",
            "confidence": 0.5,
            "bbox": [1200, 800, -100, 300],
        }
    )
    assert rec.bbox == approx([0.3, 0.0, 0.5, 1.0])
