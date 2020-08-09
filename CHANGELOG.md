# 2.0.0
- Removed support for python 2
- Updated to hunspell 1.7.0
- Added support for `suffix_suggest`
- Added support for `analyze`
- Added support for `add_dic`
- Added support for `remove`
- Added support for `add_with_affix`
- Updated builds to be wheel based
- Moved dictionaries inside hunspell directory structure

# 1.3.3
- Mapped the `add` function to the cython wrapper class.

# 1.3.1 -> 1.3.2
- Fixed dictionary loader to respect locales
- Enabled long file paths to be loaded on windows
- Fixed caching bug which caches results across hunspell instances with different dictionaries.

# 1.3.0
- Fixed build for python 3.7
- Fixed library search issues (> Ubunutu 17)
- Upgraded default hunspell to 1.6.2 for Linux distros

# 1.2.1
- Fixed empty string crash

# 1.2.0
- Fixed detect CPU issue on Linux distros
- Fixed bytes versus unicode conversion for inputs in python2
- Added fix for Python 2.7 on osx
- Added fix for Windows 10 builds

# 1.1.4
- Added Python 3 support

# 1.1.3
- Removed library depdency on cython
- Dropped support for Python 2.6
- Added ability to set concurrency on bulk operations
