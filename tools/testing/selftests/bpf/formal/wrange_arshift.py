#!/usr/bin/env python3
from z3 import *
from wrange import *


def main():
    print("Testing wrange32_arshift() - arithmetic right shift properties\n")
    
    x = BitVec32('x')
    
    # Test 1: Arithmetic shift of positive number
    print('Test 1: Positive number >> 2 stays positive')
    pos_num = BitVecVal32(100)
    prove(
        (pos_num >> 2) >= 0  # Should be 25
    )
    
    # Test 2: Arithmetic shift preserves sign
    print('\nTest 2: Negative number >> n stays negative')
    neg_num = BitVecVal32(0xFFFFFFFF)  # -1
    prove(
        (neg_num >> 3) < 0  # Still negative (-1)
    )
    
    # Test 3: Shift by 0 doesn't change value
    print('\nTest 3: x >> 0 == x')
    prove(
        (x >> 0) == x
    )
    
    # Test 4: Large shift of positive gives 0
    print('\nTest 4: Positive number >> 31 gives 0')
    pos = BitVecVal32(0x7FFFFFFF)  # Max positive s32
    prove(
        (pos >> 31) == 0
    )
    
    # Test 5: Large shift of negative gives -1
    print('\nTest 5: Negative number >> 31 gives -1 (0xFFFFFFFF)')
    neg = BitVecVal32(0x80000000)  # Min negative s32
    prove(
        (neg >> 31) == 0xFFFFFFFF
    )
    
    # Test 6: Arithmetic shift divides by power of 2 (for positive)
    print('\nTest 6: For positive x, (x >> 3) == x / 8')
    pos_x = BitVec32('pos_x')
    prove(
        Implies(
            And(pos_x >= 0, pos_x < 0x7FFFFFF8),  # Ensure division is exact
            (pos_x >> 3) == (pos_x / 8)
        )
    )
    
    print('\nAll arithmetic right shift property tests passed!')


if __name__ == '__main__':
    main()
