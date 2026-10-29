"""Validate the real generated layered manifest and transparent PNG assets.

Run from the repository root with:
    python -m unittest discover -s tests -p test_layers.py -v

Missing generated assets are errors, not successful fixture-only tests.
The separate scripts/verify_layered_render.cjs verifies rendered pixel invariance.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import unittest
import warnings

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ACTIONS = {"none", "wave", "peace", "shush", "heart", "write", "think"}
FORBIDDEN_OVERRIDES = {
    "head", "face", "headOverride", "head_override", "headTransform",
    "head_transform", "faceOverride", "face_override", "faceTransform",
    "face_transform", "headSprite", "head_sprite", "faceSprite", "face_sprite",
}


class LayeredAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manifest_path = ROOT / "data/layers.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Generated layered manifest is not available: {manifest_path}. "
                "Generate the actual sprites and manifest before running this test."
            )
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def assert_transform(self, transform, where):
        self.assertIsInstance(transform, list, where)
        self.assertEqual(len(transform), 6, where)
        self.assertTrue(
            all(isinstance(v, (int, float)) and not isinstance(v, bool)
                and math.isfinite(v) for v in transform), where
        )
        a, b, c, d, _, _ = transform
        self.assertGreater(abs(a * d - b * c), 1e-12, where)

    def assert_no_face_override(self, value, where):
        if isinstance(value, dict):
            for key, child in value.items():
                self.assertNotIn(key, FORBIDDEN_OVERRIDES, f"{where}.{key}")
                self.assert_no_face_override(child, f"{where}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.assert_no_face_override(child, f"{where}[{index}]")

    def test_one_locked_face_and_fixed_canvas(self):
        m = self.manifest
        self.assertEqual(m["schema"], "tyri.layered.v1")
        self.assertEqual(m["canvas"]["width"], 1024)
        self.assertEqual(m["canvas"]["height"], 1024)
        self.assertEqual(m["canvas"]["alpha"], "straight")
        head = m["head"]
        self.assertIs(head["locked"], True)
        self.assertEqual(head["z"], 100)
        self.assert_transform(head["transform"], "head.transform")
        a, b, c, d, _, _ = head["transform"]
        self.assertGreater(a, 0, "The canonical face must not be flipped.")
        self.assertEqual(b, 0, "The canonical face must not be rotated.")
        self.assertEqual(c, 0, "The canonical face must not be sheared.")
        self.assertEqual(a, d, "The canonical face scale must preserve its aspect ratio.")
        self.assertEqual(m["sprites"][head["sprite"]]["role"], "face")
        self.assertEqual(
            {key for key, sprite in m["sprites"].items() if sprite["role"] == "face"},
            {head["sprite"]},
            "All actions must share one canonical face sprite.",
        )

    def test_real_animation_references_and_handedness(self):
        m = self.manifest
        self.assertTrue(EXPECTED_ACTIONS.issubset(m["animations"]),
                        "The manifest must include none and all six requested actions.")
        referenced_hands = set()
        for animation_id, animation in m["animations"].items():
            with self.subTest(animation=animation_id):
                self.assert_no_face_override(animation, animation_id)
                self.assertIsInstance(animation["label"], str)
                self.assertTrue(animation["label"].strip())
                frames = animation["frames"]
                self.assertIsInstance(frames, list)
                self.assertTrue(frames, "An animation must contain actual frames.")
                instance_count = 0
                for index, frame in enumerate(frames):
                    where = f"{animation_id}.frames[{index}]"
                    duration = frame["duration_ms"]
                    self.assertIsInstance(duration, (int, float), where)
                    self.assertNotIsInstance(duration, bool, where)
                    self.assertTrue(math.isfinite(duration) and duration > 0, where)
                    self.assertIsInstance(frame["instances"], list, where)
                    if animation_id == "none":
                        self.assertEqual(frame["instances"], [],
                                         "The hand-free state must contain no hand layers.")
                    for instance in frame["instances"]:
                        instance_count += 1
                        sprite_id = instance["sprite"]
                        self.assertIn(sprite_id, m["sprites"], where)
                        sprite = m["sprites"][sprite_id]
                        self.assertIn(sprite["role"], ("hand", "hand-prop"), where)
                        self.assertNotEqual(sprite_id, m["head"]["sprite"], where)
                        if "side" in sprite:
                            self.assertIn(sprite["side"], ("left", "right", "both"),
                                          f"{sprite_id}: invalid anatomical handedness.")
                        if "surface" in sprite:
                            self.assertIn(sprite["surface"], ("palm", "back", "mixed"),
                                          f"{sprite_id}: palm/back surface is distinct from z order.")
                        self.assert_transform(instance["transform"], where)
                        z = instance["z"]
                        self.assertIsInstance(z, (int, float), where)
                        self.assertTrue(math.isfinite(z), where)
                        self.assertNotEqual(z, m["head"]["z"], where)
                        if "opacity" in instance:
                            self.assertIsInstance(instance["opacity"], (int, float), where)
                            self.assertTrue(math.isfinite(instance["opacity"])
                                            and 0 <= instance["opacity"] <= 1, where)
                        referenced_hands.add(sprite_id)
                if animation_id != "none":
                    self.assertGreater(instance_count, 0,
                                       f"{animation_id} must actually reference a hand sprite.")
        self.assertTrue(referenced_hands)

    def test_png_paths_dimensions_hashes_and_true_transparency(self):
        for sprite_id, sprite in self.manifest["sprites"].items():
            with self.subTest(sprite=sprite_id):
                relative = Path(sprite["path"])
                self.assertFalse(relative.is_absolute(), f"{sprite_id}: use repository-relative paths.")
                self.assertNotIn("..", relative.parts, sprite_id)
                path = (ROOT / relative).resolve()
                self.assertTrue(path.is_relative_to(ROOT), sprite_id)
                self.assertTrue(path.is_file(), f"Missing actual sprite PNG: {relative}")
                self.assertEqual(path.suffix.lower(), ".png", sprite_id)
                source_size = sprite["source_size"]
                self.assertEqual(len(source_size), 2, sprite_id)
                self.assertTrue(all(isinstance(n, int) and not isinstance(n, bool)
                                    and n > 0 for n in source_size), sprite_id)
                self.assertRegex(sprite["pixel_sha256"], r"^[0-9a-f]{64}$", sprite_id)
                with Image.open(path) as im:
                    im.load()
                    self.assertEqual(im.format, "PNG", sprite_id)
                    self.assertEqual(im.mode, "RGBA", f"{sprite_id}: the PNG must contain real RGBA.")
                    self.assertEqual(list(im.size), source_size, sprite_id)
                    self.assertEqual(hashlib.sha256(im.tobytes()).hexdigest(),
                                     sprite["pixel_sha256"], sprite_id)
                    alpha = im.getchannel("A")
                    histogram = alpha.histogram()
                    self.assertGreater(histogram[0], 0, f"{sprite_id}: no fully transparent pixels.")
                    self.assertGreater(sum(histogram[1:]), 0, f"{sprite_id}: the sprite is empty.")
                    self.assertGreater(histogram[255], 0, f"{sprite_id}: no opaque artwork.")
                    w, h = im.size
                    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
                    self.assertTrue(all(alpha.getpixel(point) == 0 for point in corners),
                                    f"{sprite_id}: transparent canvas corners are required.")
                    if "pivot" in sprite:
                        pivot = sprite["pivot"]
                        self.assertEqual(len(pivot), 2, sprite_id)
                        self.assertTrue(all(isinstance(v, (int, float)) and math.isfinite(v)
                                            for v in pivot), sprite_id)
                        self.assertTrue(0 <= pivot[0] <= w and 0 <= pivot[1] <= h, sprite_id)
                    self.warn_suspicious_baked_background(sprite_id, im)

    @staticmethod
    def warn_suspicious_baked_background(sprite_id, im):
        """Advisory only: alpha checks above are the hard transparency gate."""
        sample = im.copy()
        sample.thumbnail((128, 128), Image.Resampling.NEAREST)
        pixels = list(sample.getdata())
        opaque = [(r, g, b) for r, g, b, a in pixels if a > 240]
        if not opaque:
            return
        green = sum(g > 80 and g > 1.4 * r and g > 1.4 * b for r, g, b in opaque)
        if green > max(4, len(opaque) * 0.005):
            warnings.warn(f"{sprite_id}: saturated green pixels may be chroma-key residue; inspect edges.")
        gray = [r for r, g, b in opaque if max(r, g, b) - min(r, g, b) <= 3 and 40 < r < 245]
        if len(gray) > len(pixels) * 0.12 and len(set(gray)) >= 2:
            warnings.warn(f"{sprite_id}: a large opaque gray region may be a baked checkerboard; inspect visually.")


if __name__ == "__main__":
    unittest.main()
