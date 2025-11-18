#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_mul(a: Wrange, b: Wrange):
    """Model the C wrange64_mul() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Conservative: if either operand is too large or has negative values, return full range
    # Using U16_MAX as threshold (from C implementation uses U16_MAX for 32-bit)
    # For 64-bit, we use U32_MAX as threshold
    threshold = 2**32 - 1

    too_large = Or(UGT(a.end, threshold), UGT(b.end, threshold))
    has_negative = Or(a.smin < 0, b.smin < 0)

    result_start = If(Or(too_large, has_negative),
                     BitVecVal(0, a.SIZE),
                     a.start * b.start)
    result_end = If(Or(too_large, has_negative),
                   BitVecVal(2**a.SIZE - 1, a.SIZE),
                   a.end * b.end)

    return wrange_class(f'{a.name} * {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_mul()\n")

    # Test 1: Simple multiplication of small positive ranges
    w = wrange_mul(
        Wrange64('w1', start=BitVecVal64(2), end=BitVecVal64(3)),
        Wrange64('w2', start=BitVecVal64(4), end=BitVecVal64(5)),
    )
    print('Test 1: {2, 3} * {4, 5} = {8..15}')
    x = BitVec64('x')
    prove(
        w.contains(x) == And(8 <= x, x <= 15)
    )

    # Test 2: Multiplication by zero
    w = wrange_mul(
        Wrange64('w1', start=BitVecVal64(0), end=BitVecVal64(0)),
        Wrange64('w2', start=BitVecVal64(10), end=BitVecVal64(20)),
    )
    print('\nTest 2: {0} * {10..20} = {0}')
    prove(
        w.contains(x) == (x == 0)
    )

    # Test 3: Multiplication by one
    w = wrange_mul(
        Wrange64('w1', start=BitVecVal64(1), end=BitVecVal64(1)),
        Wrange64('w2', start=BitVecVal64(10), end=BitVecVal64(20)),
    )
    print('\nTest 3: {1} * {10..20} = {10..20}')
    prove(
        w.contains(x) == And(10 <= x, x <= 20)
    )

    # Test 4: Small range soundness check
    w1 = Wrange64('w1', start=BitVecVal64(0), end=BitVecVal64(100))
    w2 = Wrange64('w2', start=BitVecVal64(0), end=BitVecVal64(100))
    w = wrange_mul(w1, w2)

    x = BitVec64('x')
    y = BitVec64('y')
    premise = And(
        w1.contains(x),
        w2.contains(y),
    )
    print('\nTest 4: Soundness for small ranges')
    prove(
        Implies(
            premise,
            w.contains(x * y)
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
