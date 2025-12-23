"""
imaginarium/methods/physical/__init__.py
Physical modeling synthesis methods
"""

from .karplus import KarplusTemplate
from .modal import ModalTemplate
from .bowed import BowedTemplate
from .formant import FormantTemplate
from .membrane import MembraneTemplate
from .tube import TubeTemplate
from .comb_resonator import CombResonatorTemplate

__all__ = [
    "KarplusTemplate",
    "ModalTemplate",
    "BowedTemplate",
    "FormantTemplate",
    "MembraneTemplate",
    "TubeTemplate",
    "CombResonatorTemplate",
]

# Method registry for this family
PHYSICAL_METHODS = {
    "physical/karplus": KarplusTemplate,
    "physical/modal": ModalTemplate,
    "physical/bowed": BowedTemplate,
    "physical/formant": FormantTemplate,
    "physical/membrane": MembraneTemplate,
    "physical/tube": TubeTemplate,
    "physical/comb_resonator": CombResonatorTemplate,
}
