#!/usr/bin/env python3
from z3 import *
from wrange import *


def main():
    print("Testing wrange32_and() - basic properties\n")
    
    # Test 1: AND with constant mask
    print('Test 1: x & 0xFF gives result in [0, 0xFF]')
    x = BitVec32('x')
    mask = BitVecVal32(0xFF)
    # Any value AND 0xFF must be in [0, 0xFF]
    prove(
        ULE(x & mask, 0xFF)
    )
    
    # Test 2: AND is commutative for constants
    a = BitVecVal32(0xABCD)
    b = BitVecVal32(0x00FF)
    print('\nTest 2: AND is commutative: 0xABCD & 0x00FF == 0x00FF & 0xABCD')
    prove(
        (a & b) == (b & a)
    )
    
    # Test 3: AND with 0 gives 0
    print('\nTest 3: x & 0 == 0')
    prove(
        (x & 0) == 0
    )
    
    # Test 4: AND with all 1s gives original value
    print('\nTest 4: x & 0xFFFFFFFF == x')
    prove(
        (x & 0xFFFFFFFF) == x
    )
    
    # Test 5: Result of AND is bounded by both operands
    y = BitVec32('y')
    print('\nTest 5: (x & y) <= x and (x & y) <= y (unsigned)')
    prove(
        And(
            ULE(x & y, x),
            ULE(x & y, y)
        )
    )
    
    print('\nAll AND property tests passed!')


if __name__ == '__main__':
    main()
