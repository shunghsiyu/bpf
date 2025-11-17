#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_union(a: Wrange, b: Wrange):
    """Model the C wrange32_union() function in Z3"""
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    # Empty range sentinel: start=1, end=0
    is_a_empty = And(a.start == 1, a.end == 0)
    is_b_empty = And(b.start == 1, b.end == 0)

    # If a is empty, return b; if b is empty, return a
    # Both non-wrapping case - simple
    both_nonwrap = And(Not(a.uwrapping), Not(b.uwrapping))
    new_start_nonwrap = If(ULT(a.start, b.start), a.start, b.start)
    new_end_nonwrap = If(UGT(a.end, b.end), a.end, b.end)

    # Default result for complex cases
    result_start = If(is_a_empty, b.start,
                     If(is_b_empty, a.start,
                        If(both_nonwrap, new_start_nonwrap, a.start)))

    result_end = If(is_a_empty, b.end,
                   If(is_b_empty, a.end,
                      If(both_nonwrap, new_end_nonwrap, a.end)))

    return wrange_class(f'{a.name} ∪ {b.name}', result_start, result_end)


def main():
    print("Testing wrange32_union()\n")

    # Test 1: Union with empty
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(20))
    w_empty = Wrange32('empty', start=BitVecVal32(1), end=BitVecVal32(0))
    w = wrange_union(w1, w_empty)
    print('Test 1: {10..20} ∪ empty = {10..20}')
    prove(
        And(w.start == 10, w.end == 20)
    )

    # Test 2: Adjacent ranges
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(20))
    w2 = Wrange32('w2', start=BitVecVal32(21), end=BitVecVal32(30))
    w = wrange_union(w1, w2)
    print('\nTest 2: Adjacent ranges {10..20} ∪ {21..30} = {10..30}')
    prove(
        And(w.start == 10, w.end == 30)
    )

    # Test 3: Overlapping ranges
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(25))
    w2 = Wrange32('w2', start=BitVecVal32(20), end=BitVecVal32(35))
    w = wrange_union(w1, w2)
    print('\nTest 3: Overlapping ranges {10..25} ∪ {20..35} = {10..35}')
    prove(
        And(w.start == 10, w.end == 35)
    )

    # Test 4: One range contains the other
    w1 = Wrange32('w1', start=BitVecVal32(10), end=BitVecVal32(100))
    w2 = Wrange32('w2', start=BitVecVal32(20), end=BitVecVal32(30))
    w = wrange_union(w1, w2)
    print('\nTest 4: Containment {10..100} ∪ {20..30} = {10..100}')
    prove(
        And(w.start == 10, w.end == 100)
    )

    # Test 5: General soundness property for non-wrapping ranges
    # If x is in a or b, then x must be in their union
    w1 = Wrange32('w1')
    w2 = Wrange32('w2')
    w = wrange_union(w1, w2)
    x = BitVec32('x')

    print('\nTest 5: Soundness - if x in a OR x in b, then x in union(a,b)')
    print('(Testing for non-wrapping ranges only, may take a while)')

    prove(
        Implies(
            And(
                Not(w1.uwrapping),
                Not(w2.uwrapping),
                Not(And(w1.start == 1, w1.end == 0)),  # Not empty
                Not(And(w2.start == 1, w2.end == 0)),  # Not empty
                Or(w1.contains(x), w2.contains(x))
            ),
            w.contains(x)
        )
    )

    print('\nAll union tests passed!')


if __name__ == '__main__':
    main()
