#!/usr/bin/env python3
from z3 import *
from wrange import *
from wrange64_intersect import wrange_intersect


def wrange64_from_min_max(smin, smax, umin, umax):
    """Model the C wrange64_from_min_max() function in Z3"""
    # Create wrange from signed bounds (cast to u64 for storage)
    srange = Wrange64('srange', start=smin, end=smax)

    # Create wrange from unsigned bounds
    urange = Wrange64('urange', start=umin, end=umax)

    # Return intersection to get tightest possible range
    return wrange_intersect(srange, urange)


def main():
    print("Testing wrange64_from_min_max()\n")

    # Test 1: Positive range (signed and unsigned match)
    w = wrange64_from_min_max(
        smin=BitVecVal64(10),
        smax=BitVecVal64(20),
        umin=BitVecVal64(10),
        umax=BitVecVal64(20)
    )
    print('Test 1: Positive range [10,20] s and u match')
    prove(
        And(
            w.smin == 10,
            w.smax == 20,
            w.umin == 10,
            w.umax == 20
        )
    )

    # Test 2: Negative signed range
    # -10 in 64-bit two's complement is 2**64 - 10
    w = wrange64_from_min_max(
        smin=BitVecVal64(2**64 - 10),  # -10 as unsigned representation
        smax=BitVecVal64(2**64 - 5),   # -5 as unsigned representation
        umin=BitVecVal64(2**64 - 10),
        umax=BitVecVal64(2**64 - 5)
    )
    print('\nTest 2: Negative range [-10,-5]')
    # When interpreted as signed, should be -10 and -5
    prove(
        And(
            w.start == 2**64 - 10,
            w.end == 2**64 - 5
        )
    )

    # Test 3: Range where unsigned is tighter
    # Signed: [0, 100], Unsigned: [0, 50]
    # Intersection should give [0, 50]
    w = wrange64_from_min_max(
        smin=BitVecVal64(0),
        smax=BitVecVal64(100),
        umin=BitVecVal64(0),
        umax=BitVecVal64(50)  # Tighter unsigned bound
    )
    print('\nTest 3: Unsigned tighter than signed')
    # Result should be intersection: [0, 50]
    prove(
        And(
            w.start == 0,
            w.end == 50
        )
    )

    # Test 4: Single value
    w = wrange64_from_min_max(
        smin=BitVecVal64(42),
        smax=BitVecVal64(42),
        umin=BitVecVal64(42),
        umax=BitVecVal64(42)
    )
    print('\nTest 4: Single value {42}')
    prove(
        And(
            w.start == 42,
            w.end == 42,
            w.smin == 42,
            w.smax == 42,
            w.umin == 42,
            w.umax == 42
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
