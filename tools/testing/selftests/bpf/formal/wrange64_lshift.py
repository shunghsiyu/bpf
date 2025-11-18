#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_lshift(a: Wrange, shift: int):
    """Model the C wrange64_lshift() function in Z3"""
    wrange_class = type(a)

    # Shift must be < 64
    if shift >= a.SIZE:
        return wrange_class(f'{a.name} << {shift}',
                          BitVecVal(0, bv=a.SIZE),
                          BitVecVal(0, bv=a.SIZE))

    # Maximum safe value that won't overflow
    max_safe = BitVecVal(2**a.SIZE - 1, bv=a.SIZE) >> shift

    # If would overflow, return full range
    would_overflow = UGT(a.umax, max_safe)

    # Non-wrapping case: simple shift
    result_start = If(would_overflow,
                     BitVecVal(0, bv=a.SIZE),
                     If(a.uwrapping, BitVecVal(0, bv=a.SIZE), a.start << shift))
    result_end = If(would_overflow,
                   BitVecVal(2**a.SIZE - 1, bv=a.SIZE),
                   If(a.uwrapping, BitVecVal(2**a.SIZE - 1, bv=a.SIZE), a.end << shift))

    return wrange_class(f'{a.name} << {shift}', result_start, result_end)


def main():
    print("Testing wrange64_lshift()\n")

    # Test 1: Simple left shift (multiply by 4)
    w = Wrange64('w', start=BitVecVal64(4), end=BitVecVal64(8))
    result = wrange_lshift(w, 2)
    print('Test 1: {4..8} << 2 = {16..32}')
    prove(
        And(result.start == 16, result.end == 32)
    )

    # Test 2: Shift by 0 (no change)
    w = Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200))
    result = wrange_lshift(w, 0)
    print('\nTest 2: {100..200} << 0 = {100..200}')
    prove(
        And(result.start == 100, result.end == 200)
    )

    # Test 3: Small shift
    w = Wrange64('w', start=BitVecVal64(1), end=BitVecVal64(3))
    result = wrange_lshift(w, 3)
    print('\nTest 3: {1..3} << 3 = {8..24}')
    prove(
        And(result.start == 8, result.end == 24)
    )

    # Test 4: Single value
    w = Wrange64('w', start=BitVecVal64(5), end=BitVecVal64(5))
    result = wrange_lshift(w, 4)
    print('\nTest 4: {5} << 4 = {80}')
    prove(
        And(result.start == 80, result.end == 80)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
