"""Write NWB fixture files with the pre-upgrade pynwb/hdmf stack.

The files this writes are the backward-compatibility guard for the pynwb 4 /
hdmf 6 upgrade: the upgraded stack must still read them, because spyglass has
years of files written by the current stack sitting on disk.

This is a generator, not a test -- pytest does not collect it. It must run
against the *old* stack, in an environment separate from the one that runs the
tests; fixtures written and read by the same versions would only prove
round-tripping. CI does this automatically (see the fixture-generation step in
``.github/workflows/run_all_tests.yml``). To reproduce it by hand::

    python -m venv .fixture-env
    .fixture-env/bin/python -m pip install \\
        -r src/pynwb/tests/fixture-stack.txt .
    .fixture-env/bin/python src/pynwb/tests/make_fixtures.py

Writes into ``src/pynwb/tests/fixtures/`` alongside a ``stack.json`` recording
the package versions that produced the files. The output is gitignored --
these are build products, not checked-in binaries -- so ``test_read_fixtures``
skips until this has run.
"""

import json
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from pynwb import NWBHDF5IO, NWBFile, ProcessingModule
from pynwb.device import DeviceModel
from pynwb.testing.mock.base import mock_TimeSeries
from pynwb.testing.mock.file import mock_NWBFile

from ndx_ophys_devices import (
    Effector,
    ExcitationSource,
    ExcitationSourceModel,
    FiberInsertion,
    OpticalFiber,
    OpticalFiberModel,
    ViralVector,
    ViralVectorInjection,
)
from ndx_optogenetics import (
    OptogeneticEffectors,
    OptogeneticExperimentMetadata,
    OptogeneticSitesTable,
    OptogeneticViruses,
    OptogeneticVirusInjections,
)

from ndx_franklab_novela import (
    AssociatedFiles,
    CameraDevice,
    DataAcqDevice,
    FrankLabOptogeneticEpochsTable,
    HeaderDevice,
    NwbElectrodeGroup,
    Probe,
    Shank,
    ShanksElectrode,
)

