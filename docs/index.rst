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
   :maxdepth: 2
   :caption: API reference

   api/pump
   api/pumpflow

.. toctree::
   :maxdepth: 2
   :caption: Architecture & tutorials

   ARCHITECTURE
   RUN_AND_TEST
   pumpflow-theming

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

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
