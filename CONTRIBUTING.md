# Contributing

Contributions are welcome and they are greatly appreciated!
Every little bit helps and credit will always be given.


## Types of Contributions

You can contribute in many ways:


### Report Bugs

Report bugs at https://github.com/markus-ebke/python-billiards/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.


### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help wanted" is open to whoever wants to implement it.


### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.


### Documentation Improvements

billiards could always use more and clearer documentation, whether as part of the official billiards docs, in docstrings, or even on the web in blog posts, articles, and such.


### Submit Feature Requests and Feedback

The best way to send feedback is to file an issue at https://github.com/markus-ebke/python-billiards/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Tag it with "enhancement" and "help wanted"
* Remember that this is a volunteer-driven project, and that contributions are welcome :)


## Development

Before you start make sure that you have Python version>=3.5.
Then
1. Fork [billiards](https://github.com/markus-ebke/python-billiards) (look for the "Fork" button).
2. Clone your fork locally:
   ```shell
   $ git clone git@github.com:your_name_here/python-billiards.git
   ```
3. Install your local copy into a virtual environment.
   Assuming you have [pipenv](https://pypi.org/project/pipenv/) installed, this is how you set up your fork for local development:
   ```shell
   $ cd python-billiards
   $ pipenv install --dev
   ```
   If you don't have pipenv you can use [venv](https://docs.python.org/3/library/venv.html) and [pip](https://pypi.org/project/pip/) instead.
   Setup the virtual environment and then use the requirements-file with pip like this:
   ```shell
   $ pip install -r requirements_dev.txt
   $ python setup.py develop
   ```

4. Create a branch for local development (use the [git-flow model](https://nvie.com/posts/a-successful-git-branching-model/)):
   ```shell
   $ git checkout -b feature/name-of-your-feature
   ```
   Now you can make your changes locally.

5. If you changed code in visualize.py, regenerate the images and videos for the documentation with
   ```shell
   $ cd docs/
   $ python3 create_visualizations.py
   ```

6. When you're done making changes, run the autoformatter, linter, tests and doc builder with [tox](https://tox.readthedocs.io/en/latest/install.html) in one command:
   ```shell
   $ tox
   ```
   It will
     - use [isort](https://pypi.org/project/isort/) and [black](https://pypi.org/project/black/) for automatic code formatting
     - [flake8](https://pypi.org/project/flake8/) as linter
     - [pydocstyle](https://pypi.org/project/pydocstyle/) and [doc8](https://pypi.org/project/doc8/) as linters for documentation
     - [pytest](https://pypi.org/project/pytest/) with [pytest-cov](https://pypi.org/project/pytest-cov/) to run tests and collect test coverage
     - [sphinx](https://pypi.org/project/Sphinx/) to build the documentation in the _build/docs_ folder

   Note that tox will run the tests for Python 3.5, 3.6 and 3.7.
   If there are no python interpreters for these versions on your system, the tests will fail.

   Did you know that you can preview markdown with [grip](https://pypi.org/project/grip/)?
   While modifing `README.md` you can preview the changes in your browser:
   ```shell
   $ grip -b
   ```
   or for `CONTRIBUTING.md`:
   ```shell
   $ grip -b CONTRIBUTING.md
   ```

7. Commit your changes and push your branch to GitHub:
   ```shell
   $ git add .
   $ git commit -m "Your detailed description of your changes"
   $ git push origin feature/name-of-your-feature
   ```

8. Submit a pull request through the GitHub website.


### Pull Request Guidelines

If you need some code review or feedback while you're developing the code just make the pull request.

For merging, you should:
1. Include passing tests (run tox).
2. Update the documentation if you extend the API or add functionality, etc.
   If you add functions or classes use the docstring.
3. Add a note at the top of `CHANGELOG.md` about the changes.
4. Add yourself to the _Author_ section in the `README.md` file.


### Tips

To run a subset of tests:
```shell
$ pytest tests.test_myfeature
```

To view all tox environments:
```shell
$ tox -l
```

If you want to use only one of them:
```shell
$ tox -e codestyle
```


## Notes for the Maintainer

- Create the `requirements_dev.txt` from the Pipfile with
  ```shell
  $ pipenv lock --requirements --dev > requirements_dev.txt
  ```
  but delete the `.[visualize]` line because pip19.1 [can't do editable installs with ``pyproject.toml`` files](https://github.com/pypa/pip/issues/6375) (the [recommended way](https://setuptools.readthedocs.io/en/latest/setuptools.html#development-mode) is `$ python setup.py develop`).

- Use `major.minor.patch` version numbering and use [bump2version](https://pypi.org/project/bump2version/) to change it.
  Make sure all changes are committed (and `CHANGELOG.md` updated), then use
  ```shell
  $ bump2version minor
  $ git push --tags
  ```
  to increase the minor version number (alternative: `major` or `patch`).
