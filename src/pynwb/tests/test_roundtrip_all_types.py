"""Round-trip every neurodata type through an NWB file.

Writes one file containing all extension types, reads it back, and checks the
values survive. This is the broadest guard against the pynwb 4 / hdmf 6
upgrade changing how these types are built, written, or read.
"""

import numpy as np
from pynwb import NWBHDF5IO

from ndx_franklab_novela import (
    AssociatedFiles,
    CameraDevice,
    DataAcqDevice,
    HeaderDevice,
    NwbElectrodeGroup,
    Probe,
    Shank,
    ShanksElectrode,
)


def test_header_device_roundtrip(written_nwb_path):
    """A HeaderDevice keeps its attributes across write and read.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        read = io.read().devices["header_device"]
        assert isinstance(read, HeaderDevice)
        assert read.headstage_serial == "Sample headstage_serial"
        assert read.qt_version == "Sample qt_version"
        assert read.file_path == "Sample file_path"
        assert read.system_time_at_creation == "Sample system_time_at_creation"


def test_data_acq_device_roundtrip(written_nwb_path):
    """DataAcqDevice round-trips with and without its optional fields.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        devices = io.read().devices

        full = devices["data_acq_device_full"]
        assert isinstance(full, DataAcqDevice)
        assert full.system == "System1"
        assert full.amplifier == "Amplifier1"
        assert full.adc_circuit == "adc_circuit1"

        minimal = devices["data_acq_device_min"]
        assert minimal.system == "System1"
        assert minimal.amplifier is None
        assert minimal.adc_circuit is None


def test_camera_device_roundtrip(written_nwb_path):
    """A CameraDevice keeps its attributes and its DeviceModel link.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        read = io.read().devices["camera_device"]
        assert isinstance(read, CameraDevice)
        assert read.meters_per_pixel == 0.20
        assert read.camera_name == "test name"
        assert read.lens == "500dpt"
        assert read.frame_rate == 30.0
        assert read.model.name == "ndx2000"
        assert read.model.manufacturer == "sony"


def test_probe_nesting_roundtrip(written_nwb_path):
    """Probe -> Shank -> ShanksElectrode nesting survives a round trip.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        read = io.read().devices["probe"]
        assert isinstance(read, Probe)
        assert read.id == 1
        assert read.probe_type == "type_1"
        assert read.units == "um"
        assert read.probe_description == "sample description"
        assert read.contact_side_numbering
        assert read.contact_size == 1.0

        shank = read.shanks["0"]
        assert isinstance(shank, Shank)
        assert set(shank.shanks_electrodes) == {"0", "1"}

        electrode = shank.shanks_electrodes["1"]
        assert isinstance(electrode, ShanksElectrode)
        assert electrode.rel_x == 4.0
        assert electrode.rel_y == 5.0
        assert electrode.rel_z == 6.0


def test_nwb_electrode_group_roundtrip(written_nwb_path):
    """An NwbElectrodeGroup keeps its targeting metadata.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        read = io.read().electrode_groups["nwb_electrode_group"]
        assert isinstance(read, NwbElectrodeGroup)
        assert read.location == "Sample location"
        assert read.targeted_location == "mPFC"
        assert read.targeted_x == 1.0
        assert read.targeted_y == 2.0
        assert read.targeted_z == 3.0
        assert read.units == "um"
        np.testing.assert_array_equal(
            np.asarray(read.position).tolist(),
            np.array(
                (1.0, 2.0, 3.0),
                dtype=[("x", "<f8"), ("y", "<f8"), ("z", "<f8")],
            ).tolist(),
        )


def test_associated_files_roundtrip(written_nwb_path):
    """AssociatedFiles round-trips inside a ProcessingModule.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        read = io.read().processing["associated_files"]["file1"]
        assert isinstance(read, AssociatedFiles)
        assert read.description == "description of file1"
        assert read.content == "1 2 3 content of file test"
        assert read.task_epochs == "1, 2"


def test_electrode_group_device_link_roundtrip(written_nwb_path):
    """The electrode group still points at the Probe after a round trip.

    Parameters
    ----------
    written_nwb_path : pathlib.Path
        File containing every extension type.

    Notes
    -----
    Spyglass resolves probe metadata by following this link, so a break here
    would surface as missing probe information rather than an obvious error.
    """
    with NWBHDF5IO(str(written_nwb_path), mode="r") as io:
        nwbfile = io.read()
        group = nwbfile.electrode_groups["nwb_electrode_group"]
        assert group.device is nwbfile.devices["probe"]