OUT_DIR = Path(__file__).parent / "fixtures"
# Fixed timestamp: fixtures should differ between runs only when the stack
# that wrote them differs.
SESSION_START = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def build_nwbfile() -> NWBFile:
    """Assemble one NWBFile holding every type this extension defines.

    Returns
    -------
    NWBFile
        File containing a HeaderDevice, DataAcqDevice, CameraDevice, Probe
        (with Shank and ShanksElectrode children), NwbElectrodeGroup, and an
        AssociatedFiles inside a ProcessingModule.
    """
    nwbfile = NWBFile(
        session_description="ndx-franklab-novela migration fixture",
        identifier="ndx-franklab-novela-fixture-0.2.4",
        session_start_time=SESSION_START,
    )

    nwbfile.add_device(
        HeaderDevice(
            name="header_device",
            headstage_serial="Sample headstage_serial",
            headstage_smart_ref_on="Sample headstage_smart_ref_on",
            realtime_mode="Sample realtime_mode",
            headstage_auto_settle_on="Sample headstage_auto_settle_on",
            timestamp_at_creation="Sample timestamp_at_creation",
            controller_firmware_version="Sample controller_firmware_version",
            controller_serial="Sample controller_serial",
            save_displayed_chan_only="Sample save_displayed_chan_only",
            headstage_firmware_version="Sample headstage_firmware_version",
            qt_version="Sample qt_version",
            compile_date="Sample compile_date",
            compile_time="Sample compile_time",
            file_prefix="Sample file_prefix",
            headstage_gyro_sensor_on="Sample headstage_gyro_sensor_on",
            headstage_mag_sensor_on="Sample headstage_mag_sensor_on",
            trodes_version="Sample trodes_version",
            headstage_accel_sensor_on="Sample headstage_accel_sensor_on",
            commit_head="Sample commit_head",
            system_time_at_creation="Sample system_time_at_creation",
            file_path="Sample file_path",
        )
    )

    # Both the with- and without-optional-fields forms, since
    # `amplifier`/`adc_circuit` are optional in the spec.
    nwbfile.add_device(
        DataAcqDevice(
            name="data_acq_device_full",
            system="System1",
            amplifier="Amplifier1",
            adc_circuit="adc_circuit1",
        )
    )
    nwbfile.add_device(
        DataAcqDevice(name="data_acq_device_min", system="System1")
    )

    camera_model = DeviceModel(
        name="ndx2000", manufacturer="sony", model_number="ndx2000"
    )
    nwbfile.add_device_model(camera_model)
    nwbfile.add_device(
        CameraDevice(
            name="camera_device",
            description="Camera used for tracking running",
            meters_per_pixel=0.20,
            camera_name="test name",
            model=camera_model,
            lens="500dpt",
            frame_rate=30.0,  # optional since 0.2.0
        )
    )

    probe = Probe(
        id=1,
        name="probe",
        probe_type="type_1",
        units="um",
        probe_description="sample description",
        contact_side_numbering=True,  # optional since 0.2.1
        contact_size=1.0,
    )
    shank = Shank(name="0")
    # Deliberately via the back-compat aliases, so the fixture also proves the
    # aliases were exercised on the old stack.
    shank.add_shanks_electrode(
        ShanksElectrode(name="0", rel_x=1.0, rel_y=2.0, rel_z=3.0)
    )
    shank.add_shanks_electrode(
        ShanksElectrode(name="1", rel_x=4.0, rel_y=5.0, rel_z=6.0)
    )
    probe.add_shank(shank)
    nwbfile.add_device(probe)

    nwbfile.add_electrode_group(
        NwbElectrodeGroup(
            name="nwb_electrode_group",
            description="Sample description",
            location="Sample location",
            device=probe,
            position=[1.0, 2.0, 3.0],
            targeted_location="mPFC",
            targeted_x=1.0,
            targeted_y=2.0,
            targeted_z=3.0,
            units="um",
        )
    )

    pm = ProcessingModule(
        name="associated_files", description="description_of_associated_files"
    )
    nwbfile.add_processing_module(pm)
    pm.add(
        AssociatedFiles(
            name="file1",
            description="description of file1",
            content="1 2 3 content of file test",
            task_epochs="1, 2",
        )
    )

    return nwbfile


def build_optogenetics_nwbfile() -> NWBFile:
    """Assemble one NWBFile holding a populated optogenetics epochs table.

    Shared with ``test_optogenetics.py`` so the fixture and the round-trip
    test are built from exactly the same scaffolding rather than drifting
    apart.

    Returns
    -------
    NWBFile
        File containing a ``FrankLabOptogeneticEpochsTable`` with one row, the
        two ``CameraDevice`` objects its ``spatial_filter_cameras`` column
        references, and the ndx-optogenetics / ndx-ophys-devices metadata the
        table depends on.
    """
    nwbfile = mock_NWBFile()

    stimulus = mock_TimeSeries()
    nwbfile.add_stimulus(stimulus)

    camera_model = DeviceModel(
        name="ndx2000", manufacturer="sony", model_number="ndx2000"
    )
    nwbfile.add_device_model(camera_model)

    camera1 = CameraDevice(
        name="overhead_run_camera 1",
        description="Camera used for tracking running",
        meters_per_pixel=0.20,
        camera_name="test name",
        model=camera_model,
        lens="500dpt",
        frame_rate=30.0,
    )
    nwbfile.add_device(camera1)

    camera2 = CameraDevice(
        name="overhead_run_camera 2",
        description="Camera used for tracking running",
        meters_per_pixel=0.20,
        camera_name="test name",
        model=camera_model,
        lens="500dpt",
        frame_rate=30.0,
    )
    nwbfile.add_device(camera2)

    # Create and add excitation source devices
    excitation_source_model = ExcitationSourceModel(
        name="Omicron LuxX+ 488-100 Model",
        description="Laser for optogenetic stimulation.",
        manufacturer="Omicron",
        source_type="laser",
        excitation_mode="one-photon",
        wavelength_range_in_nm=[488.0, 488.0],
    )
    excitation_source = ExcitationSource(
        name="Omicron LuxX+ 488-100",
        model=excitation_source_model,
        power_in_W=0.077,
        intensity_in_W_per_m2=1.0e10,
    )
    nwbfile.add_device_model(excitation_source_model)
    nwbfile.add_device(excitation_source)

    # Create and add optical fiber devices
    optical_fiber_model = OpticalFiberModel(
        name="Lambda Model",
        description="Lambda fiber (tapered fiber) from Optogenix.",
        model_number="lambda_b5",
        manufacturer="Optogenix",
        numerical_aperture=0.39,
        core_diameter_in_um=200.0,
        active_length_in_mm=2.0,
        ferrule_name="cFCF - ∅2.5mm Ceramic Ferrule",
        ferrule_diameter_in_mm=2.5,
    )
    fiber_insertion = FiberInsertion(
        name="fiber_insertion",
        depth_in_mm=2.0,
        insertion_position_ap_in_mm=-1.5,
        insertion_position_ml_in_mm=3.2,
        insertion_position_dv_in_mm=-5.8,
        position_reference="Bregma at the cortical surface",
        hemisphere="right",
        insertion_angle_pitch_in_deg=0.0,
    )
    optical_fiber = OpticalFiber(
        name="Lambda",
        description="Lambda fiber implanted into right GPe.",
        serial_number="123456",
        model=optical_fiber_model,
        fiber_insertion=fiber_insertion,
    )
    nwbfile.add_device_model(optical_fiber_model)
    nwbfile.add_device(optical_fiber)

    # Create virus and injection metadata
    virus = ViralVector(
        name="AAV-EF1a-DIO-hChR2(H134R)-EYFP",
        construct_name="AAV-EF1a-DIO-hChR2(H134R)-EYFP",
        description="Excitatory optogenetic construct for ChR2-EYFP expression",
        manufacturer="UNC Vector Core",
        titer_in_vg_per_ml=1.0e12,
    )
    optogenetic_viruses = OptogeneticViruses(viral_vectors=[virus])

    virus_injection = ViralVectorInjection(
        name="AAV-EF1a-DIO-hChR2(H134R)-EYFP Injection",
        description="AAV-EF1a-DIO-hChR2(H134R)-EYFP injection into GPe.",
        hemisphere="right",
        location="GPe",
        ap_in_mm=-1.5,
        ml_in_mm=3.2,
        dv_in_mm=-6.0,
        roll_in_deg=0.0,
        pitch_in_deg=0.0,
        yaw_in_deg=0.0,
        reference="Bregma at the cortical surface",
        viral_vector=virus,
        volume_in_uL=0.45,
        injection_date="1970-01-01T00:00:00+00:00",
    )
    optogenetic_virus_injections = OptogeneticVirusInjections(
        viral_vector_injections=[virus_injection]
    )

    effector = Effector(
        name="effector",
        description="Excitatory opsin",
        label="hChR2-EYFP",
        viral_vector_injection=virus_injection,
    )
    optogenetic_effectors = OptogeneticEffectors(effectors=[effector])

    # Create OptogeneticSitesTable
    optogenetic_sites_table = OptogeneticSitesTable(
        description="Information about the optogenetic stimulation sites."
    )
    optogenetic_sites_table.add_row(
        excitation_source=excitation_source,
        optical_fiber=optical_fiber,
        effector=effector,
    )

    # Create experiment metadata container
    optogenetic_experiment_metadata = OptogeneticExperimentMetadata(
        optogenetic_sites_table=optogenetic_sites_table,
        optogenetic_viruses=optogenetic_viruses,
        optogenetic_virus_injections=optogenetic_virus_injections,
        optogenetic_effectors=optogenetic_effectors,
        stimulation_software="FSGUI 2.0",
    )
    nwbfile.add_lab_meta_data(optogenetic_experiment_metadata)

    opto_epochs = FrankLabOptogeneticEpochsTable(
        name="optogenetic_epochs",
        description="Metadata about the optogenetic stimulation parameters that change per epoch.",
        target_tables={"optogenetic_sites": optogenetic_sites_table},
    )

    # test add one epoch
    opto_epochs.add_row(
        start_time=0.0,
        stop_time=100.0,
        stimulation_on=True,
        power_in_mW=100.0,
        pulse_length_in_ms=40.0,
        period_in_ms=250.0,
        number_pulses_per_pulse_train=100,
        number_trains=1,
        intertrain_interval_in_ms=0.0,
        epoch_name="20220911_Wallie_01_sleep",
        epoch_number=1,
        convenience_code="a1",
        epoch_type="sleep",
        theta_filter_on=True,
        theta_filter_lockout_period_in_samples=10,
        theta_filter_phase_in_deg=180.0,
        theta_filter_reference_ntrode=1,
        spatial_filter_on=True,
        spatial_filter_lockout_period_in_samples=10,
        # below is an example of a single rectangular spatial filter region defined by the pixel coordinates of the
        # four corners
        spatial_filter_region_node_coordinates_in_pixels=(
            ((260, 920), (260, 800), (800, 1050), (800, 920)),
        ),
        spatial_filter_cameras=[camera1, camera2],
        spatial_filter_cameras_cm_per_pixel=[0.3, 0.18],
        ripple_filter_on=True,
        ripple_filter_lockout_period_in_samples=10,
        ripple_filter_threshold_sd=5.0,
        ripple_filter_num_above_threshold=4,
        speed_filter_on=True,
        speed_filter_threshold_in_cm_per_s=10.0,
        speed_filter_on_above_threshold=True,
        stimulus_signal=stimulus,
        wavelength_in_nm=450.0,
        optogenetic_sites=[0],
    )
    nwbfile.add_time_intervals(opto_epochs)

    return nwbfile


