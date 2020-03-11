SRC = $(wildcard ./*.ipynb)

all: fiducial_detect docs

fiducial_detect: $(SRC)
	nbdev_build_lib
	touch fiducial_detect

docs: $(SRC)
	nbdev_build_docs
	touch docs

test:
	nbdev_test_nbs

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist