#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange64_from_wrange32_sext(w32: Wrange32):
    """Model the C wrange64_from_wrange32_sext() function in Z3"""

    # Handle empty range
    is_empty = And(w32.start == 1, w32.end == 0)
    if_empty = is_empty

    # If wrapping in signed 32-bit domain, becomes full s32 range in 64-bit
    if_swrapping = w32.swrapping

    # Sign-extend start and end
    # SignExt extends the sign bit
    sext_start = SignExt(32, w32.start)
    sext_end = SignExt(32, w32.end)

    # S32_MIN = -2^31, S32_MAX = 2^31 - 1
    # Represented as u64 for storage in wrange64
    S32_MIN_as_u64 = BitVecVal64(2**64 - 2**31)  # -2^31 as u64
    S32_MAX_as_u64 = BitVecVal64(2**31 - 1)

    # Results
    result_start = If(if_empty, BitVecVal64(1),
                     If(if_swrapping, S32_MIN_as_u64,
                        sext_start))

    result_end = If(if_empty, BitVecVal64(0),
                   If(if_swrapping, S32_MAX_as_u64,
                      sext_end))

    return Wrange64(f'sext({w32.name})', result_start, result_end)


def main():
    print("Testing wrange64_from_wrange32_sext()\n")

    # Test 1: Positive range (sign bit 0)
    w32 = Wrange32('w32', start=BitVecVal32(10), end=BitVecVal32(20))
    w64 = wrange64_from_wrange32_sext(w32)
    print('Test 1: Positive {10..20} sign-extends to {10..20}')
    prove(
        And(
            w64.start == 10,
            w64.end == 20
        )
    )

    # Test 2: Negative range (sign bit 1)
    # -10 in 32-bit is 2^32 - 10
    # When sign-extended to 64-bit, becomes 2^64 - 10
    w32 = Wrange32('w32',
                   start=BitVecVal32(2**32 - 10),  # -10 as u32
                   end=BitVecVal32(2**32 - 5))     # -5 as u32
    w64 = wrange64_from_wrange32_sext(w32)
    print('\nTest 2: Negative {-10..-5} sign-extends preserving sign')
    prove(
        And(
            w64.start == 2**64 - 10,  # -10 as u64
            w64.end == 2**64 - 5      # -5 as u64
        )
    )

    # Test 3: Zero
    w32 = Wrange32('w32', start=BitVecVal32(0), end=BitVecVal32(0))
    w64 = wrange64_from_wrange32_sext(w32)
    print('\nTest 3: {0} sign-extends to {0}')
    prove(
        And(
            w64.start == 0,
            w64.end == 0
        )
    )

    # Test 4: Soundness - sext preserves signed values
    w32 = Wrange32('w32', start=BitVecVal32(100), end=BitVecVal32(200))
    w64 = wrange64_from_wrange32_sext(w32)

    x32 = BitVec32('x32')
    premise = w32.contains(x32)

    print('\nTest 4: Soundness - sext preserves signed values')
    prove(
        Implies(
            premise,
            w64.contains(SignExt(32, x32))
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
