"""Characterize the generated spec against the committed spec.

``src/spec/create_extension_spec.py`` is the source of truth for
``spec/*.yaml``; the YAML is generated output, never hand-edited. These tests
regenerate it into a temporary directory and compare, so that a change in how
hdmf builds or serializes specs cannot silently alter the published schema.

The generator is exercised by patching the ``export_spec`` name it imported,
which redirects the write without touching the committed files.
"""

import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "spec"
GENERATOR = REPO_ROOT / "src" / "spec" / "create_extension_spec.py"
SPEC_FILES = (
    "ndx-franklab-novela.namespace.yaml",
    "ndx-franklab-novela.extensions.yaml",
)


def _committed_spec_digests():
    """Return digests of the committed spec files.

    Returns
    -------
    dict
        Mapping of filename to the SHA-256 hex digest of its bytes.
    """
    return {
        name: hashlib.sha256((SPEC_DIR / name).read_bytes()).hexdigest()
        for name in SPEC_FILES
    }


# Captured at import, i.e. before any test has had a chance to regenerate.
_DIGESTS_AT_IMPORT = _committed_spec_digests()


def _load_generator():
    """Import the spec generator from its path.

    Returns
    -------
    module
        The imported ``create_extension_spec`` module.

    Notes
    -----
    ``src/spec`` is not an importable package, so the module is loaded
    directly from its file location.
    """
    spec = importlib.util.spec_from_file_location(
        "create_extension_spec", GENERATOR
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def regenerated_spec_dir(tmp_path_factory):
    """Regenerate the spec into a temporary directory.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Factory for the module-scoped output directory.

    Returns
    -------
    pathlib.Path
        Directory holding the freshly generated spec files.
    """
    output_dir = tmp_path_factory.mktemp("regenerated_spec")
    module = _load_generator()
    real_export_spec = module.export_spec

    def export_to_tmp(ns_builder, new_data_types, _output_dir):
        """Redirect the generator's write to the temporary directory."""
        return real_export_spec(ns_builder, new_data_types, str(output_dir))

    module.export_spec = export_to_tmp
    module.main()
    return output_dir


@pytest.mark.parametrize("filename", SPEC_FILES)
def test_regenerated_spec_file_exists(regenerated_spec_dir, filename):
    """The generator writes each expected spec file.

    Parameters
    ----------
    regenerated_spec_dir : pathlib.Path
        Directory of freshly generated spec files.
    filename : str
        Spec file the generator is expected to produce.
    """
    assert (regenerated_spec_dir / filename).is_file()


@pytest.mark.parametrize("filename", SPEC_FILES)
def test_regenerated_spec_matches_committed(regenerated_spec_dir, filename):
    """Regenerating the spec reproduces the committed schema.

    Parameters
    ----------
    regenerated_spec_dir : pathlib.Path
        Directory of freshly generated spec files.
    filename : str
        Spec file to compare.

    Notes
    -----
    The comparison is on the parsed YAML rather than the raw text, so it
    reports genuine schema changes (types, dtypes, docs, shapes) and ignores
    serialization details such as where long strings are wrapped. Byte
    equality would fail today for a reason unrelated to the schema -- see
    :func:`test_committed_spec_differs_from_generated_only_in_trailing_space`.
    """
    regenerated = yaml.safe_load((regenerated_spec_dir / filename).read_text())
    committed = yaml.safe_load((SPEC_DIR / filename).read_text())
    assert regenerated == committed


@pytest.mark.parametrize("filename", SPEC_FILES)
def test_committed_spec_differs_from_generated_only_in_trailing_space(
    regenerated_spec_dir, filename
):
    """Text differences are confined to trailing whitespace.

    Parameters
    ----------
    regenerated_spec_dir : pathlib.Path
        Directory of freshly generated spec files.
    filename : str
        Spec file to compare.

    Notes
    -----
    The YAML emitter leaves a trailing space where it wraps a long string, and
    the committed files do not always carry it. That difference is cosmetic,
    but it means the committed spec is not byte-identical to generator output.
    This test pins the difference down to exactly that, so if serialization
    changes in a more meaningful way -- different wrap points, reordered keys
    -- it is caught rather than absorbed by the semantic comparison above.
    """

    def normalize(text):
        return "\n".join(line.rstrip() for line in text.splitlines())

    regenerated = (regenerated_spec_dir / filename).read_text()
    committed = (SPEC_DIR / filename).read_text()
    assert normalize(regenerated) == normalize(committed)


def test_regenerating_does_not_modify_committed_spec(regenerated_spec_dir):
    """The regeneration fixture leaves the committed spec untouched.

    Parameters
    ----------
    regenerated_spec_dir : pathlib.Path
        Directory of freshly generated spec files.

    Notes
    -----
    Guards the patching in :func:`regenerated_spec_dir`. If the redirect ever
    stopped working, the generator would overwrite ``spec/`` during a test run
    and the damage could go unnoticed until it was committed. The reference
    digests are taken at import time, before any fixture has run.
    """
    assert not regenerated_spec_dir.samefile(SPEC_DIR)
    assert _committed_spec_digests() == _DIGESTS_AT_IMPORT
