#!/usr/bin/env python3
"""Read-only pixel and timing verification for the native animated WebP.

The renderer must be run with TYRI_PREVIEW_KEEP_FRAMES=1. Its retained work
directory contains timeline.json and the original native PNG frames.

Usage:
    python3 scripts/verify_preview_quality.py \
        --frames-dir /tmp/tyri-layered-previews-... \
        --output docs/preview-quality-validation.json

Only the requested JSON report is written. No image or metadata input changes.
Requires Pillow with animated WebP support. This verifies PNG -> WebP fidelity
and the declared native transform; the separate layered-render verification
already tests the invariant face layer across hand states.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image, features


ROOT = Path(__file__).resolve().parents[1]


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def read_json(path):
    require(path.is_file(), f"Required generated input is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def positive_milliseconds(value, where):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"{where} must be a finite millisecond value.")
    require(value > 0 and float(value).is_integer(),
            f"{where} must be a positive whole number of milliseconds; got {value!r}.")
    return int(value)


def first_difference(actual, expected, width):
    for byte_index, (a, b) in enumerate(zip(actual, expected)):
        if a != b:
            pixel_index = byte_index // 4
            start = pixel_index * 4
            return {
                "x": pixel_index % width,
                "y": pixel_index // width,
                "decoded_rgba": list(actual[start:start + 4]),
                "source_rgba": list(expected[start:start + 4]),
            }
    return {"actual_byte_count": len(actual), "source_byte_count": len(expected)}


def verify(args, report):
    repo = args.repo.resolve()
    work = args.frames_dir.resolve()
    metadata_path = repo / "docs/preview-quality.json"
    timeline_path = work / "timeline.json"
    require(args.output.resolve() not in {metadata_path.resolve(), timeline_path.resolve()},
            "The output report must not overwrite preview-quality.json or timeline.json.")
    metadata = read_json(metadata_path)
    timeline = read_json(timeline_path)
    native = metadata["native"]
    transform = native["face_transform"]
    require(isinstance(transform, list) and len(transform) == 6
            and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                    and math.isfinite(v) for v in transform),
            "native.face_transform must contain six finite numbers.")
    # Permit machine-precision products such as s * (1 / s), not actual scaling
    # or fractional translation. The normalized values make the report explicit.
    for index, expected in enumerate((1, 0, 0, 1)):
        require(math.isclose(transform[index], expected, rel_tol=0, abs_tol=1e-12),
                "The native face is resampled or rotated: face_transform must begin [1,0,0,1].")
    for index in (4, 5):
        require(math.isclose(transform[index], round(transform[index]), rel_tol=0, abs_tol=1e-9),
                "The native face has fractional translation; tx and ty must be integers.")
    require(native.get("face_pixels_per_source_pixel") == 1,
            "Metadata must declare one output face pixel per source pixel.")
    normalized_transform = [1, 0, 0, 1, round(transform[4]), round(transform[5])]
    report["native_face_transform"] = transform
    report["normalized_native_face_transform"] = normalized_transform
    report["declared_face_transform_is_unit_integer_translation"] = True

    expected_size = native["canvas_size"]
    require(isinstance(expected_size, list) and len(expected_size) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) and v > 0
                    for v in expected_size), "native.canvas_size must be two positive integers.")
    animation_path = Path(native["animation"])
    require(not animation_path.is_absolute() and ".." not in animation_path.parts,
            "The native WebP path must be repository-relative.")
    webp_path = (repo / animation_path).resolve()
    require(webp_path.is_relative_to(repo), "The WebP path escapes the repository.")
    require(webp_path.is_file(), f"Generated native WebP is missing: {webp_path}")
    require(webp_path.suffix.lower() == ".webp", "The native animation must be a WebP file.")
    require(features.check("webp"), "This Pillow installation cannot decode WebP images.")

    stages, paths, durations = timeline["stages"], timeline["paths"], timeline["durations"]
    require(isinstance(stages, list) and isinstance(paths, list) and isinstance(durations, list),
            "timeline.json must contain stages, paths, and durations arrays.")
    require(len(paths) > 0 and len(stages) == len(paths) == len(durations),
            "The timeline arrays must have the same nonzero length.")
    durations = [positive_milliseconds(ms, f"durations[{i}]") for i, ms in enumerate(durations)]
    source_paths = []
    starts, ends = [], []
    elapsed = 0
    for index, (stage, filename, duration) in enumerate(zip(stages, paths, durations)):
        require(isinstance(stage, dict) and isinstance(stage.get("id"), str),
                f"stages[{index}] must identify an animation.")
        require(positive_milliseconds(stage.get("duration"), f"stages[{index}].duration") == duration,
                f"stages[{index}].duration disagrees with durations[{index}].")
        require(isinstance(filename, str), f"paths[{index}] must name an actual PNG.")
        source_path = Path(filename)
        require(source_path.is_absolute(), f"paths[{index}] must be an absolute renderer PNG path.")
        require(source_path.is_file(), f"Retained original PNG is missing: {source_path}")
        require(source_path.suffix.lower() == ".png", f"Expected an original PNG: {source_path}")
        source_paths.append(source_path)
        starts.append(elapsed)
        elapsed += duration
        ends.append(elapsed)
    expected_duration = elapsed
    require(metadata.get("source_frame_count") == len(source_paths),
            "preview-quality.json source_frame_count disagrees with the retained timeline.")
    require(metadata.get("duration_ms") == expected_duration,
            "preview-quality.json duration_ms disagrees with the retained timeline.")

    @lru_cache(maxsize=3)
    def source_pixels(index):
        with Image.open(source_paths[index]) as source:
            require(source.format == "PNG", f"Input is not a PNG: {source_paths[index]}")
            require(list(source.size) == expected_size,
                    f"Source PNG dimensions differ from native.canvas_size: {source_paths[index].name}")
            pixels = source.convert("RGBA").tobytes()
        return pixels, hashlib.sha256(pixels).hexdigest()

    report.update({
        "animation": animation_path.as_posix(),
        "webp_file_sha256": file_hash(webp_path),
        "renderer_metadata_sha256": file_hash(metadata_path),
        "retained_timeline_sha256": file_hash(timeline_path),
        "expected_canvas_size": expected_size,
        "source_frame_count": len(source_paths),
        "expected_duration_ms": expected_duration,
        "scope": "Exact decoded WebP RGBA versus the renderer's PNG timeline, including complete frame intervals; declared native transform checked separately. Face/hand invariance is covered by layered-render-validation.json.",
    })
    frame_reports = []
    covered = set()
    decoded_elapsed = 0
    with Image.open(webp_path) as animation:
        require(animation.format == "WEBP", "The generated animation is not a WebP container.")
        report["decoded_canvas_size"] = list(animation.size)
        require(list(animation.size) == expected_size,
                f"Decoded WebP size {animation.size} differs from the original PNG canvas {expected_size}.")
        report["decoded_frame_count"] = animation.n_frames
        report["loop"] = animation.info.get("loop")
        for frame_index in range(animation.n_frames):
            animation.seek(frame_index)
            # Pillow populates animated WebP duration metadata when pixels load.
            decoded = animation.convert("RGBA")
            actual = decoded.tobytes()
            duration = positive_milliseconds(animation.info.get("duration"),
                                             f"decoded WebP frame {frame_index} duration")
            frame_start = decoded_elapsed
            frame_end = frame_start + duration
            decoded_elapsed = frame_end
            report["decoded_duration_ms_so_far"] = decoded_elapsed
            require(frame_start < expected_duration and frame_end <= expected_duration,
                    f"WebP frame {frame_index} extends to {frame_end}ms beyond the intended "
                    f"{expected_duration}ms. Check for an encoded concat terminal duplicate or extra final-frame duration.")

            # An encoder may combine consecutive identical PNGs. Checking only
            # the frame's start would miss a frame held across a different PNG,
            # so compare with EVERY source interval the decoded frame covers.
            source_index = bisect_right(ends, frame_start)
            compared = []
            actual_hash = hashlib.sha256(actual).hexdigest()
            while source_index < len(source_paths) and starts[source_index] < frame_end:
                expected, expected_hash = source_pixels(source_index)
                if actual != expected:
                    detail = first_difference(actual, expected, expected_size[0])
                    report["pixel_mismatch"] = {
                        "decoded_frame": frame_index,
                        "decoded_interval_ms": [frame_start, frame_end],
                        "source_frame": source_index,
                        "source_png": source_paths[source_index].name,
                        "source_interval_ms": [starts[source_index], ends[source_index]],
                        "decoded_rgba_sha256": actual_hash,
                        "source_rgba_sha256": expected_hash,
                        "first_difference": detail,
                    }
                    raise VerificationError(
                        f"Decoded WebP frame {frame_index} [{frame_start},{frame_end})ms "
                        f"does not match source PNG {source_index} "
                        f"[{starts[source_index]},{ends[source_index]})ms. "
                        "This can indicate lossy encoding, color conversion, a shifted timestamp, "
                        "or an incorrect frame merge. See pixel_mismatch."
                    )
                compared.append(source_index)
                covered.add(source_index)
                source_index += 1
            require(compared, f"Decoded WebP frame {frame_index} maps to no source PNG interval.")
            frame_reports.append({
                "decoded_frame": frame_index,
                "start_ms": frame_start,
                "duration_ms": duration,
                "source_frames_compared": compared,
                "rgba_sha256": actual_hash,
                "all_rgba_bytes_equal": True,
            })

    report["decoded_duration_ms"] = decoded_elapsed
    report["duration_delta_ms"] = decoded_elapsed - expected_duration
    require(decoded_elapsed == expected_duration,
            f"Decoded WebP duration is {decoded_elapsed}ms; expected {expected_duration}ms "
            f"(difference {decoded_elapsed - expected_duration:+d}ms). Check concat final-frame timing or truncation.")
    require(covered == set(range(len(source_paths))),
            "Some original PNG timeline intervals were never represented in the decoded WebP.")
    report.pop("decoded_duration_ms_so_far", None)
    report.update({
        "status": "passed",
        "all_original_intervals_covered": True,
        "source_intervals_compared": len(covered),
        "decoded_webp_rgba_equals_original_pngs": True,
        "canvas_size_matches": True,
        "total_duration_matches": True,
        "extra_terminal_frame_duration_ms": 0,
        "frames": frame_reports,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frames-dir", type=Path, required=True,
                        help="Retained renderer work directory containing timeline.json and native PNGs")
    parser.add_argument("--output", type=Path, required=True, help="JSON verification report to write")
    parser.add_argument("--repo", type=Path, default=ROOT, help="Repository root (defaults to this script's parent repository)")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".json":
        parser.error("--output must have a .json extension")
    report = {"schema": "tyri.preview-quality-validation.v1", "status": "failed"}
    success = False
    try:
        verify(args, report)
        success = True
    except Exception as error:
        report["error"] = str(error)
        report["decoded_webp_rgba_equals_original_pngs"] = None
    result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    # Protect metadata inputs even on a failure before opening any report file.
    protected = {(args.repo.resolve() / "docs/preview-quality.json").resolve(),
                 (args.frames_dir.resolve() / "timeline.json").resolve()}
    if args.output.resolve() in protected:
        sys.stdout.write(result)
        return 1
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    except OSError as error:
        report["status"] = "failed"
        report["report_write_error"] = str(error)
        result = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        success = False
    sys.stdout.write(result)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
