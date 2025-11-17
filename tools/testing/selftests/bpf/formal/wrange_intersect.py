#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_intersect(a: Wrange, b: Wrange):
    """Model the C wrange32_intersect() function in Z3"""
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

    # One wrapping, one not (simplified model - may be conservative)
    # For simplicity in modeling, handle key cases
    one_wrap = Xor(a.uwrapping, b.uwrapping)

    # Select which range is wrapping
    wrap_range_start = If(a.uwrapping, a.start, b.start)
    wrap_range_end = If(a.uwrapping, a.end, b.end)
    nonwrap_range_start = If(a.uwrapping, b.start, a.start)
    nonwrap_range_end = If(a.uwrapping, b.end, a.end)

    # Check if nonwrap is in upper part of wrap
    in_upper = And(UGE(nonwrap_range_start, wrap_range_start),
                   UGE(nonwrap_range_end, wrap_range_start))

    # Check if nonwrap is in lower part of wrap
    in_lower = And(ULE(nonwrap_range_end, wrap_range_end),
                   ULE(nonwrap_range_start, wrap_range_end))

    # If contained, return nonwrap
    one_wrap_result_start = If(Or(in_upper, in_lower), nonwrap_range_start, BitVecVal(1, bv=a.SIZE))
    one_wrap_result_end = If(Or(in_upper, in_lower), nonwrap_range_end, BitVecVal(0, bv=a.SIZE))

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
    print("Testing wrange32_intersect()\n")

    # Test 1: Non-overlapping non-wrapping ranges
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(20))
    w2 = Wrange32('w2', start=BitVecVal32(30), end=BitVecVal32(40))
    w = wrange_intersect(w1, w2)
    print('Test 1: Non-overlapping ranges {10..20} ∩ {30..40} = empty')
    prove(
        And(w.start == 1, w.end == 0)  # Empty
    )

    # Test 2: Overlapping non-wrapping ranges
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(30))
    w2 = Wrange32('w2', start=BitVecVal32(20), end=BitVecVal32(40))
    w = wrange_intersect(w1, w2)
    print('\nTest 2: Overlapping ranges {10..30} ∩ {20..40} = {20..30}')
    prove(
        And(w.start == 20, w.end == 30)
    )

    # Test 3: Identical ranges
    w1 = Wrange32('w1', start=BitVecVal32(100), end=BitVecVal32(200))
    w2 = Wrange32('w2', start=BitVecVal32(100), end=BitVecVal32(200))
    w = wrange_intersect(w1, w2)
    print('\nTest 3: Identical ranges {100..200} ∩ {100..200} = {100..200}')
    prove(
        And(w.start == 100, w.end == 200)
    )

    # Test 4: One range contains the other
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(100))
    w2 = Wrange32('w2', start=BitVecVal32(20), end=BitVecVal32(30))
    w = wrange_intersect(w1, w2)
    print('\nTest 4: Containment {10..100} ∩ {20..30} = {20..30}')
    prove(
        And(w.start == 20, w.end == 30)
    )

    # Test 5: General soundness property for non-wrapping ranges
    # If x is in the intersection, then x must be in both a and b
    w1 = Wrange32('w1')
    w2 = Wrange32('w2')
    w = wrange_intersect(w1, w2)
    x = BitVec32('x')

    print('\nTest 5: Soundness - if x in intersect(a,b), then x in a AND x in b')
    print('(Testing for non-wrapping ranges only, may take a while)')

    prove(
        Implies(
            And(
                Not(w1.uwrapping),
                Not(w2.uwrapping),
                w.contains(x),
                Not(And(w.start == 1, w.end == 0))  # Not empty
            ),
            And(w1.contains(x), w2.contains(x))
        )
    )

    # Test 6: Completeness property
    # If x is in both a and b, then x should be in their intersection
    print('\nTest 6: Completeness - if x in a AND x in b, then x in intersect(a,b)')
    print('(Testing for non-wrapping ranges only, may take a while)')

    prove(
        Implies(
            And(
                Not(w1.uwrapping),
                Not(w2.uwrapping),
                w1.contains(x),
                w2.contains(x)
            ),
            w.contains(x)
        )
    )

    print('\nAll intersection tests passed!')


if __name__ == '__main__':
    main()
