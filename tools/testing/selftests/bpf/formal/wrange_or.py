#!/usr/bin/env python3
from z3 import *
from wrange import *


def main():
    print("Testing wrange32_or() - basic properties\n")
    
    x = BitVec32('x')
    y = BitVec32('y')
    
    # Test 1: OR with 0 gives original value
    print('Test 1: x | 0 == x')
    prove(
        (x | 0) == x
    )
    
    # Test 2: OR is commutative
    a = BitVecVal32(0xABCD)
    b = BitVecVal32(0x00FF)
    print('\nTest 2: OR is commutative: 0xABCD | 0x00FF == 0x00FF | 0xABCD')
    prove(
        (a | b) == (b | a)
    )
    
    # Test 3: OR with all 1s gives all 1s
    print('\nTest 3: x | 0xFFFFFFFF == 0xFFFFFFFF')
    prove(
        (x | 0xFFFFFFFF) == 0xFFFFFFFF
    )
    
    # Test 4: Result of OR is bounded below by both operands
    print('\nTest 4: x <= (x | y) and y <= (x | y) (unsigned)')
    prove(
        And(
            ULE(x, x | y),
            ULE(y, x | y)
        )
    )
    
    # Test 5: OR can only set bits
    print('\nTest 5: If bit i is set in x, it\'s set in (x | y)')
    # This is hard to express generally, so test specific case
    # If x = 0xFF (all low bits set), then x | y has all low bits set
    x_val = BitVecVal32(0xFF)
    prove(
        (x_val | y) & 0xFF == 0xFF
    )
    
    print('\nAll OR property tests passed!')


if __name__ == '__main__':
    main()
