#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_arshift(a: Wrange, shift: int):
    """Model the C wrange64_arshift() function in Z3"""
    wrange_class = type(a)

    # Shift must be < 64
    if shift >= a.SIZE:
        # All bits become sign bit
        if_negative = a.smin < 0
        result_val = If(if_negative,
                       BitVecVal(2**a.SIZE - 1, bv=a.SIZE),  # -1
                       BitVecVal(0, bv=a.SIZE))  # 0
        return wrange_class(f'{a.name} >> {shift}', result_val, result_val)

    # If not wrapping in signed domain, compute precisely
    # Use Z3's arithmetic right shift operator
    result_start = If(a.swrapping,
                     BitVecVal(0, bv=a.SIZE),
                     a.start >> shift)
    result_end = If(a.swrapping,
                   BitVecVal(2**a.SIZE - 1, bv=a.SIZE),
                   a.end >> shift)

    return wrange_class(f'{a.name} >> {shift}', result_start, result_end)


def main():
    print("Testing wrange64_arshift()\n")

    # Test 1: Positive range (behaves like logical shift)
    w = Wrange64('w', start=BitVecVal64(64), end=BitVecVal64(128))
    result = wrange_arshift(w, 2)
    print('Test 1: {64..128} >> 2 = {16..32}')
    prove(
        And(result.start == 16, result.end == 32)
    )

    # Test 2: Negative range (preserves sign)
    w = Wrange64('w', start=BitVecVal64(-128), end=BitVecVal64(-64))
    result = wrange_arshift(w, 2)
    print('\nTest 2: {-128..-64} >> 2 = {-32..-16}')
    prove(
        And(result.start == -32, result.end == -16)
    )

    # Test 3: Shift by 0 (no change)
    w = Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200))
    result = wrange_arshift(w, 0)
    print('\nTest 3: {100..200} >> 0 = {100..200}')
    prove(
        And(result.start == 100, result.end == 200)
    )

    # Test 4: Single negative value
    w = Wrange64('w', start=BitVecVal64(-64), end=BitVecVal64(-64))
    result = wrange_arshift(w, 3)
    print('\nTest 4: {-64} >> 3 = {-8}')
    prove(
        And(result.start == -8, result.end == -8)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
