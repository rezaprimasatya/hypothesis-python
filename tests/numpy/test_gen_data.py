# coding=utf-8
#
# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis-python
#
# Most of this work is copyright (C) 2013-2017 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import numpy as np
import pytest
from flaky import flaky

import hypothesis.strategies as st
from hypothesis import given, settings
from tests.common.debug import minimal
from hypothesis.extra.numpy import arrays, from_dtype, array_shapes, \
    nested_dtypes, scalar_dtypes
from hypothesis.strategytests import strategy_test_suite
from hypothesis.searchstrategy import SearchStrategy
from hypothesis.internal.compat import text_type, binary_type

TestFloats = strategy_test_suite(arrays(float, ()))
TestIntMatrix = strategy_test_suite(arrays(int, (3, 2)))
TestBoolTensor = strategy_test_suite(arrays(bool, (2, 2, 2)))


STANDARD_TYPES = list(map(np.dtype, [
    u'int8', u'int32', u'int64',
    u'float', u'float32', u'float64',
    complex,
    u'datetime64', u'timedelta64',
    bool, text_type, binary_type
]))


@given(nested_dtypes())
def test_strategies_for_standard_dtypes_have_reusable_values(dtype):
    assert from_dtype(dtype).has_reusable_values


@pytest.mark.parametrize(u't', STANDARD_TYPES)
def test_produces_instances(t):
    @given(from_dtype(t))
    def test_is_t(x):
        assert isinstance(x, t.type)
        assert x.dtype.kind == t.kind
    test_is_t()


@given(arrays(float, ()))
def test_empty_dimensions_are_scalars(x):
    assert isinstance(x, np.dtype(float).type)


@given(arrays(float, (1, 0, 1)))
def test_can_handle_zero_dimensions(x):
    assert x.shape == (1, 0, 1)


@given(arrays(u'uint32', (5, 5)))
def test_generates_unsigned_ints(x):
    assert (x >= 0).all()


@given(arrays(int, (1,)))
def test_assert_fits_in_machine_size(x):
    pass


def test_generates_and_minimizes():
    assert (minimal(arrays(float, (2, 2))) == np.zeros(shape=(2, 2))).all()


def test_can_minimize_large_arrays():
    assert minimal(
        arrays(u'uint32', 500), lambda x: np.any(x) and not np.all(x),
        timeout_after=60
    ).sum() == 1


@flaky(max_runs=50, min_passes=1)
def test_can_minimize_float_arrays():
    x = minimal(arrays(float, 50), lambda t: t.sum() >= 1.0)
    assert 1.0 <= x.sum() <= 1.1


class Foo(object):
    pass


foos = st.tuples().map(lambda _: Foo())


def test_can_create_arrays_of_composite_types():
    arr = minimal(arrays(object, 100, foos))
    for x in arr:
        assert isinstance(x, Foo)


def test_can_create_arrays_of_tuples():
    arr = minimal(arrays(object, 10, st.tuples(st.integers(), st.integers())),
                  lambda x: all(t0 != t1 for t0, t1 in x))
    assert all(a in ((1, 0), (0, 1)) for a in arr)


@given(arrays(object, (2, 2), st.tuples(st.integers())))
def test_does_not_flatten_arrays_of_tuples(arr):
    assert isinstance(arr[0][0], tuple)


@given(arrays(object, (2, 2), st.lists(st.integers(), min_size=1, max_size=1)))
def test_does_not_flatten_arrays_of_lists(arr):
    assert isinstance(arr[0][0], list)


@given(arrays(object, 100, st.lists(max_size=0)))
def test_generated_lists_are_distinct(ls):
    assert len({id(x) for x in ls}) == len(ls)


@st.composite
def distinct_integers(draw):
    used = draw(st.shared(st.builds(set)))
    i = draw(st.integers(0, 2 ** 64 - 1).filter(lambda x: x not in used))
    used.add(i)
    return i


@given(arrays('uint64', 10, distinct_integers()))
def test_does_not_reuse_distinct_integers(arr):
    assert len(set(arr)) == len(arr)


@given(array_shapes())
def test_can_generate_array_shapes(shape):
    assert isinstance(shape, tuple)
    assert all(isinstance(i, int) for i in shape)


@given(st.integers(1, 10), st.integers(0, 9), st.integers(1), st.integers(0))
def test_minimise_array_shapes(min_dims, dim_range, min_side, side_range):
    smallest = minimal(array_shapes(min_dims, min_dims + dim_range,
                                    min_side, min_side + side_range))
    assert len(smallest) == min_dims and all(k == min_side for k in smallest)


@given(scalar_dtypes())
def test_can_generate_scalar_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@given(nested_dtypes())
def test_can_generate_compound_dtypes(dtype):
    assert isinstance(dtype, np.dtype)


@given(nested_dtypes(max_itemsize=settings.default.buffer_size // 10),
       st.data())
def test_infer_strategy_from_dtype(dtype, data):
    # Given a dtype
    assert isinstance(dtype, np.dtype)
    # We can infer a strategy
    strat = from_dtype(dtype)
    assert isinstance(strat, SearchStrategy)
    # And use it to fill an array of that dtype
    data.draw(arrays(dtype, 10, strat))


@given(nested_dtypes())
def test_np_dtype_is_idempotent(dtype):
    assert dtype == np.dtype(dtype)


def test_minimise_scalar_dtypes():
    assert minimal(scalar_dtypes()) == np.dtype(u'bool')


def test_minimise_nested_types():
    assert minimal(nested_dtypes()) == np.dtype(u'bool')


def test_minimise_array_strategy():
    smallest = minimal(arrays(
        nested_dtypes(max_itemsize=settings.default.buffer_size // 3**3),
        array_shapes(max_dims=3, max_side=3)))
    assert smallest.dtype == np.dtype(u'bool') and not smallest.any()
