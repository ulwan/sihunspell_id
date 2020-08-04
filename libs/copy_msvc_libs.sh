DIRNAME="$(dirname "$0")"

cp "$DIRNAME/../external/hunspell-1.7.0/msvc/x64/Release/libhunspell.lib" "$DIRNAME/../libs/msvc/libhunspell-msvc14-x64.lib"
cp "$DIRNAME/../external/hunspell-1.7.0/msvc/Release/libhunspell/libhunspell.lib" "$DIRNAME/../libs/msvc/libhunspell-msvc14-x86.lib"
