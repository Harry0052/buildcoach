# Overlap review

Access date for every source below: 2026-11-23.

Decision: **proceed**. BuildCoach stays a separate repository. No existing workflow meets the acceptance case on an original still-photo fixture without a paid service or a non-commercial dataset.

## Acceptance case held constant

The comparison uses one metric and one expected artifact.

- Input: one practice step whose required tag is hidden, then the same step with the missing view added.
- Expected artifact when the tag is hidden in every supplied view: a named view request and zero step completions.
- Clear, consistent views of a correct layout may complete. That count is reported separately and is not mixed into the zero-completion gate.
- Contradictory clean views must request a retake and must not keep the higher-confidence image.

The smallest shared picture used for the observed probe is an original `DICT_4X4_50` tag (id 0, 200 px) on a 480×640 light canvas, the same canvas with that rectangle covered by flat gray, and the visible canvas rotated 90° clockwise. Observed numbers are in `docs/research/p01-aruco-probe.json`.

## Capability matrix

| Project | Primary URL | Version or commit | License and data terms | Evidence | Named view request and zero completions on a hidden tag | Relative tag orientation on still photos | Runs locally without a paid API |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Epoch AI Furniture Assembly Benchmark | https://epoch.ai/benchmarks/furniture-assembly | No software release. Human baseline published for September 2026 (average 63% on 60 photos). | Research page. IKEA photos and manuals are copyrighted. Epoch does not distribute them. | Documentation | No. One photo per item. The mistake must already be clearly visible. No second-photo class. | Not a fiducial or orientation protocol. | No. Model APIs and a paid grader. |
| Assembly101 | https://assembly-101.github.io/ and https://github.com/assembly-101/assembly101-mistake-detection | CVPR 2022 paper. Mistake annotations released August 2023. | CC BY-NC 4.0. Non-commercial. Not imported. | Documentation | No. Labels are time segments, not a request for a named angle. | Misorientation is annotated in later work and was left out of the method scope (Ding et al., arXiv:2307.16453). | Dataset download and trained video models. Not this fixture. |
| AssemblyGuard | https://github.com/ArmmyC/assemblyguard | `60204ed030e67f0be8dc5f494d36c1ab3cab46d7` (2026-11-04, branch `master`) | No license file (GitHub `license` is null). Not reused. | Documentation | Partial, and not on this fixture. A detection explicitly marked occluded stays `UNKNOWN` and asks for an unobstructed view. The README says the SAM parser does not emit per-object occlusion labels. | Not ArUco relative orientation. | No. Live mode needs `MODEL_API_KEY` and calls Muse / SAM. |
| AssemLens | https://github.com/Akashkumarsenthil/assemlens | `b478fb5f10601530085ffbb923e38e2d46ff2bd1` (2026-09-24, branch `main`) | No license file. Not reused. | Documentation, including `assemlens/policy.py` | Partial. `clear_view` false routes to `RECAPTURE` with the reason "Insufficient visual evidence: ask for another angle." The request is not a named kit angle, and the policy does not see pixels. | Not in the policy. The visual model is a separate, unmeasured GPU pilot. | The policy function is local. The checker that would set `clear_view` is not. |
| Visionary | https://github.com/terrencefu/Visionary | `0d58c1c6edce4a9cac65c69c2cfc96a02bfc01fa` (2026-09-22, branch `main`) | No license file. Not reused. | Documentation | Uncertain. The README says the camera can report that there is not enough visible evidence. It does not specify a named angle or a zero-completion gate. | ArUco is used to register a board and a movable base, not to identify the practice parts. Detection photos are labeled "identity not checked." | Needs the camera–projector rig. |
| StepWitness | https://github.com/spala-ai/stepwitness | `bfbdd8bedd20665627fdc98c62b78bbb8bf8eab4` (2026-11-03, branch `master`) | MIT | Documentation | No. Flags wrong-order video steps. | README: wrong position or orientation was 0 of 5. | No. Meta API, default spend cap 10 USD. |
| ProcessLens | https://github.com/DravenDou/processlens | `2bbf3572d0a6b919b3d23f5abee79a2fcbf77a7f` (2026-11-03, branch `main`) | MIT | Documentation | No. Video findings are `missing`, `wrong-order`, or `misplaced`. | Not a still-photo fiducial protocol. | Depends on SAM and Muse Spark. |
| OpenCV ArUco | https://github.com/opencv/opencv/releases/tag/4.12.0 and https://pypi.org/project/opencv-python-headless/4.12.0.88/ | OpenCV tag `4.12.0` (2025-07-02). Wheel `opencv-python-headless==4.12.0.88`. | OpenCV 4.5.0+ is Apache-2.0 (https://opencv.org/license/). Wrapper scripts are MIT. Wheels also ship FFmpeg under LGPLv2.1. | Observed run | No. Covered tag → `ids []`. No request object and no completion flag. | Corner order is available. A 90° roll kept id 0. Relative step rules are not in the library. | Yes. This is the detection dependency, not a product that covers the case. |

