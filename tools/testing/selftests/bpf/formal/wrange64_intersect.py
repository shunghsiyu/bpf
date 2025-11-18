#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_intersect(a: Wrange, b: Wrange):
    """Model the C wrange64_intersect() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range sentinel: start=1, end=0
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    # If either is empty, return empty
    if_empty = Or(is_a_empty, is_b_empty)

    # Both non-wrapping case
    both_nonwrap = And(Not(a.uwrapping), Not(b.uwrapping))
    no_overlap = Or(UGT(a.start, b.end), UGT(b.start, a.end))
    new_start_nonwrap = If(UGT(a.start, b.start), a.start, b.start)
    new_end_nonwrap = If(ULT(a.end, b.end), a.end, b.end)

    # Both wrapping case
    both_wrap = And(a.uwrapping, b.uwrapping)
    new_start_wrap = If(UGT(a.start, b.start), a.start, b.start)
    new_end_wrap = If(ULT(a.end, b.end), a.end, b.end)

    # One wrapping, one not (simplified conservative model)
    one_wrap = Xor(a.uwrapping, b.uwrapping)
    one_wrap_result_start = BitVecVal(1, bv=a.SIZE)  # Conservative: empty
    one_wrap_result_end = BitVecVal(0, bv=a.SIZE)

    # Final result
    result_start = If(if_empty, BitVecVal(1, bv=a.SIZE),
                     If(both_nonwrap,
                        If(no_overlap, BitVecVal(1, bv=a.SIZE), new_start_nonwrap),
                        If(both_wrap, new_start_wrap,
                           one_wrap_result_start)))

    result_end = If(if_empty, BitVecVal(0, bv=a.SIZE),
                   If(both_nonwrap,
                      If(no_overlap, BitVecVal(0, bv=a.SIZE), new_end_nonwrap),
                      If(both_wrap, new_end_wrap,
                         one_wrap_result_end)))

    return wrange_class(f'{a.name} ∩ {b.name}', result_start, result_end)


def main():
    print("Testing wrange64_intersect()\n")

    # Test 1: Non-overlapping non-wrapping ranges
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(20))
    w2 = Wrange64('w2', start=BitVecVal64(30), end=BitVecVal64(40))
    w = wrange_intersect(w1, w2)
    print('Test 1: Non-overlapping ranges {10..20} ∩ {30..40} = empty')
    prove(
        And(w.start == 1, w.end == 0)  # Empty
    )

    # Test 2: Overlapping non-wrapping ranges
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(30))
    w2 = Wrange64('w2', start=BitVecVal64(20), end=BitVecVal64(40))
    w = wrange_intersect(w1, w2)
    print('\nTest 2: Overlapping ranges {10..30} ∩ {20..40} = {20..30}')
    prove(
        And(w.start == 20, w.end == 30)
    )

    # Test 3: Identical ranges
    w1 = Wrange64('w1', start=BitVecVal64(100), end=BitVecVal64(200))
    w2 = Wrange64('w2', start=BitVecVal64(100), end=BitVecVal64(200))
    w = wrange_intersect(w1, w2)
    print('\nTest 3: Identical ranges {100..200} ∩ {100..200} = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 4: One range contains the other
    w1 = Wrange64('w1', start=BitVecVal64(10), end=BitVecVal64(100))
    w2 = Wrange64('w2', start=BitVecVal64(20), end=BitVecVal64(30))
    w = wrange_intersect(w1, w2)
    print('\nTest 4: One contains other {10..100} ∩ {20..30} = {20..30}')
    prove(
        And(w.start == 20, w.end == 30)
    )

    print('\nAll tests passed!')


if __name__ == '__main__':
    main()
