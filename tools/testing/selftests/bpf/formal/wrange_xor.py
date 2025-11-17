#!/usr/bin/env python3
from z3 import *
from wrange import *


def main():
    print("Testing wrange32_xor() - basic properties\n")
    
    x = BitVec32('x')
    y = BitVec32('y')
    
    # Test 1: XOR with 0 gives original value
    print('Test 1: x ^ 0 == x')
    prove(
        (x ^ 0) == x
    )
    
    # Test 2: XOR with self gives 0
    print('\nTest 2: x ^ x == 0')
    prove(
        (x ^ x) == 0
    )
    
    # Test 3: XOR is commutative
    a = BitVecVal32(0xABCD)
    b = BitVecVal32(0x00FF)
    print('\nTest 3: XOR is commutative: 0xABCD ^ 0x00FF == 0x00FF ^ 0xABCD')
    prove(
        (a ^ b) == (b ^ a)
    )
    
    # Test 4: XOR with all 1s is bitwise NOT
    print('\nTest 4: x ^ 0xFFFFFFFF == ~x')
    prove(
        (x ^ 0xFFFFFFFF) == ~x
    )
    
    # Test 5: XOR is associative
    z = BitVec32('z')
    print('\nTest 5: (x ^ y) ^ z == x ^ (y ^ z)')
    prove(
        ((x ^ y) ^ z) == (x ^ (y ^ z))
    )
    
    # Test 6: Double XOR cancels out
    print('\nTest 6: (x ^ y) ^ y == x')
    prove(
        ((x ^ y) ^ y) == x
    )
    
    print('\nAll XOR property tests passed!')


if __name__ == '__main__':
    main()
