#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_union(a: Wrange, b: Wrange):
    """Model the C wrange64_union() function in Z3 (simplified)"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range handling
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    if_a_empty = is_a_empty
    if_b_empty = is_b_empty

    # Both non-wrapping case (simple)
    both_nonwrap = And(Not(a.uwrapping), Not(b.uwrapping))
    new_start_nonwrap = If(ULT(a.start, b.start), a.start, b.start)
    new_end_nonwrap = If(UGT(a.end, b.end), a.end, b.end)

    # Conservative: other cases return full range
    result_start = If(if_a_empty, b.start,
                     If(if_b_empty, a.start,
                        If(both_nonwrap, new_start_nonwrap,
                           BitVecVal(0, a.SIZE))))

    result_end = If(if_a_empty, b.end,
                   If(if_b_empty, a.end,
                      If(both_nonwrap, new_end_nonwrap,
                         BitVecVal(2**a.SIZE - 1, a.SIZE))))

    return wrange_class(f'{a.name} ∪ {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_union()\n")

    # Test 1: Union of overlapping ranges
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(30))
    w2 = Wrange64('w2', start=BitVecVal64(20), end=BitVecVal64(40))
    w = wrange_union(w1, w2)
    print('Test 1: {10..30} ∪ {20..40} = {10..40}')
    prove(
        And(w.start == 10, w.end == 40)
    )

    # Test 2: Union with empty range
    w1 = Wrange64('w1', start=BitVecVal64(1), end=BitVecVal64(0))  # empty
    w2 = Wrange64('w2', start=BitVecVal64(100), end=BitVecVal64(200))
    w = wrange_union(w1, w2)
    print('\nTest 2: empty ∪ {100..200} = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 3: Union of adjacent ranges
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(20))
    w2 = Wrange64('w2', start=BitVecVal64(21), end=BitVecVal64(30))
    w = wrange_union(w1, w2)
    print('\nTest 3: {10..20} ∪ {21..30} = {10..30}')
    prove(
        And(w.start == 10, w.end == 30)
    )

    # Test 4: Union of identical ranges
    w1 = Wrange64('w1', start=BitVecVal64(50), end=BitVecVal64(100))
    w2 = Wrange64('w2', start=BitVecVal64(50), end=BitVecVal64(100))
    w = wrange_union(w1, w2)
    print('\nTest 4: {50..100} ∪ {50..100} = {50..100}')
    prove(
        And(w.start == 50, w.end == 100)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
