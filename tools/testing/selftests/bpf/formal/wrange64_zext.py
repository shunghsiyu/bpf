#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange64_from_wrange32_zext(w32: Wrange32):
    """Model the C wrange64_from_wrange32_zext() function in Z3"""

    # Handle empty range
    is_empty = And(w32.start == 1, w32.end == 0)
    if_empty = is_empty

    # If wrapping in 32-bit domain, becomes [0, U32_MAX] in 64-bit
    if_wrapping = w32.uwrapping

    # Results
    result_start = If(if_empty, BitVecVal64(1),
                     If(if_wrapping, BitVecVal64(0),
                        ZeroExt(32, w32.start)))  # Zero-extend 32-bit to 64-bit

    result_end = If(if_empty, BitVecVal64(0),
                   If(if_wrapping, BitVecVal64(2**32 - 1),
                      ZeroExt(32, w32.end)))

    return Wrange64(f'zext({w32.name})', result_start, result_end)


def main():
    print("Testing wrange64_from_wrange32_zext()\n")

    # Test 1: Simple positive range
    w32 = Wrange32('w32', start=BitVecVal32(10), end=BitVecVal32(20))
    w64 = wrange64_from_wrange32_zext(w32)
    print('Test 1: {10..20} zero-extends to {10..20}')
    prove(
        And(
            w64.start == 10,
            w64.end == 20
        )
    )

    # Test 2: Full 32-bit range
    w32 = Wrange32('w32', start=BitVecVal32(0), end=BitVecVal32(2**32 - 1))
    w64 = wrange64_from_wrange32_zext(w32)
    print('\nTest 2: Full 32-bit range extends to [0, U32_MAX]')
    prove(
        And(
            w64.start == 0,
            w64.end == 2**32 - 1
        )
    )

    # Test 3: Single value
    w32 = Wrange32('w32', start=BitVecVal32(42), end=BitVecVal32(42))
    w64 = wrange64_from_wrange32_zext(w32)
    print('\nTest 3: {42} extends to {42}')
    prove(
        And(
            w64.start == 42,
            w64.end == 42
        )
    )

    # Test 4: Soundness - zext preserves unsigned values
    w32 = Wrange32('w32', start=BitVecVal32(100), end=BitVecVal32(200))
    w64 = wrange64_from_wrange32_zext(w32)

    x32 = BitVec32('x32')
    premise = w32.contains(x32)

    print('\nTest 4: Soundness - zext preserves values')
    prove(
        Implies(
            premise,
            w64.contains(ZeroExt(32, x32))
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
