============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

Bug reports
===========

When `reporting a bug <https://github.com/python-mario/mario/issues>`_ please include:

    * Your operating system name and version.
    * Any details about your local setup that might be helpful in troubleshooting.
    * Detailed steps to reproduce the bug.

Documentation improvements
==========================

mario could always use more documentation, whether as part of the
official mario docs, in docstrings, or even on the web in blog posts,
articles, and such.




- Use `semantic newlines`_ in reStructuredText_ files (files ending in ``.rst``):

  .. code-block:: rst

     This is a sentence.
     This is another sentence.

- If you start a new section, add two blank lines before and one blank line after the header, except if two headers follow immediately after each other:

  .. code-block:: rst

     Last line of previous section.


     Header of New Top Section
     -------------------------

     Header of New Section
     ^^^^^^^^^^^^^^^^^^^^^

     First line of new section.

- If you add a new feature, demonstrate its awesomeness on the `examples page`_!


Updating the changelog
-----------------------------

If your change is noteworthy, there needs to be a changelog entry so our users can learn about it!

To avoid merge conflicts, we use the towncrier_ package to manage our changelog.
``towncrier`` uses independent files for each pull request -- so called *news fragments* -- instead of one monolithic changelog file.
On release, those news fragments are compiled into our ``CHANGELOG.rst``.

You don't need to install ``towncrier`` yourself, you just have to abide by a few simple rules:

- For each pull request, add a new file into ``changelog.d`` with a filename adhering to the ``pr#.(change|deprecation|breaking).rst`` schema:
  For example, ``changelog.d/42.change.rst`` for a non-breaking change that is proposed in pull request #42.
- As with other docs, please use `semantic newlines`_ within news fragments.
- Wrap symbols like modules, functions, or classes into double backticks so they are rendered in a ``monospace font``.
- Wrap arguments into asterisks like in docstrings: *these* or *attributes*.
- If you mention functions or other callables, add parentheses at the end of their names: ``mario.func()`` or ``mario.Class.method()``.
  This makes the changelog a lot more readable.
- Prefer simple past tense or constructions with "now".
  For example:

  + Added ``mario.func()``.
  + ``mario.func()`` now doesn't crash the Large Hadron Collider anymore when passed the *foobar* argument.
- If you want to reference multiple issues, copy the news fragment to another filename.
  ``towncrier`` will merge all news fragments with identical contents into one entry with multiple links to the respective pull requests.

Example entries:

  .. code-block:: rst

     Added ``mario.func()``.
     The feature really *is* awesome.

or:

  .. code-block:: rst

     ``mario.func()`` now doesn't crash the Large Hadron Collider anymore when passed the *foobar* argument.
     The bug really *was* nasty.

----

Feature requests and feedback
=============================

The best way to send feedback is to file an issue at https://github.com/python-mario/mario/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that code contributions are welcome :)

Development
===========

To set up `mario` for local development:

1. Fork `mario <https://github.com/python-mario/mario>`_
   (look for the "Fork" button).
2. Clone your fork locally::

     git clone git@github.com:your_name_here/mario.git

3. Create a branch for local development::

    git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

4. When you're done making changes, run all the checks, doc builder and spell checker with `tox`_ one command::

    tox

5. Commit your changes and push your branch to GitHub::

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

6. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

If you need some code review or feedback while you're developing the code just make the pull request.

For merging, you should:

1. Include passing tests (run ``tox``) [1]_.
2. Update documentation when there's new API, functionality etc.
3. Add a file in ``changelog.d/`` describing the changes. The filename should be ``{id}.{type}.rst``, where ``{id}`` is the number of the GitHub issue or pull request and ``{type}`` is one of ``breaking`` (for breaking changes), ``deprecation`` (for deprecations), or ``change`` (for non-breaking changes). For example, to add a new feature requested in GitHub issue #1234, add a file called ``changelog.d/1234.change.rst`` describing the change.
4. Add yourself to ``AUTHORS.rst``.

.. [1] If you don't have all the necessary python versions available locally you can rely on Travis - it will
       `run the tests <https://travis-ci.org/python-mario/mario/pull_requests>`_ for each change you add in the pull request.

       It will be slower though ...

Tips
----

To run a subset of tests::

    tox -e envname -- pytest -k test_myfeature

To run all the test environments in *parallel* (you need to ``pip install detox``)::

    detox




.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`PEP 257`: https://www.python.org/dev/peps/pep-0257/
.. _`good test docstrings`: https://jml.io/pages/test-docstrings.html
.. _`Code of Conduct`: https://github.com/python-attrs/attrs/blob/master/.github/CODE_OF_CONDUCT.rst
.. _changelog: https://github.com/python-attrs/attrs/blob/master/CHANGELOG.rst
.. _tox: https://tox.readthedocs.io/
.. _pyenv: https://github.com/pyenv/pyenv
.. _reStructuredText: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _semantic newlines: https://rhodesmill.org/brandon/2012/one-sentence-per-line/
.. _examples page: https://github.com/python-attrs/attrs/blob/master/docs/examples.rst
.. _Hypothesis: https://hypothesis.readthedocs.io/
.. _CI: https://attrs.visualstudio.com/attrs/_build/latest?definitionId=1&branchName=master
.. _towncrier: https://pypi.org/project/towncrier
.. _black: https://github.com/ambv/black
.. _pre-commit: https://pre-commit.com/
.. _isort: https://github.com/timothycrosley/isort
