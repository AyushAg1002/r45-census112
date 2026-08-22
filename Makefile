CXX ?= c++
CXXFLAGS ?= -O3 -std=c++20 -Wall -Wextra -pedantic
PYTHON ?= python3
NAUTY_DIR := third_party/nauty2_9_3

.PHONY: all clean fetch-inputs build-nauty test verify-low-degree verify-nonsaturated reproduce-nonsaturated independent-deletion-crosscheck reproduce-saturated-witness reproduce-all release release-candidate

all: build/extend_from_min_vertex build/independent_delete_filter

fetch-inputs:
	./scripts/fetch_inputs.sh

build-nauty: fetch-inputs
	test -x $(NAUTY_DIR)/countg || (cd $(NAUTY_DIR) && ./configure)
	$(MAKE) -C $(NAUTY_DIR)

build/extend_from_min_vertex: src/extend_from_min_vertex.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@

build/independent_delete_filter: src/independent_delete_filter.cpp
	@mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@

test: build-nauty build/extend_from_min_vertex build/independent_delete_filter
	./tests/test_extension.sh
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

verify-low-degree: build/extend_from_min_vertex
	PYTHON_BIN=$(PYTHON) ./scripts/reproduce_low_degree.sh

verify-nonsaturated:
	$(PYTHON) verify_nonsaturated.py

reproduce-nonsaturated: build-nauty
	./scripts/reproduce_nonsaturated.sh

independent-deletion-crosscheck: build/independent_delete_filter build-nauty
	./scripts/reproduce_independent_deletion.sh

reproduce-saturated-witness: build-nauty
	PYTHON_BIN=$(PYTHON) ./scripts/reproduce_saturated_witness.sh

reproduce-all:
	PYTHON_BIN=$(PYTHON) ./scripts/reproduce_all.sh

release:
	$(PYTHON) scripts/build_release_candidate.py

release-candidate: release

clean:
	rm -f build/extend_from_min_vertex build/independent_delete_filter