def main() -> None:
    """Write both fixture files and the stack manifest beside them."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "all_types_0.2.4.nwb"

    with NWBHDF5IO(str(path), mode="w") as io:
        io.write(build_nwbfile())

    # Read it straight back, so a broken fixture fails here rather than
    # surfacing later as a confusing failure in the read-back tests.
    with NWBHDF5IO(str(path), mode="r") as io:
        read = io.read()
        assert read.devices["header_device"].qt_version == "Sample qt_version"
        assert read.devices["camera_device"].frame_rate == 30.0
        assert (
            read.devices["probe"].shanks["0"].shanks_electrodes["1"].rel_z
            == 6.0
        )
        assert (
            read.electrode_groups["nwb_electrode_group"].targeted_location
            == "mPFC"
        )
        assert (
            read.processing["associated_files"]["file1"].task_epochs == "1, 2"
        )

    opto_path = OUT_DIR / "optogenetics_0.2.4.nwb"
    with NWBHDF5IO(str(opto_path), mode="w") as io:
        io.write(build_optogenetics_nwbfile())

    with NWBHDF5IO(str(opto_path), mode="r") as io:
        read = io.read()
        epochs = read.intervals["optogenetic_epochs"]
        assert epochs[0, "epoch_name"] == "20220911_Wallie_01_sleep"
        assert epochs[0, "wavelength_in_nm"] == 450.0
        assert [c.name for c in epochs[0, "spatial_filter_cameras"]] == [
            "overhead_run_camera 1",
            "overhead_run_camera 2",
        ]

    stack = {
        pkg: version(pkg)
        for pkg in (
            "pynwb",
            "hdmf",
            "ndx-franklab-novela",
            "ndx-optogenetics",
            "ndx-ophys-devices",
            "numpy",
            "h5py",
        )
    }
    (OUT_DIR / "stack.json").write_text(json.dumps(stack, indent=2) + "\n")

    for written in (path, opto_path):
        print(f"wrote {written} ({written.stat().st_size} bytes)")  # noqa: T201
    print(json.dumps(stack, indent=2))  # noqa: T201


if __name__ == "__main__":
    main()
