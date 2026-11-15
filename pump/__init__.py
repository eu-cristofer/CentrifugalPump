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
- trim: Impeller trim (diameter affinity) helpers.
- fitting: Natural cubic spline, R² and bracketed bisection.
- system_curve: System resistance curves (static + k·Q^n, pipe Darcy-Weisbach).
- operating_point: Pump curve / system curve intersection.
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
    trim,
    fitting,
    system_curve,
    operating_point,
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
from .trim import *
from .fitting import *
from .system_curve import *
from .operating_point import OperatingPoint

__all__ = list(
    set(utilities.__all__) |
    set(constants.__all__) |
    {"constants", "quantity_io", "acceptance", "mechanical_run", "npsh", "compare", "viscosity", "trim",
     "fitting", "system_curve", "operating_point", "OperatingPoint"} |
    set(point.__all__) |
    set(mechanical_run.__all__) |
    set(npsh.__all__) |
    set(acceptance.__all__) |
    set(viscosity.__all__) |
    set(performance_curve.__all__) |
    set(compare.__all__) |
    set(trim.__all__) |
    set(fitting.__all__) |
    set(system_curve.__all__)
)
