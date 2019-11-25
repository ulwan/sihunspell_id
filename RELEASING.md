# Releasing

## Tracking Changes

Update the CHANGELOG.md with any significant changes for the release.

Update VERSION file with the next version bump

    git commit -am "Updated version to `cat VERSION`"

## Rebuilding Extensions

Then ensure that you've built the extension for the release.

    python --version # Use >= 3.6.x
    pip install -r requirements-dev.txt
    python setup.py build_ext
    # Remove the any accidentally added so files
    rm -rf hunspell/*.so
    python setup.py test # Should pass with changes

## Commiting Changes

You should now see a new hunspell.cpp in the hunspell directory.

   git add hunspell/hunspell.cpp
   git commit -m "Compiled new hunspell.cpp for release"


## Push release

To release, run through the following:

    rm -rf dist
    git tag `cat VERSION`
    python setup.py sdist
    pip install dist/*
    # Check the tar version matches expected release version
    git push
    git push --tags
    twine upload dist/*
