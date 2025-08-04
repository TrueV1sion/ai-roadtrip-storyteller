#!/bin/bash

# iOS Debug Symbol Stripping Script
# Six Sigma DMAIC - Code Obfuscation Implementation

set -e

echo "🔒 Stripping debug symbols for release build..."

# Only run for release builds
if [ "${CONFIGURATION}" != "Release" ]; then
    echo "ℹ️  Skipping symbol stripping for ${CONFIGURATION} build"
    exit 0
fi

# Strip debug symbols from frameworks
find "${BUILT_PRODUCTS_DIR}" -name '*.framework' -type d | while read -r framework
do
    echo "Stripping ${framework}..."
    find "${framework}" -name '*.dylib' -o -name '*.a' | while read -r lib
    do
        strip -S "${lib}" 2>/dev/null || true
    done
done

# Strip main executable
if [ -f "${BUILT_PRODUCTS_DIR}/${EXECUTABLE_PATH}" ]; then
    echo "Stripping main executable..."
    strip -S "${BUILT_PRODUCTS_DIR}/${EXECUTABLE_PATH}"
fi

# Remove dSYM files from app bundle
find "${BUILT_PRODUCTS_DIR}" -name '*.dSYM' -exec rm -rf {} + 2>/dev/null || true

echo "✅ Debug symbols stripped successfully"