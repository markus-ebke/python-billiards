# Contributing

Contributions are always welcome and greatly appreciated!
Here is how you can help:

- Report bugs at <https://github.com/markus-ebke/python-billiards/issues>.
    Please include your Python version, a list of steps to reproduce the bug and any details about your local setup that may be helpful in troubleshooting.
- Suggest a feature: File an issue labeled with `enhancement` and explain in detail how the proposed feature would work.
- Improve documentation: *billiards* could always use more and clearer documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such. You can also contribute example files.
- Fix bugs or implement features: Have a look at the issues page or work on your own ideas. The section below explains how to setup everything for local development.



## Development

Before you start make sure that you have Python version >= 3.7.

1. Fork this project (via the button on the Github page) and clone your fork locally:

   ```shell
   git clone https://github.com/<your_username>/python-billiards.git
   ```

2. Install the local copy inside a virtual environment.
   Using [pipenv](https://pypi.org/project/pipenv/) this is quite easy:

   ```shell
   cd python-billiards
   pipenv install --dev
   ```

   But you can also use [venv](https://docs.python.org/3/library/venv.html) or [virtualenv](https://virtualenv.pypa.io/en/latest) to create a virtual environment and then install the required packages with [pip](https://pypi.org/project/pip/) like this:

   ```shell
   pip install -r requirements_dev.txt
   python setup.py develop
   ```

3. Install the [pre-commit](https://pre-commit.com) git hook scripts with

   ```shell
   pre-commit install
   ```

   This will run several checks automatically before every commit:
   - [flynt](https://github.com/ikamensh/flynt) and [pyupgrade](https://github.com/asottile/pyupgrade) to upgrade python syntax (will modify files)
   - [isort](https://pypi.org/project/isort/), [black](https://pypi.org/project/black/) and [blacken-docs](https://github.com/asottile/blacken-docs) for automatic code formatting (will modify files)
   - [flake8](https://pypi.org/project/flake8/) as linter for code
   - [pydocstyle](https://pypi.org/project/pydocstyle/) (only for `src/billiards/`) and [doc8](https://pypi.org/project/doc8/) (only for `docs/`) as linters for documentation

   You can also run them manually with

   ```shell
   pre-commit run --all-files
   ```

4. Create a branch for local development (I suggest to follow the [GitHub flow](https://guides.github.com/introduction/flow/) model):

   ```shell
   git checkout -b <name-of-your-feature>
   ```

   and now you can start on your new feature, bugfix, etc.

5. Regularly run tests with [pytest](https://pypi.org/project/pytest/), note that this will also create a coverage report via [pytest-cov](https://pypi.org/project/pytest-cov/) (summary on the command line, details in `htmlcov/index.html`).
   Depending on the kind of changes you made, there are some additional steps you should take to keep everything consistent:

   - If you changed code in `visualize.py`, please regenerate the images and videos for the documentation with

      ```shell
      cd docs/
      python create_visualizations.py
      ```

   - While modifing the markdown files `README.md` or `CONTRIBUTING.md`, you can preview the changes in your browser with [grip](https://pypi.org/project/grip/):

      ```shell
      grip -b
      ```

      or for `CONTRIBUTING.md`:

      ```shell
      grip -b CONTRIBUTING.md
      ```

   - If you changed docstrings or documentation files, check that the documentation generates correctly via [tox](https://tox.readthedocs.io/en/latest/install.html):

      ```shell
      tox -e docs
      ```

      This will install [sphinx](https://pypi.org/project/Sphinx/) in its own environment and build the documentation in the `build/docs` folder.

   - If you want to run the tests against other versions of Python that you have installed, use [tox](https://tox.readthedocs.io/en/latest/install.html).
     The command

      ```shell
      tox -l
      ```

      will list all Python versions that *billiards* should be able to support.

6. Commit your changes and push your branch to GitHub:

   ```shell
   git add .
   git commit -m "Write a description of your changes"
   git push origin <name-of-your-feature>
   ```

   Helpful: [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

7. Submit a pull request through the GitHub website and I will have a look!



## Pull Request Guidelines

If you need some code review or feedback while you're developing the code, just make the pull request.

Before merging, you should:

1. Include tests and make sure they pass (run *pytest* or *tox*).
2. Update the documentation if you extended the API or added functionality, etc.
   If you added functions or classes write a docstring (use the [Google style](https://google.github.io/styleguide/pyguide.html), [example](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html)).
3. Add a note at the top of `CHANGELOG.md` about the changes.
4. Add yourself to the *Authors* section in the `README.md` file.



## Notes to Myself

- Update packages and pre-commit hooks to their newest version:

   ```shell
   pipenv update
   pre-commit autoupdate
   ```

- The configuration settings are in `pyproject.toml`, except for *flake8* (because it doesn't support `pyproject.toml` yet, see `tox.ini` instead)

- I don't include `Pipfile.lock` in git because the [official recommendation](https://pipenv.pypa.io/en/latest/basics/#general-recommendations-version-control) is
  > Do not keep `Pipfile.lock` in version control if multiple versions of Python are being targeted.

  And *billiards* is intended as a libary for multiple Python versions and not as a standalone application.

- Don't include *billiards* in `requirements_dev.txt`, because *pip19.1* [can't do editable installs with ``pyproject.toml`` files](https://github.com/pypa/pip/issues/6375) (the [recommended way](https://setuptools.readthedocs.io/en/latest/setuptools.html#development-mode) is `$ python setup.py develop`).

- I used [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) when writing the readme and this file.

- Using pandoc, I converted the readme file to rst and copied some of the text to the documentation

   ```shell
   pandoc README.md --from markdown --to rst -s -o readme.rst
   ```

- Create docs manually (i.e. without tox):

   ```shell
   cd docs/
   pip install -r requirements.txt
   make html
   ```

- To make a new release:
  - Go to master branch:

  ```shell
  git checkout master
  ```

  - Merge develop branch into master:

  ```shell
  git merge develop
  ```

  - Update `CHANGELOG.md` and close off the topmost section with `**v<new_version>**`.

  - Commit, message: `Updated CHANGELOG.md` or similar.

  - Use [bump2version](https://pypi.org/project/bump2version/) to change the version number in the files:

  ```shell
  bump2version minor
  ```

  (alternative: `major` or `patch`).
  This will create another commit and a tag with the new version number of the form `v<major.minor.patch>`.

  - Push to Github:

  ```shell
  git commit
  $ git push --tags
  ```

  - Return to develop branch:

  ```shell
  git checkout develop
  ```

- The *tox* environment *metadata* checks that the project can be correctly packaged, it runs [check-manifest](https://pypi.org/project/check-manifest/) (configuration settings in `tox.ini`) to make sure the important files are included.
  Note that I haven't figured out a good way to put this package on [PyPi](https://pypi.org/) (yet).



### List of tools in pre-commit

- flynt (f-string conversion)
- pyupgrade --py37-plus
- isort
- black
- blacken-docs
- flake8 (with flake8-colors, flake8-bugbear, flake8-comprehensions)
- pydocstyle (only for src, not for tests or examples)
- docs8

### Other tools (i.e. not included in pre-commit)

- pytest, coverage report
- sphinx-build
- check-manifest and $ python setup.py check --metadata --strict
- tox
- bumpversion

### The current state of configuration files

Tool name       | name.cfg/ini      | setup.cfg     | pyproject.toml
----------------|-------------------|---------------|-----------------
isort           | yes (preferred)   | yes           | yes (preferred)
black           | no                | no            | yes
flake8          | yes               | yes           | no
pydocstyle      | yes               | yes           | yes
doc8            | yes               | yes           | yes
pytest          | yes               | no            | yes
coverage        | yes               | no            | yes
bumpversion     | yes               | yes           | no
check-manifest  | no                | yes           | yes



### Total Cleanup

- Folders that can be safely removed: `build`, `htmlcov`, `src/billiards.egg-info`, `.eggs`, `.pytest_cache`, `.tox`

- Delete `.coverage` file: $ coverage erase

- Remove pipenv virtual environment: $ pipenv --rm

- Delete the virtualenv folder in `~/.local/share/virtualenvs` (Linux)
