"""Validate written files against the cached namespaces.

A file holding every extension type must pass ``pynwb.validate`` cleanly. This
catches specs that build and write but describe something the validator
rejects -- the failure mode most likely to appear when hdmf changes how specs
are resolved.
"""

import pynwb
from pynwb import NWBHDF5IO


def test_all_types_file_validates(written_nwb_path):
    """A file containing every extension type validates without errors.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.

    Notes
    -----
    Uses the singular ``path`` argument. The plural ``paths`` form still works
    on pynwb 3 but is removed in pynwb 4, so this call stays valid across the
    migration.
    """
    errors = pynwb.validate(path=str(written_nwb_path))
    assert errors == []


def test_extension_namespace_is_cached_in_file(written_nwb_path):
    """The extension namespace is embedded in the written file.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.

    Notes
    -----
    Files are routinely read on machines without this package installed, and
    validation relies on the cached namespace. If caching regressed, files
    would still write but would no longer be self-describing. The dependency
    namespaces are asserted too: ndx-optogenetics must travel with the file
    for ``FrankLabOptogeneticEpochsTable`` to be resolvable.
    """
    namespaces = NWBHDF5IO.get_namespaces(path=str(written_nwb_path))
    assert "ndx-franklab-novela" in namespaces
    assert "ndx-optogenetics" in namespaces
    assert "core" in namespaces


def test_validation_uses_the_extension_namespace(written_nwb_path):
    """Validating against this namespace explicitly also passes.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        errors = pynwb.validate(io=io, namespace="ndx-franklab-novela")
    assert errors == []
