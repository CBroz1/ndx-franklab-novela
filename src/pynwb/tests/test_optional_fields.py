"""Characterize which fields are optional.

Several fields were made optional in past releases (``CameraDevice`` gained
``frame_rate`` in 0.2.0, ``Probe.contact_side_numbering`` became optional in
0.2.1, ``speed_filter_on_above_threshold`` in 0.2.2). Optionality is asserted
two ways: the spec declares ``required: false``, and omitting the field at
construction leaves it ``None`` instead of raising.
"""

import pytest
import yaml

from ndx_franklab_novela import CameraDevice, DataAcqDevice, Probe

from .conftest import EXTENSIONS_FILE, SPEC_DIR

# (data type, attribute) pairs the spec must continue to mark optional.
OPTIONAL_ATTRIBUTES = [
    ("CameraDevice", "frame_rate"),
    ("DataAcqDevice", "amplifier"),
    ("DataAcqDevice", "adc_circuit"),
    ("Probe", "contact_side_numbering"),
]

# Columns of FrankLabOptogeneticEpochsTable that must stay optional, i.e. must
# not be created up front by the constructor.
OPTIONAL_OPTO_COLUMNS = [
    "speed_filter_on",
    "speed_filter_threshold_in_cm_per_s",
    "speed_filter_on_above_threshold",
    "theta_filter_on",
    "ripple_filter_on",
    "spatial_filter_on",
    "stimulus_signal",
]


@pytest.fixture(scope="module")
def extensions_spec():
    """Return the parsed extensions spec.

    Returns
    -------
    dict
        Contents of the committed extensions YAML.
    """
    return yaml.safe_load((SPEC_DIR / EXTENSIONS_FILE).read_text())


def _attributes(spec, type_name):
    """Return a data type's attributes, keyed by name.

    Parameters
    ----------
    spec : dict
        Parsed extensions spec.
    type_name : str
        Neurodata type to look up.

    Returns
    -------
    dict
        Mapping of attribute name to its spec dictionary.
    """
    for group in spec["groups"]:
        if group.get("neurodata_type_def") == type_name:
            return {a["name"]: a for a in group.get("attributes", [])}
    raise AssertionError(f"{type_name} not found in the extensions spec")


@pytest.mark.parametrize(
    ("type_name", "attribute"),
    OPTIONAL_ATTRIBUTES,
    ids=[f"{t}.{a}" for t, a in OPTIONAL_ATTRIBUTES],
)
def test_spec_marks_attribute_optional(extensions_spec, type_name, attribute):
    """The spec declares the attribute ``required: false``.

    Parameters
    ----------
    extensions_spec : dict
        Parsed extensions spec.
    type_name : str
        Neurodata type owning the attribute.
    attribute : str
        Attribute expected to be optional.
    """
    attributes = _attributes(extensions_spec, type_name)
    assert attribute in attributes
    assert attributes[attribute].get("required", True) is False


def test_camera_device_without_frame_rate():
    """A CameraDevice can be built without ``frame_rate``."""
    device = CameraDevice(
        name="camera",
        description="Camera used for tracking running",
        meters_per_pixel=0.20,
        camera_name="test name",
        lens="500dpt",
    )
    assert device.frame_rate is None


def test_data_acq_device_without_optional_attributes():
    """A DataAcqDevice can be built with only ``system``."""
    device = DataAcqDevice(name="daq", system="System1")
    assert device.amplifier is None
    assert device.adc_circuit is None


def test_probe_without_contact_side_numbering():
    """A Probe can be built without ``contact_side_numbering``."""
    device = Probe(
        id=1,
        name="probe",
        probe_type="type_1",
        units="um",
        probe_description="sample description",
        contact_size=1.0,
    )
    assert device.contact_side_numbering is None


@pytest.mark.parametrize("column", OPTIONAL_OPTO_COLUMNS)
def test_optogenetic_epochs_optional_columns_absent_by_default(column):
    """Optional filter columns are not created up front.

    Parameters
    ----------
    column : str
        Column expected to be absent from a freshly built table.

    Notes
    -----
    ``add_row`` requires a value for every column that already exists on the
    table, so a column being absent here *is* what makes it optional. Building
    the table needs none of the ndx-optogenetics scaffolding, which keeps this
    check independent of that dependency's own migration state.
    """
    from ndx_franklab_novela import FrankLabOptogeneticEpochsTable

    table = FrankLabOptogeneticEpochsTable(
        name="optogenetic_epochs",
        description="Metadata about the optogenetic stimulation parameters.",
    )
    assert column not in table.colnames
