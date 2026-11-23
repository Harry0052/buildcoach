# Third-party notices

BuildCoach does not vendor these packages. `pip install` fetches them. Versions are pinned in `pyproject.toml`.

| Package | Version | License | Role |
| --- | --- | --- | --- |
| OpenCV | 4.12.0 (wheel `opencv-python-headless==4.12.0.88`) | Apache-2.0 for OpenCV 4.5.0 and later. https://opencv.org/license/ | ArUco detection |
| opencv-python wrapper scripts | 4.12.0.88 | MIT. https://github.com/opencv/opencv-python | Python packaging |
| FFmpeg, shipped inside the OpenCV wheel | as bundled by that wheel | LGPLv2.1 | Image decode inside the wheel. Not distributed from this git repository. |
| NumPy | 2.2.6 | BSD-3-Clause | Array dependency of the OpenCV wheel |
| pytest | 8.4.2 | MIT | Tests only |
| ruff | 0.14.14 | MIT | Lint only |

The `DICT_4X4_50` bit patterns are generated locally from that OpenCV build. No OpenCV sample photos are included.

Fixture photographs, the guide, and the tag sheets are original and use the repository MIT license. See `src/buildcoach/fixtures/MANIFEST.json`.
