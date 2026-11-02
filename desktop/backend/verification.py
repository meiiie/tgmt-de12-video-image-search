"""Local image-detail correspondence, separate from semantic similarity."""
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MAX_CANDIDATES = 48


@dataclass
class Features:
    rgb: np.ndarray
    points: np.ndarray
    descriptors: np.ndarray | None


def extract_features(image):
    image = image.convert("RGB").copy()
    image.thumbnail((960, 960))
    rgb = np.asarray(image)
    keypoints, descriptors = cv2.SIFT_create(nfeatures=1800).detectAndCompute(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), None)
    points = np.asarray([key.pt for key in keypoints], dtype=np.float32).reshape(-1, 2)
    return Features(rgb, points, descriptors)


def compare_features(query, candidate):
    result = {"status": "unconfirmed", "reason": "insufficient_detail", "inliers": 0,
              "coverage": 0.0, "agreement": 0.0, "quality": 0.0}
    if len(query.points) < 10 or len(candidate.points) < 10:
        return result
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    pairs = matcher.knnMatch(query.descriptors, candidate.descriptors, k=2)
    reverse = {m.queryIdx: m.trainIdx for m in matcher.match(candidate.descriptors, query.descriptors)}
    good, occupied_query, occupied_target = [], set(), set()
    for pair in pairs:
        if len(pair) != 2:
            continue
        m, runner_up = pair
        a = tuple(np.floor(query.points[m.queryIdx] / 2).astype(int))
        b = tuple(np.floor(candidate.points[m.trainIdx] / 2).astype(int))
        if m.distance < .75 * runner_up.distance and reverse.get(m.trainIdx) == m.queryIdx and a not in occupied_query and b not in occupied_target:
            good.append(m)
            occupied_query.add(a)
            occupied_target.add(b)
    result["reason"] = "insufficient_correspondence"
    if len(good) < 10:
        return result
    source = np.float32([query.points[m.queryIdx] for m in good])
    target = np.float32([candidate.points[m.trainIdx] for m in good])
    transform, mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
    if transform is None or mask is None or not np.isfinite(transform).all():
        return result
    inliers = source[mask.ravel().astype(bool)]
    height, width = query.rgb.shape[:2]
    coverage = cv2.contourArea(cv2.convexHull(inliers)) / (width * height) if len(inliers) >= 3 else 0
    result.update(inliers=len(inliers), coverage=float(coverage))
    if len(inliers) < 10 or len(inliers) / len(good) < .45 or coverage < .2:
        return result
    corners = np.float32([[0, 0], [width-1, 0], [width-1, height-1], [0, height-1]]).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(corners, transform)
    if not np.isfinite(projected).all() or not cv2.isContourConvex(projected):
        return result
    area = abs(cv2.contourArea(projected))
    if not 16 <= area <= candidate.rgb.shape[0] * candidate.rgb.shape[1] * 4:
        return result
    try:
        inverse = np.linalg.inv(transform)
    except np.linalg.LinAlgError:
        return result
    valid = cv2.warpPerspective(np.full(candidate.rgb.shape[:2], 255, np.uint8), inverse, (width, height)) > 250
    if valid.mean() < .85:
        return result
    aligned = cv2.warpPerspective(candidate.rgb, inverse, (width, height))
    original = cv2.GaussianBlur(query.rgb, (5, 5), 0).astype(np.float32)
    aligned = cv2.GaussianBlur(aligned, (5, 5), 0).astype(np.float32)
    agreement = float((np.abs(original - aligned).mean(axis=2)[valid] <= 40).mean())
    result.update(agreement=agreement, quality=float(coverage * agreement * min(1, len(inliers) / 40)))
    if agreement < .55:
        result["reason"] = "appearance_changed"
        return result
    result.update(status="matched", reason="detail_correspondence")
    return result


class FrameDetails:
    def __init__(self, root: Path):
        self.root = root
        self.cache = OrderedDict()

    def get(self, row):
        key = (row["video_id"], row["fingerprint"], row["t"])
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        path = self.root / "details" / row["thumb"]
        if path.is_file():
            with Image.open(path) as image:
                features = extract_features(image)
        else:
            cap = cv2.VideoCapture(row["path"])
            try:
                if not cap.isOpened() or not cap.set(cv2.CAP_PROP_POS_MSEC, row["t"] * 1000):
                    raise OSError("Không đọc được khung nguồn để đối chiếu")
                ok, frame = cap.read()
                if not ok or abs(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - row["t"]) > .1:
                    raise OSError("Không đọc đúng mốc khung nguồn để đối chiếu")
                features = extract_features(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            finally:
                cap.release()
        self.cache[key] = features
        if len(self.cache) > 64:
            self.cache.popitem(last=False)
        return features
