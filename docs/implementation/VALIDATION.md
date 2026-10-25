# Implementation validation — 2026-10-25

## Executed successfully

- Created a new Python 3.12 virtual environment outside the source checkout; installed all application requirements from the configured package index with normal TLS verification.
- `python -m pip check`: no broken requirements.
- 15 unittest cases completed and passed, including real raster uploads, permission gating, structure-edit versioning, traditional-mode structure locking, export archives, image transparency, dimensions, evidence binding and raw-metadata SHA-256 verification.
- Started Uvicorn from the new environment; used Chromium to navigate the actual HTTP application, load the procedural demo, create a 2x2 repeat, inspect output and download the design ZIP (12,594 bytes).
- Browser JavaScript errors: 0. At 390-pixel viewport, document width did not overflow. Screenshots: `desktop.png` and `mobile.png`.
- JavaScript syntax checked with `node --check`.
- Built source ZIP, verified ZIP integrity and absence of runtime data / virtualenv / Git metadata, extracted into a separate directory and ran all 15 tests there successfully.

## Data acquisition

- Source: Cooper Hewitt, Smithsonian Design Museum official `cooperhewitt/collection` GitHub repository.
- Listed 194,330 object JSON paths, sampled 240 at a fixed deterministic interval, fetched all 240 successfully, retained 28 matching relevant metadata terms. Source commit and per-record hashes are checked in.
- Retrieved and preserved official CC0 metadata licensing and README. No museum images downloaded; source policy explicitly excludes images from this metadata dedication.
- UNESCO, Met collection API, Art Institute site and Wikipedia API returned proxy 403 in this environment. Met's GitHub usage policy was readable; its large CSV was an LFS pointer and the media endpoint was blocked. No data from those failed requests is represented as imported.

## Not validated / not implemented

- Windows native execution and Docker image build have not been run on their target systems.
- Optional Met API import cannot be validated online under the current network policy.
- No trained heritage classifier, diffusion model, semantic cultural validation, expert cultural review, production load test or physical manufacturing test.
- Geometric demo is original synthetic geometry, not a museum image or heritage training sample.

This record describes a functional local prototype and its checks, not proof of the final research targets in the technical plan.
