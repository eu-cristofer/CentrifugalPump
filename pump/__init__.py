"""
pump
====

This module provides tools for API 610 pumping system
calculations.

Submodules
----------
- utilities: Contains unit conversion utilities based on Pint.
- constants: Shared physical constants (``G``, ``P_ATM``).
- quantity_io: JSON (de)serialisation of Pint quantities.
- acceptance: Edition-aware acceptance criteria (tolerance tables).
- mechanical_run: Mechanical running test log, checker and trend plot.
- npsh: NPSH available / NPSH3 / NPSHr curve / margin check.
- compare: Side-by-side comparison of several performance curves.
- viscosity: HI 9.6.7 viscosity correction parameter and factors.
"""

__author__ = "Cristofer Antoni Souza Costa"
__version__ = "0.1.0"
__email__ = "cristofercosta@yahoo.com.br"
__status__ = "Development"

from . import (
    utilities,
    constants,
    quantity_io,
    point,
    mechanical_run,
    npsh,
    acceptance,
    viscosity,
    performance_curve,
    compare,
)
from .utilities import *
from .constants import *
from .point import *
from .mechanical_run import *
from .npsh import *
from .acceptance import *
from .viscosity import *
from .performance_curve import *
from .compare import *

__all__ = list(
    set(utilities.__all__) |
    set(constants.__all__) |
    {"constants", "quantity_io", "acceptance", "mechanical_run", "npsh", "compare", "viscosity"} |
    set(point.__all__) |
    set(mechanical_run.__all__) |
    set(npsh.__all__) |
    set(acceptance.__all__) |
    set(viscosity.__all__) |
    set(performance_curve.__all__) |
    set(compare.__all__)
)
