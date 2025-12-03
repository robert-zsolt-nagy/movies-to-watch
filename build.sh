#!/bin/bash

echo ">generate assets"
mkdir -p web/dist
if ! npm ci --ignore-scripts --prefix web > web/dist/install-log.txt; then
  echo "ERROR: npm install failed:"
  cat web/dist/install-log.txt
  echo "exiting..."
  exit 1
fi

if ! npm run build --prefix web > web/dist/build-log.txt; then
  echo "ERROR: npm build failed:"
  cat web/dist/build-log.txt
  echo "exiting..."
  exit 1
fi

echo ">copy generated assets"
mkdir -p static/style static/script
cp web/dist/main.css static/style/main.css
cp web/dist/main.js static/script/main.js
cp web/dist/main.js.LICENSE.txt static/script/main.js.LICENSE.txt

echo ">build completed $(date)"
