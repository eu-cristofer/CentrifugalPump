``pumpflow`` — visual workbench
===============================

The PySide6 layer. Qt (``PySide6``) is mocked during the docs build, so these
pages document the Qt-agnostic logic and data layers; the rendering code is
documented from its docstrings without importing Qt.

Typed signals & sample data
---------------------------

.. automodule:: pumpflow.signals

.. automodule:: pumpflow.sample_data

Persistence
-----------

.. automodule:: pumpflow.persistence

Node logic
----------

The Qt-agnostic base of every widget node. (The concrete node classes subclass
Qt dialogs and are documented in the source; they cannot be imported under a
mocked Qt.)

.. automodule:: pumpflow.nodes.base
