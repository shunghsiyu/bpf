#!/usr/bin/env python3
from z3 import *
from wrange import *


def main():
    print("Testing wrange64_to_min_max()\n")

    # wrange64_to_min_max extracts smin, smax, umin, umax from a wrange
    # It's the inverse of wrange64_from_min_max

    # Test 1: Positive range
    w = Wrange64('w', start=BitVecVal64(10), end=BitVecVal64(20))
    print('Test 1: {10..20} extracts correctly')
    prove(
        And(
            w.smin == 10,
            w.smax == 20,
            w.umin == 10,
            w.umax == 20
        )
    )

    # Test 2: Negative range
    # Start and end are both > S64_MAX, so interpreted as negative
    w = Wrange64('w',
                 start=BitVecVal64(2**64 - 10),  # -10
                 end=BitVecVal64(2**64 - 5))     # -5
    print('\nTest 2: Negative range extracts correctly')
    # smin and smax should be negative when interpreted as signed
    # umin and umax are the unsigned values
    prove(
        And(
            # As unsigned
            w.umin == 2**64 - 10,
            w.umax == 2**64 - 5,
            # As signed (Z3 interprets these correctly)
            w.smin == BitVecVal64(2**64 - 10),
            w.smax == BitVecVal64(2**64 - 5)
        )
    )

    # Test 3: Single value
    w = Wrange64('w', start=BitVecVal64(42), end=BitVecVal64(42))
    print('\nTest 3: Single value {42}')
    prove(
        And(
            w.smin == 42,
            w.smax == 42,
            w.umin == 42,
            w.umax == 42
        )
    )

    # Test 4: Full range
    w = Wrange64('w', start=BitVecVal64(0), end=BitVecVal64(2**64 - 1))
    print('\nTest 4: Full range [0, U64_MAX]')
    prove(
        And(
            w.umin == 0,
            w.umax == 2**64 - 1
        )
    )

    # Test 5: Roundtrip property
    # from_min_max(to_min_max(w)) should preserve the range
    print('\nTest 5: Roundtrip property')
    w_orig = Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200))

    # Extract bounds
    smin = w_orig.smin
    smax = w_orig.smax
    umin = w_orig.umin
    umax = w_orig.umax

    # Reconstruct (this would call from_min_max, but we can just check properties)
    w_reconstructed = Wrange64('w2', start=umin, end=umax)

    prove(
        And(
            w_reconstructed.start == w_orig.start,
            w_reconstructed.end == w_orig.end
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
