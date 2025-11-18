#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_rshift(a: Wrange, shift: int):
    """Model the C wrange64_rshift() function in Z3"""
    wrange_class = type(a)

    # Shift must be < 64
    if shift >= a.SIZE:
        return wrange_class(f'{a.name} >> {shift}',
                          BitVecVal(0, bv=a.SIZE),
                          BitVecVal(0, bv=a.SIZE))

    # Non-wrapping case: simple right shift
    result_start = If(a.uwrapping,
                     BitVecVal(0, bv=a.SIZE),
                     LShR(a.start, shift))
    result_end = If(a.uwrapping,
                   LShR(BitVecVal(2**a.SIZE - 1, bv=a.SIZE), shift),
                   LShR(a.end, shift))

    return wrange_class(f'{a.name} >> {shift}', result_start, result_end)


def main():
    print("Testing wrange64_rshift()\n")

    # Test 1: Simple right shift of non-wrapping range
    w1 = Wrange64('w1', start=BitVecVal64(16), end=BitVecVal64(32))
    w = wrange_rshift(w1, 2)
    print('Test 1: {16..32} >> 2 = {4..8}')
    prove(
        And(w.start == 4, w.end == 8)
    )

    # Test 2: Right shift by 0 (identity)
    w1 = Wrange64('w1', start=BitVecVal64(100), end=BitVecVal64(200))
    w = wrange_rshift(w1, 0)
    print('\nTest 2: {100..200} >> 0 = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 3: Large shift reduces to small range
    w1 = Wrange64('w1', start=BitVecVal64(0x1000), end=BitVecVal64(0xFFFF))
    w = wrange_rshift(w1, 8)
    print('\nTest 3: {0x1000..0xFFFF} >> 8 = {0x10..0xFF}')
    prove(
        And(w.start == 0x10, w.end == 0xFF)
    )

    # Test 4: Shift of single value
    w1 = Wrange64('w1', start=BitVecVal64(64), end=BitVecVal64(64))
    w = wrange_rshift(w1, 3)
    print('\nTest 4: {64} >> 3 = {8}')
    prove(
        And(w.start == 8, w.end == 8)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
