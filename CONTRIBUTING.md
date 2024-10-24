# Contributing

Contributions are always welcome and greatly appreciated!
Here is how you can help:

- Report bugs at <https://github.com/markus-ebke/python-billiards/issues>.
    Please include your Python version, a list of steps to reproduce the bug (or an example file) and any details about your local setup that may be helpful in troubleshooting.
- Suggest a feature: File an issue labeled with `enhancement` and describe your idea.
- Improve documentation: *billiards* could always use more and clearer documentation, in the docstrings or as part of the official docs. You can also contribute example files.
- Fix bugs or implement features: Have a look at the issues page or work on your own ideas. The section below explains how to setup the project for local development.



## Development

Before you start, make sure that you have Python version >= 3.8.

1. Fork this project (via the button on the Github page) and clone your fork locally:

   ```shell
   git clone https://github.com/<your_username>/python-billiards.git
   ```

2. Install the local copy, preferably inside a virtual environment.
   With [pipenv](https://pypi.org/project/pipenv/) this is quite easy:

   ```shell
   cd python-billiards
   pipenv install --dev
   ```

   But you can also use [venv](https://docs.python.org/3/library/venv.html) or [virtualenv](https://virtualenv.pypa.io/en/latest) to create a virtual environment and, after activating it, install the required packages with [pip](https://pypi.org/project/pip/) like this:

   ```shell
   pip install --editable .[visualize]
   pip install -r requirements_dev.txt
   ```

3. Optional: Install [pre-commit](https://pre-commit.com) (not included in `requirements_dev.txt`) and its git hook scripts:

   ```shell
   pip install pre-commit
   pre-commit install
   ```

   This will run several checks automatically before every commit:
   - [flynt](https://github.com/ikamensh/flynt) and [pyupgrade](https://github.com/asottile/pyupgrade) to upgrade python syntax (will modify files)
   - [isort](https://pypi.org/project/isort/), [black](https://pypi.org/project/black/) and [blacken-docs](https://github.com/asottile/blacken-docs) for automatic code formatting (will modify files)
   - [flake8](https://pypi.org/project/flake8/) as linter for code
   - [pydocstyle](https://pypi.org/project/pydocstyle/) (only for `src/billiards/`) and [doc8](https://pypi.org/project/doc8/) (only for `docs/`) as linters for documentation

   You can also run the tools manually:

   ```shell
   pre-commit run --all-files
   ```

4. Create a branch for local development (I suggest you follow the [GitHub flow](https://guides.github.com/introduction/flow/) model):

   ```shell
   git checkout -b <name-of-your-feature>
   ```

   and now you can start on your new feature, bugfix, etc.

5. Commit the changes and push your branch to GitHub:

   ```shell
   git add .
   git commit -m "Write a description of your changes"
   git push origin <name-of-your-feature>
   ```

   Helpful: [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

6. Before submitting a pull request, please run the unit tests with [pytest](https://pypi.org/project/pytest/).
   Note that pytest will also create a coverage report via [pytest-cov](https://pypi.org/project/pytest-cov/) (summary on the command line, details in `htmlcov/index.html`).
   Depending on the kind of changes you made, there are some additional steps you should take to keep everything consistent:

   - If you changed code in `visualize_matplotlib.py`, please regenerate the images and videos for the documentation with:

      ```shell
      python docs/create_visualizations.py
      ```

   - If you changed docstrings or documentation files, check that the documentation is generated correctly via [tox](https://tox.readthedocs.io/en/latest/install.html):

      ```shell
      tox -e docs-lint
      tox -e docs-build
      ```

      The first command will run [pydocstyle](https://pypi.org/project/pydocstyle/) on the `src/billiards` folder and [doc8](https://pypi.org/project/doc8/) followed by [Sphinx](https://pypi.org/project/Sphinx/) doctest and linkcheck on the `docs` folder.
      The second command will generate the documentation and place it in the `build/docs` folder.

   - If you want to run the unit tests against other versions of Python, use [tox](https://tox.readthedocs.io/en/latest/install.html).
     The command

      ```shell
      tox -l
      ```

      will list all Python versions that *billiards* should be compatible with.
      For example, to run against Python 3.13 (assuming the corresponding Python interpreter is already installed on your system):

      ```shell
      tox -e py313
      ```

      This will run pytest and also overwrite the coverage report in `htmlcov/index.html`.

   - While modifing the markdown files `README.md` or `CONTRIBUTING.md`, you can preview the changes in your browser with [grip](https://pypi.org/project/grip/) (not included in `requirements_dev.txt`):

      ```shell
      grip -b
      ```

      or for `CONTRIBUTING.md`:

      ```shell
      grip -b CONTRIBUTING.md
      ```

7. Submit a pull request through the GitHub website and I will have a look!



## Pull Request Guidelines

If you need some code review or feedback while you're developing the code, just make a pull request.

Before merging, you should:

1. Include new tests (if any) and make sure they pass (run pytest or tox).
2. Update docstrings and the documentation files if you changed the API or added functionality.
   For docstrings, use the [Google style guide](https://google.github.io/styleguide/pyguide.html).
   Example file: <https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html>.
3. Add a note in the top section of `CHANGELOG.md` describing the changes.
4. Add yourself to the *Authors* section in the `README.md` file.



## Notes to Myself

### How to make a new release

1. Complete the notes in `CHANGELOG.md` and close off the topmost section with `**v<new_version>**` (write it exactly as stated here, later *bump2version* will replace `<new_version>` with the updated version number).

2. Commit, message: `Update CHANGELOG.md` or similar.

3. Go to master branch and merge develop into master:

   ```shell
   git checkout master
   git merge develop
   ```

4. In the master branch use [bump2version](https://pypi.org/project/bump2version/) to update the version number in the files.
   The version identifier should always be of the form `N.N.N[.devN]`.
   To prepare a new release, use

   ```shell
   bump2version part
   ```

   where `part` is `major`, `minor` or `patch`.
   This will set the version number to `major.minor.patch.dev0`, i.e. it is automatically a development version.
   To bump the development number, use `dev_number` for `part`; to promote the development version to final, use

   ```shell
   bump2version dev_label --tag
   ```

   The tag will be `v<major.minor.patch>`.

   To skip development versions (e.g. when using `patch`), use the `--new-version` argument and set the version number explicitly.
   Other useful arguments: `--dry-run` and `--list`.

5. Push to Github:

   ```shell
   git push --all
   git push --tags
   ```

6. The *tox* environment *metadata* checks that the project can be correctly packaged, it runs [check-manifest](https://pypi.org/project/check-manifest/) (configuration settings in `tox.ini`) and [twine check](https://twine.readthedocs.io/en/stable/index.html#twine-check) to make sure the important files are included.
To check the metadata and build the package use

   ```shell
   tox -e metadata
   python3 -m build
   ```

   TODO: Figure out a way to upload this package to [PyPi](https://pypi.org/).

7. Return to develop branch and merge master branch (to get current version number):

   ```shell
   git checkout develop
   git merge master
   ```

   Then continue working.

### Useful commands and settings

- Update packages and pre-commit hooks to their newest version:

   ```shell
   pipenv update
   pre-commit autoupdate
   ```

- The configuration settings are in `pyproject.toml`, `setup.cfg` (TODO: move to `pyproject.toml`), `tox.ini` (TODO: can move to `pyproject.toml`, but requires version >=v4.21.0?) and `.flake8` (doesn't support `pyproject.toml`, workaround: [Flake8-pyproject](https://pypi.org/project/Flake8-pyproject/)?)

- I don't include `Pipfile.lock` in git because the [official recommendation](https://pipenv.pypa.io/en/latest/basics/#general-recommendations-version-control) is
  > Do not keep `Pipfile.lock` in version control if multiple versions of Python are being targeted.

  And *billiards* is intended as a libary for multiple Python versions and not as a standalone application.

- I used [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) when writing the readme and this file.

- Using [pandoc](https://pandoc.org/), I converted the readme file to rst and copied some of the text to the documentation

   ```shell
   pandoc README.md --from markdown --to rst -s -o readme.rst
   ```

- Generate the API documentation templates:

   ```shell
   sphinx-apidoc -f -o {toxinidir}/docs/api_reference {toxinidir}/src/billiards
   ```

- Create docs manually (i.e. without tox):

   ```shell
   cd docs/
   pip install -r requirements_docs.txt
   make html
   ```


### List of tools in pre-commit

- flynt (f-string conversion)
- pyupgrade --py37-plus
- isort
- black
- blacken-docs
- flake8 (with flake8-bugbear, flake8-comprehensions)
- pydocstyle (only for src, not for tests or examples)
- docs8

### Other tools (i.e. not included in pre-commit)

- pytest, coverage report
- sphinx-build
- check-manifest and twine
- tox
- bump2version

### The current state of configuration files

Tool name       | name.cfg/ini      | setup.cfg     | pyproject.toml
----------------|-------------------|---------------|-----------------
isort           | yes (preferred)   | yes           | yes (preferred)
black           | no                | no            | yes
flake8          | yes               | yes           | Flake8-pyproject
pydocstyle      | yes               | yes           | yes
doc8            | yes               | yes           | yes
pytest          | yes               | no            | yes
coverage        | yes               | no            | yes
bumpversion     | yes               | yes           | no
check-manifest  | no                | yes           | yes



### Total Cleanup

- Files and folders that can be safely removed: `build`, `dist`, `htmlcov`, `src/billiards.egg-info`, `.eggs`, `.pytest_cache`, `.tox`, `.coverage`

- Remove pipenv virtual environment: $ pipenv --rm

- When using Pipenv on Linux: delete the virtualenv folder in `~/.local/share/virtualenvs`
