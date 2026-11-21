CentrifugalPump
===============

Engineering tools for assessing **API 610 centrifugal pumps** during Performance
and Mechanical Running Test (FAT) trials. The project is two stacked subsystems:

- **pump/** — a layered Python *library* of pump physics: units, fluids, points,
  performance curves, API 610 compliance, and ``.docx`` reporting.
- **pumpflow/** — a PySide6 *visual workbench* that orchestrates the library into a
  drag-and-wire node workflow.

.. toctree::
   :maxdepth: 2
   :caption: Guide

   overview

.. toctree::
   :maxdepth: 1
   :caption: Concepts

   concepts/affinity
   concepts/head-components
   concepts/npsh
   concepts/viscosity
   concepts/acceptance-tolerances
   concepts/system-curve
   concepts/mechanical-run
   concepts/vibration

.. toctree::
   :maxdepth: 1
   :caption: Training

   training/README
   training/TR-01-witness-performance-test
   training/TR-02-witness-with-the-browser

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/pump
   api/pumpflow

.. toctree::
   :maxdepth: 2
   :caption: Architecture & tutorials

   ARCHITECTURE
   RUN_AND_TEST
   design-system
   web

.. toctree::
   :maxdepth: 1
   :caption: Product

   product/audience
   product/use-cases

.. toctree::
   :maxdepth: 1
   :caption: Sprints
   :glob:

   sprints/README
   sprints/sprint-*

.. toctree::
   :maxdepth: 1
   :caption: Decision records
   :glob:

   adr/README
   adr/0*

.. toctree::
   :maxdepth: 1
   :caption: Project records
   :glob:

   changes/NEXT_STEPS
   changes/001_masterpiece/README
   changes/001_masterpiece/MOTIVATION
   changes/001_masterpiece/sprint-*
   UI_SPEC
   multi-unit-philosophy
   BUILD
   DEV_JOURNEY
   REMOVAL_MAP
   reviews/*

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