TrueMeasure (calibrated geometry) and HardwareBridge (firmware response to simulated faults) are scope boundaries from the playbook, not candidates. A search on 2026-11-23 did not find a public project under those names that already performs this still-photo evidence protocol. MIT Biomimetics’ `HardwareBridge.cpp` is a robot hardware interface and does not check assembly photographs.

## Probes

### Observed: OpenCV ArUco on the shared fixture

Command, from a throwaway directory, not from the product environment:

```text
pip install --target /tmp/p01-cv opencv-python-headless==4.12.0.88
PYTHONPATH=/tmp/p01-cv python3
```

The script drew tag 0, covered it with gray, and rotated the visible image 90° clockwise. Runtime `cv2.__version__` was `4.12.0`.

| Case | Observed ids | Named view request | Completions |
| --- | --- | --- | --- |
| Visible | `[0]` | none | none |
| Covered | `[]` | none | none |
| Rolled 90° | `[0]` | none | none |

The probe exited `PROBE_OK`. OpenCV can tell a present tag from a covered tag and can keep the id when the camera rolls. It does not produce the acceptance artifact. That gap is the MVP.

### Documentation: nearest products on the same artifact

These were not executed. AssemblyGuard, AssemLens, Visionary, StepWitness, and ProcessLens either have no license or call a paid model API. The playbook forbids paid services, and an unlicensed tree was not copied or run. Epoch’s photos and Assembly101’s videos were not downloaded.

Against the same expected artifact (named view, zero completions when the required feature is hidden):

- Epoch scores a yes/no mistake decision on a photo where the error is already visible. A hidden feature is outside the published task.
- Assembly101’s mistake files are segment rows: `start`, `end`, `verb`, `this`, `that`, `label`, `remark`. Remarks include wrong order, unnecessary detach, and wrong position. There is no label whose meaning is "ask for the left side." Original Assembly101 action labels were one verb plus one noun; Ding, Sener, Ma, and Yao (arXiv:2307.16453, https://arxiv.org/abs/2307.16453) show that those labels collide across different part pairs. Their later part-to-part labels fix that ambiguity and still do not record a missing camera angle. Simultaneous multi-view capture is not the same as withholding completion until a named view arrives. An original still-photo protocol is a useful fixture. The CC BY-NC videos stay out of this repository.
- AssemblyGuard’s occlusion request depends on an occlusion flag the current parser does not produce.
- AssemLens asks for "another angle" only after some other component has set `clear_view` to false. The published policy text was read. It was not vendored.
- Visionary, StepWitness, and ProcessLens do not publish this artifact.

## What already matches

- OpenCV already detects ArUco ids and ordered corners under Apache-2.0.
- Several prototypes already abstain or say the view is unclear. None of them tie that abstention to a kit manifest, a named angle, and a hard ban on completion for this still-photo case without a paid model.
- Assembly101 and Epoch already study assembly mistakes. Their labels and licenses do not supply the default fixture.

## Remaining uncertainties

- Phone photos of a printed kit are not part of this evidence. The MVP can prove the protocol on authored images only.
- OpenCV 5.1.0.95 is on PyPI. The ArUco tutorial used here is the 4.7+ `ArucoDetector` API. The build pins 4.12.0.88 rather than assuming 5.x.
- Nearby repositories with `license: null` might add a license later. Nothing was copied from them.
- Pose in millimetres under lens distortion is intentionally out of scope (that would be a measurement product).

## Decision

Proceed with a narrow MVP:

- One original non-load-bearing tabletop kit, three steps, printed tags.
- Local images only. No account, no model API, no dataset download at runtime.
- OpenCV ArUco for id and corners. Rules in typed kit JSON. pytest. A small local upload page.
- Complete a step only when every required rule is supported by consistent views.
- If the required tags are not co-visible, name the view that would show them and complete nothing.
- If clean views disagree, ask for a retake and do not keep the larger detection.

Do not integrate or contribute the acceptance case into AssemblyGuard, AssemLens, Visionary, StepWitness, or ProcessLens. Those projects either cannot be reused under a known license, require a paid API, or check a different artifact (video order, projector alignment, or a single already-clear photo).
