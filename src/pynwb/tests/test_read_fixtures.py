"""Read NWB files written by the pre-migration stack.

This is the backward-compatibility guard for the pynwb 4 / hdmf 6 upgrade.
Spyglass has years of files on disk written by earlier releases; if the
upgrade breaks reading them, that is a release blocker rather than a detail.

The fixtures live in ``src/pynwb/tests/fixtures/``. They are not checked in;
CI rebuilds them each run by executing ``make_fixtures.py`` in a throwaway
environment pinned to the pre-upgrade stack (``fixture-stack.txt``), so the
files these tests read were genuinely written by older pynwb/hdmf than the
ones reading them. These tests skip rather than fail when the files are
absent, so a checkout that has not run the generator still runs the rest of
the suite.
"""

import json

import pytest
from pynwb import NWBHDF5IO

from ndx_franklab_novela import (
    AssociatedFiles,
    CameraDevice,
    DataAcqDevice,
    HeaderDevice,
    NwbElectrodeGroup,
    Probe,
)

ALL_TYPES_FIXTURE = "all_types_0.2.4.nwb"
OPTOGENETICS_FIXTURE = "optogenetics_0.2.4.nwb"


@pytest.fixture
def all_types_fixture(baseline_fixture_dir):
    """Return the path of the all-types fixture.

    Parameters
    ----------
    baseline_fixture_dir : pathlib.Path
        Directory holding the archived fixtures.

    Returns
    -------
    pathlib.Path
        Path of the fixture file.
    """
    path = baseline_fixture_dir / ALL_TYPES_FIXTURE
    if not path.is_file():
        pytest.skip(f"missing fixture {path}")
    return path


@pytest.fixture
def optogenetics_fixture(baseline_fixture_dir):
    """Return the path of the optogenetics fixture.

    Parameters
    ----------
    baseline_fixture_dir : pathlib.Path
        Directory holding the archived fixtures.

    Returns
    -------
    pathlib.Path
        Path of the fixture file.
    """
    path = baseline_fixture_dir / OPTOGENETICS_FIXTURE
    if not path.is_file():
        pytest.skip(f"missing fixture {path}")
    return path


def test_fixture_stack_is_recorded(baseline_fixture_dir):
    """The fixtures carry a manifest of the stack that wrote them.

    Parameters
    ----------
    baseline_fixture_dir : pathlib.Path
        Directory holding the archived fixtures.

    Notes
    -----
    Without this, a passing read test says nothing about *which* stack wrote
    the file it read.
    """
    manifest = baseline_fixture_dir / "stack.json"
    if not manifest.is_file():
        pytest.skip(f"missing manifest {manifest}")
    stack = json.loads(manifest.read_text())
    assert "pynwb" in stack
    assert "hdmf" in stack
    assert stack["ndx-franklab-novela"]


def test_read_all_types_fixture(all_types_fixture):
    """Every type in a pre-migration file reads back with its values.

    Parameters
    ----------
    all_types_fixture : pathlib.Path
        Fixture written by the pre-migration stack.
    """
    with NWBHDF5IO(str(all_types_fixture), mode="r") as io:
        nwbfile = io.read()

        header = nwbfile.devices["header_device"]
        assert isinstance(header, HeaderDevice)
        assert header.qt_version == "Sample qt_version"

        full = nwbfile.devices["data_acq_device_full"]
        assert isinstance(full, DataAcqDevice)
        assert full.amplifier == "Amplifier1"
        assert nwbfile.devices["data_acq_device_min"].amplifier is None

        camera = nwbfile.devices["camera_device"]
        assert isinstance(camera, CameraDevice)
        assert camera.frame_rate == 30.0
        assert camera.meters_per_pixel == 0.20

        probe = nwbfile.devices["probe"]
        assert isinstance(probe, Probe)
        assert probe.contact_side_numbering
        electrode = probe.shanks["0"].shanks_electrodes["1"]
        assert electrode.rel_z == 6.0

        group = nwbfile.electrode_groups["nwb_electrode_group"]
        assert isinstance(group, NwbElectrodeGroup)
        assert group.targeted_location == "mPFC"

        associated = nwbfile.processing["associated_files"]["file1"]
        assert isinstance(associated, AssociatedFiles)
        assert associated.task_epochs == "1, 2"


def test_read_optogenetics_fixture(optogenetics_fixture):
    """A pre-migration FrankLabOptogeneticEpochsTable reads back intact.

    Parameters
    ----------
    optogenetics_fixture : pathlib.Path
        Fixture written by the pre-migration stack.

    Notes
    -----
    Exercises the type with the largest surface -- and the one most exposed to
    hdmf's spec-resolution changes, since its columns refine ``VectorData``.
    """
    with NWBHDF5IO(str(optogenetics_fixture), mode="r") as io:
        nwbfile = io.read()
        epochs = nwbfile.intervals["optogenetic_epochs"]

        assert epochs[0, "start_time"] == 0.0
        assert epochs[0, "stop_time"] == 100.0
        assert epochs[0, "stimulation_on"]
        assert epochs[0, "power_in_mW"] == 100.0
        assert epochs[0, "epoch_name"] == "20220911_Wallie_01_sleep"
        assert epochs[0, "epoch_type"] == "sleep"
        assert epochs[0, "theta_filter_lockout_period_in_samples"] == 10
        assert epochs[0, "ripple_filter_num_above_threshold"] == 4
        assert epochs[0, "speed_filter_on_above_threshold"]
        assert epochs[0, "wavelength_in_nm"] == 450.0


def test_optogenetics_fixture_camera_references(optogenetics_fixture):
    """The stored camera references still resolve to CameraDevice objects.

    Parameters
    ----------
    optogenetics_fixture : pathlib.Path
        Fixture written by the pre-migration stack.
    """
    with NWBHDF5IO(str(optogenetics_fixture), mode="r") as io:
        nwbfile = io.read()
        epochs = nwbfile.intervals["optogenetic_epochs"]
        cameras = epochs[0, "spatial_filter_cameras"]
        assert [c.name for c in cameras] == [
            "overhead_run_camera 1",
            "overhead_run_camera 2",
        ]
        assert all(isinstance(c, CameraDevice) for c in cameras)
