#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_rshift(a: Wrange, shift: int):
    """Model the C wrange32_rshift() function in Z3"""
    wrange_class = type(a)
    
    # Shift must be < 32
    if shift >= 32:
        return wrange_class(f'{a.name} >> {shift}', BitVecVal(0, bv=a.SIZE), BitVecVal(0, bv=a.SIZE))
    
    # Non-wrapping case: simple right shift
    result_start = If(a.uwrapping, 
                     BitVecVal(0, bv=a.SIZE),
                     LShR(a.start, shift))
    result_end = If(a.uwrapping,
                   LShR(BitVecVal(2**a.SIZE - 1, bv=a.SIZE), shift),
                   LShR(a.end, shift))
    
    return wrange_class(f'{a.name} >> {shift}', result_start, result_end)


def main():
    print("Testing wrange32_rshift()\n")
    
    # Test 1: Simple non-wrapping range
    w = Wrange32('w', start=BitVecVal32(16), end=BitVecVal32(64))
    result = wrange_rshift(w, 2)  # >> 2 (divide by 4)
    print('Test 1: {16..64} >> 2 = {4..16}')
    prove(
        And(result.start == 4, result.end == 16)
    )
    
    # Test 2: Shift by 0 (no change)
    w = Wrange32('w', start=BitVecVal32(100), end=BitVecVal32(200))
    result = wrange_rshift(w, 0)
    print('\nTest 2: {100..200} >> 0 = {100..200}')
    prove(
        And(result.start == 100, result.end == 200)
    )
    
    # Test 3: Large shift
    w = Wrange32('w', start=BitVecVal32(0xF0000000), end=BitVecVal32(0xFFFFFFFF))
    result = wrange_rshift(w, 28)  # Shift almost all the way
    print('\nTest 3: {0xF0000000..0xFFFFFFFF} >> 28 = {0xF..0xF}')
    prove(
        And(result.start == 0xF, result.end == 0xF)
    )
    
    # Test 4: Shift >= 32 returns zero
    w = Wrange32('w', start=BitVecVal32(100), end=BitVecVal32(200))
    result = wrange_rshift(w, 32)
    print('\nTest 4: {100..200} >> 32 = {0..0}')
    prove(
        And(result.start == 0, result.end == 0)
    )
    
    # Test 5: General soundness - for non-wrapping ranges
    # If x is in range a, then (x >> shift) should be in rshift(a, shift)
    w = Wrange32('w')
    x = BitVec32('x')
    shift_amt = 3
    result = wrange_rshift(w, shift_amt)
    
    print(f'\nTest 5: Soundness - if x in a, then (x >> {shift_amt}) in rshift(a, {shift_amt})')
    print('(Testing for non-wrapping ranges only)')
    prove(
        Implies(
            And(
                Not(w.uwrapping),
                w.contains(x)
            ),
            result.contains(LShR(x, shift_amt))
        )
    )
    
    print('\nAll rshift tests passed!')


if __name__ == '__main__':
    main()
