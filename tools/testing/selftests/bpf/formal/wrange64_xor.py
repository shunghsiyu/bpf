#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_xor(a: Wrange, b: Wrange):
    """Model the C wrange64_xor() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range handling
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    # Special case: XOR with 0
    a_is_zero = And(a.start == 0, a.end == 0)
    b_is_zero = And(b.start == 0, b.end == 0)

    # Same value: x ^ x = 0
    both_same = And(a.start == a.end, b.start == b.end, a.start == b.start)

    # XOR with all 1s is bitwise NOT
    all_ones = BitVecVal(2**a.SIZE - 1, a.SIZE)
    b_is_max = And(b.start == all_ones, b.end == all_ones)
    a_is_max = And(a.start == all_ones, a.end == all_ones)

    # Both constants: exact result
    both_const = And(a.start == a.end, b.start == b.end)

    # Results for different cases
    result_start = If(Or(is_a_empty, is_b_empty), BitVecVal(1, a.SIZE),
                     If(b_is_zero, a.start,
                        If(a_is_zero, b.start,
                           If(both_same, BitVecVal(0, a.SIZE),
                              If(And(b_is_max, Not(a.uwrapping)), ~a.end,
                                 If(And(a_is_max, Not(b.uwrapping)), ~b.end,
                                    If(both_const, a.start ^ b.start,
                                       BitVecVal(0, a.SIZE))))))))

    result_end = If(Or(is_a_empty, is_b_empty), BitVecVal(0, a.SIZE),
                   If(b_is_zero, a.end,
                      If(a_is_zero, b.end,
                         If(both_same, BitVecVal(0, a.SIZE),
                            If(And(b_is_max, Not(a.uwrapping)), ~a.start,
                               If(And(a_is_max, Not(b.uwrapping)), ~b.start,
                                  If(both_const, a.start ^ b.start,
                                     all_ones)))))))

    return wrange_class(f'{a.name} ^ {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_xor()\n")

    # Test 1: XOR with zero
    w = wrange_xor(
        Wrange64('w', start=BitVecVal64(100), end=BitVecVal64(200)),
        Wrange64('zero', start=BitVecVal64(0), end=BitVecVal64(0)),
    )
    print('Test 1: {100..200} ^ {0} = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 2: XOR with itself
    w = wrange_xor(
        Wrange64('w', start=BitVecVal64(42), end=BitVecVal64(42)),
        Wrange64('w2', start=BitVecVal64(42), end=BitVecVal64(42)),
    )
    print('\nTest 2: {42} ^ {42} = {0}')
    prove(
        And(w.start == 0, w.end == 0)
    )

    # Test 3: XOR with constants
    w = wrange_xor(
        Wrange64('a', start=BitVecVal64(0xAA), end=BitVecVal64(0xAA)),
        Wrange64('b', start=BitVecVal64(0x55), end=BitVecVal64(0x55)),
    )
    print('\nTest 3: {0xAA} ^ {0x55} = {0xFF}')
    prove(
        And(w.start == 0xFF, w.end == 0xFF)
    )

    # Test 4: Soundness check with small ranges
    w1 = Wrange64('w1', start=BitVecVal64(0), end=BitVecVal64(10))
    w2 = Wrange64('w2', start=BitVecVal64(0), end=BitVecVal64(10))
    w = wrange_xor(w1, w2)

    x = BitVec64('x')
    y = BitVec64('y')
    premise = And(
        w1.contains(x),
        w2.contains(y),
    )
    print('\nTest 4: Soundness - result contains all possible XOR values')
    prove(
        Implies(
            premise,
            w.contains(x ^ y)
        )
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
