#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_and(a: Wrange, b: Wrange):
    """Model the C wrange64_and() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range handling
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    if_a_empty = is_a_empty
    if_b_empty = is_b_empty

    # AND can only clear bits, never set them
    # Upper bound is min(umax_a, umax_b)
    upper = If(ULT(a.umax, b.umax), a.umax, b.umax)

    # Special case: AND with constant (single-value range)
    a_is_const = (a.start == a.end)
    b_is_const = (b.start == b.end)
    b_small = And(Not(b.uwrapping), ULT(b.end - b.start, 256))
    a_small = And(Not(a.uwrapping), ULT(a.end - a.start, 256))

    # If a is constant and b is small non-wrapping
    case_a_const = And(a_is_const, b_small)
    min_result_a = a.start & b.start
    max_result_a = a.start & b.end
    result_a_precise = ULE(min_result_a, max_result_a)

    # If b is constant and a is small non-wrapping
    case_b_const = And(b_is_const, a_small)
    min_result_b = a.start & b.start
    max_result_b = a.end & b.start
    result_b_precise = ULE(min_result_b, max_result_b)

    # Conservative result
    result_start = If(if_a_empty, BitVecVal(1, a.SIZE),
                     If(if_b_empty, BitVecVal(1, a.SIZE),
                        If(And(case_a_const, result_a_precise), min_result_a,
                           If(And(case_b_const, result_b_precise), min_result_b,
                              BitVecVal(0, a.SIZE)))))

    result_end = If(if_a_empty, BitVecVal(0, a.SIZE),
                   If(if_b_empty, BitVecVal(0, a.SIZE),
                      If(a_is_const, a.start,
                         If(b_is_const, b.start,
                            If(And(case_a_const, result_a_precise), max_result_a,
                               If(And(case_b_const, result_b_precise), max_result_b,
                                  upper))))))

    return wrange_class(f'{a.name} & {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_and()\n")

    # Test 1: AND with mask
    w = wrange_and(
        Wrange64('w', start=BitVecVal64(0), end=BitVecVal64(1000)),
        Wrange64('mask', start=BitVecVal64(0xFF), end=BitVecVal64(0xFF)),
    )
    print('Test 1: {0..1000} & {0xFF} = {0..255}')
    prove(
        And(w.start == 0, ULE(w.end, 255))
    )

    # Test 2: AND bounded by operands
    w1 = Wrange64('w1', start=BitVecVal64(0), end=BitVecVal64(100))
    w2 = Wrange64('w2', start=BitVecVal64(0), end=BitVecVal64(200))
    w = wrange_and(w1, w2)
    print('\nTest 2: {0..100} & {0..200} upper bound <= 100')
    prove(
        ULE(w.end, 100)
    )

    # Test 3: Soundness - result contains all possible AND values
    x = BitVec64('x')
    y = BitVec64('y')
    premise = And(
        w1.contains(x),
        w2.contains(y),
    )
    print('\nTest 3: Soundness check')
    prove(
        Implies(
            premise,
            w.contains(x & y)
        )
    )

    # Test 4: AND with zero
    w = wrange_and(
        Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200)),
        Wrange64('zero', start=BitVecVal64(0), end=BitVecVal64(0)),
    )
    print('\nTest 4: {100..200} & {0} = {0}')
    prove(
        And(w.start == 0, w.end == 0)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
