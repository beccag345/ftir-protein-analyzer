# Third-Party Software Notices

Last reviewed: 2026-08-17

The FTIR Protein Analyzer source code is licensed separately under the MIT
License in [`LICENSE`](LICENSE). That license does not replace or modify the
licenses of the third-party projects listed below.

This source repository imports third-party packages but does not vendor their
source code or binaries. Installing the application or notebook dependencies
obtains those packages separately. The license files distributed with the
exact package versions being installed or redistributed are authoritative.

## Direct dependencies

| Project | Used by | License summary | Authoritative license information |
| --- | --- | --- | --- |
| NumPy | `graph.py`, notebook | BSD-3-Clause for NumPy; distributions include separately licensed components | [NumPy license](https://github.com/numpy/numpy/blob/main/LICENSE.txt) |
| pandas | `graph.py`, notebook | BSD-3-Clause; distributions include separately licensed components | [pandas license](https://github.com/pandas-dev/pandas/blob/main/LICENSE) |
| SciPy | `graph.py`, notebook | BSD-3-Clause; distributions include compatibly licensed bundled components | [SciPy license](https://github.com/scipy/scipy/blob/main/LICENSE.txt) and [bundled licenses](https://github.com/scipy/scipy/blob/main/LICENSES_bundled.txt) |
| Matplotlib | `graph.py`, notebook | Matplotlib License, based on the PSF license; distributions can include components under other licenses | [Matplotlib license and bundled notices](https://matplotlib.org/stable/project/license.html) |
| pybaselines | `graph.py`, notebook | BSD-3-Clause | [pybaselines license](https://pybaselines.readthedocs.io/en/stable/license.html) |
| IPython | notebook | BSD-3-Clause | [IPython license](https://github.com/ipython/ipython/blob/main/LICENSE) |
| PySide6 / Qt for Python | `main.py` | Community edition under LGPLv3/GPLv3, or a commercial Qt license | [Qt for Python licensing](https://doc.qt.io/qtforpython-6/) and [third-party license list](https://doc.qt.io/qtforpython-6/licenses.html) |

Python standard-library modules such as `os`, `sys`, `dataclasses`, and
`collections` are not third-party dependencies and are therefore not listed.

## PySide6 and binary distribution

`main.py` imports `PySide6.QtWidgets`. PySide6 and the Qt libraries are not
relicensed under this project's MIT License.

Publishing this source repository, without vendoring PySide6 or Qt binaries,
is different from distributing a frozen or installed application that bundles
them. Anyone distributing such an application must comply with the license
option they use and reproduce the applicable Qt, PySide6, Shiboken, and
bundled-component notices from the exact distribution. The Qt for Python
documentation should be reviewed again before creating a binary release.

## Dependency and notice maintenance

When a direct dependency is added, removed, or replaced, update this file. If
the project begins distributing dependency wheels, shared libraries, fonts,
or a standalone executable, retain the complete license and copyright notices
shipped with those exact artifacts rather than relying only on this summary.
