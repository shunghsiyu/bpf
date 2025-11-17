#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_lshift(a: Wrange, shift: int):
    """Model the C wrange32_lshift() function in Z3"""
    wrange_class = type(a)
    
    # Shift must be < 32
    if shift >= 32:
        return wrange_class(f'{a.name} << {shift}', BitVecVal(0, bv=a.SIZE), BitVecVal(0, bv=a.SIZE))
    
    max_safe = BitVecVal(2**a.SIZE - 1, bv=a.SIZE) >> shift
    would_overflow = UGT(a.umax, max_safe)
    
    # If would overflow, return full range
    result_start = If(would_overflow, 
                     BitVecVal(0, bv=a.SIZE),
                     a.start << shift)
    result_end = If(would_overflow,
                   BitVecVal(2**a.SIZE - 1, bv=a.SIZE),
                   a.end << shift)
    
    return wrange_class(f'{a.name} << {shift}', result_start, result_end)


def main():
    print("Testing wrange32_lshift()\n")
    
    # Test 1: Simple non-wrapping range
    w = Wrange32('w', start=BitVecVal32(4), end=BitVecVal32(16))
    result = wrange_lshift(w, 2)  # << 2 (multiply by 4)
    print('Test 1: {4..16} << 2 = {16..64}')
    prove(
        And(result.start == 16, result.end == 64)
    )
    
    # Test 2: Shift by 0 (no change)
    w = Wrange32('w', start=BitVecVal32(100), end=BitVecVal32(200))
    result = wrange_lshift(w, 0)
    print('\nTest 2: {100..200} << 0 = {100..200}')
    prove(
        And(result.start == 100, result.end == 200)
    )
    
    # Test 3: Overflow case
    w = Wrange32('w', start=BitVecVal32(0x80000000), end=BitVecVal32(0xFFFFFFFF))
    result = wrange_lshift(w, 1)  # Would overflow
    print('\nTest 3: {0x80000000..0xFFFFFFFF} << 1 overflows → full range')
    prove(
        And(result.start == 0, result.end == 0xFFFFFFFF)
    )
    
    # Test 4: Small safe shift
    w = Wrange32('w', start=BitVecVal32(1), end=BitVecVal32(10))
    result = wrange_lshift(w, 3)  # << 3 (multiply by 8)
    print('\nTest 4: {1..10} << 3 = {8..80}')
    prove(
        And(result.start == 8, result.end == 80)
    )
    
    # Test 5: General soundness for small shifts (to avoid overflow in proof)
    w = Wrange32('w')
    x = BitVec32('x')
    shift_amt = 2
    result = wrange_lshift(w, shift_amt)
    
    print(f'\nTest 5: Soundness - if x in a and x << {shift_amt} doesn\'t overflow,')
    print(f'        then (x << {shift_amt}) in lshift(a, {shift_amt})')
    prove(
        Implies(
            And(
                Not(w.uwrapping),
                w.contains(x),
                ULE(x, 2**32 - 1 >> shift_amt)  # x won't overflow when shifted
            ),
            result.contains(x << shift_amt)
        )
    )
    
    print('\nAll lshift tests passed!')


if __name__ == '__main__':
    main()
