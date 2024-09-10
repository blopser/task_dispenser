#! /usr/bin/bash

set -ex

rm ./coverage.xml htmlcov -rf && pytest
