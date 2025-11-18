#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_or(a: Wrange, b: Wrange):
    """Model the C wrange64_or() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range handling
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    # Special case: OR with 0
    a_is_zero = And(a.start == 0, a.end == 0)
    b_is_zero = And(b.start == 0, b.end == 0)

    # OR can only set bits, never clear them
    # Lower bound is max(umin_a, umin_b)
    lower = If(UGT(a.umin, b.umin), a.umin, b.umin)

    # Upper bound is umax_a | umax_b
    upper = a.umax | b.umax

    # Both constants: exact result
    both_const = And(a.start == a.end, b.start == b.end)

    result_start = If(is_a_empty, b.start,
                     If(is_b_empty, a.start,
                        If(a_is_zero, b.start,
                           If(b_is_zero, a.start,
                              If(both_const, a.start | b.start,
                                 lower)))))

    result_end = If(is_a_empty, b.end,
                   If(is_b_empty, a.end,
                      If(a_is_zero, b.end,
                         If(b_is_zero, a.end,
                            If(both_const, a.start | b.start,
                               upper)))))

    return wrange_class(f'{a.name} | {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_or()\n")

    # Test 1: OR with zero
    w = wrange_or(
        Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200)),
        Wrange64('zero', start=BitVecVal64(0), end=BitVecVal64(0)),
    )
    print('Test 1: {100..200} | {0} = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 2: OR with constants
    w = wrange_or(
        Wrange64('a', start=BitVecVal64(0x100), end=BitVecVal64(0x100)),
        Wrange64('b', start=BitVecVal64(0x0F), end=BitVecVal64(0x0F)),
    )
    print('\nTest 2: {0x100} | {0x0F} = {0x10F}')
    prove(
        And(w.start == 0x10F, w.end == 0x10F)
    )

    # Test 3: Lower bound check
    w = wrange_or(
        Wrange64('w1', start=BitVecVal64(100), end=BitVecVal64(200)),
        Wrange64('w2', start=BitVecVal64(50), end=BitVecVal64(150)),
    )
    print('\nTest 3: {100..200} | {50..150} lower bound >= 100')
    prove(
        UGE(w.start, 100)
    )

    # Test 4: Soundness check
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(20))
    w2 = Wrange64('w2', start=BitVecVal64(5), end=BitVecVal64(15))
    w = wrange_or(w1, w2)

    x = BitVec64('x')
    y = BitVec64('y')
    premise = And(
        w1.contains(x),
        w2.contains(y),
    )
    print('\nTest 4: Soundness - result contains all possible OR values')
    prove(
        Implies(
            premise,
            w.contains(x | y)
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
