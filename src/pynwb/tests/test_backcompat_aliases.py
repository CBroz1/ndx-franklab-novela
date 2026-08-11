"""Characterize the backward-compatibility aliases.

``ndx_franklab_novela/__init__.py`` aliases the singular method names onto the
generated plural ones. Downstream code (including spyglass) still calls the
singular forms, so these must keep working and must stay the *same* callables
as their plural counterparts.
"""

import pytest

from ndx_franklab_novela import Probe, Shank, ShanksElectrode

ALIASES = [
    (Probe, "add_shank", "add_shanks"),
    (Probe, "get_shank", "get_shanks"),
    (Shank, "add_shanks_electrode", "add_shanks_electrodes"),
    (Shank, "get_shanks_electrode", "get_shanks_electrodes"),
]


@pytest.mark.parametrize(
    ("cls", "alias", "canonical"),
    ALIASES,
    ids=[f"{c.__name__}.{a}" for c, a, _ in ALIASES],
)
def test_alias_is_the_canonical_method(cls, alias, canonical):
    """Each alias is the very same function object as its plural form.

    Parameters
    ----------
    cls : type
        Class carrying the alias.
    alias : str
        Singular, deprecated method name.
    canonical : str
        Plural method name generated from the spec.
    """
    assert getattr(cls, alias) is getattr(cls, canonical)


def test_probe_shank_aliases_are_functional():
    """Shanks added via the alias are retrievable by either name."""
    probe = Probe(
        id=1,
        name="probe",
        probe_type="type_1",
        units="um",
        probe_description="sample description",
        contact_size=1.0,
    )
    shank = Shank(name="0")
    probe.add_shank(shank)

    assert probe.get_shank("0") is shank
    assert probe.get_shanks("0") is shank
    assert probe.shanks == {"0": shank}


def test_shank_electrode_aliases_are_functional():
    """Electrodes added via the alias are retrievable by either name."""
    shank = Shank(name="0")
    electrode = ShanksElectrode(name="0", rel_x=1.0, rel_y=2.0, rel_z=3.0)
    shank.add_shanks_electrode(electrode)

    assert shank.get_shanks_electrode("0") is electrode
    assert shank.get_shanks_electrodes("0") is electrode
    assert shank.shanks_electrodes == {"0": electrode}


def test_aliases_interoperate_with_canonical_methods():
    """A value added with the plural form is readable with the singular one.

    Notes
    -----
    Covers the mixed-usage case: older downstream code calling the singular
    getter against objects populated by newer code using the plural setter.
    """
    shank = Shank(name="0")
    electrode = ShanksElectrode(name="7", rel_x=0.0, rel_y=0.0, rel_z=0.0)
    shank.add_shanks_electrodes(electrode)
    assert shank.get_shanks_electrode("7") is electrode
