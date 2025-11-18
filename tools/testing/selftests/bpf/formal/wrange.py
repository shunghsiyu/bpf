#!/usr/bin/env python3
import abc
from z3 import *


# Helpers
BitVec32 = lambda n: BitVec(n, bv=32)
BitVecVal32 = lambda v: BitVecVal(v, bv=32)
BitVec64 = lambda n: BitVec(n, bv=64)
BitVecVal64 = lambda v: BitVecVal(v, bv=64)

class Wrange(abc.ABC):
    SIZE = None # Bitwidth, this will be defined in the subclass
    name: str
    start: BitVecRef
    end: BitVecRef

    def __init__(self, name, start=None, end=None):
        self.name = name
        self.start = BitVec(f'Wrange{self.SIZE}-{name}-start', bv=self.SIZE) if start is None else start
        assert(self.start.size() == self.SIZE)
        self.end = BitVec(f'Wrange{self.SIZE}-{name}-end', bv=self.SIZE) if end is None else end
        assert(self.end.size() == self.SIZE)

    def wellformed(self):
        # allow end < start, so any start/end combination is valid
        return BoolVal(True)

    @property
    def length(self):
        return self.end - self.start

    @property
    def uwrapping(self):
        # unsigned comparison, (u32)end < (u32)start
        return ULT(self.end, self.start)

    @property
    def umin(self):
        return If(self.uwrapping, BitVecVal(0, bv=self.SIZE), self.start)

    @property
    def umax(self):
        return If(self.uwrapping, BitVecVal(2**self.SIZE - 1, bv=self.SIZE), self.end)

    @property
    def swrapping(self):
        # signed comparison, (s32)end < (s32)start
        return self.end < self.start

    @property
    def smin(self):
        return If(self.swrapping, BitVecVal(1 << (self.SIZE - 1), bv=self.SIZE), self.start)

    @property
    def smax(self):
        return If(self.swrapping, BitVecVal((2**self.SIZE - 1) >> 1, bv=self.SIZE), self.end)

    # Not used in wrange.c, but helps with checking later
    def contains(self, val: BitVecRef):
        assert(val.size() == self.SIZE)
        # start <= val <= end
        nonwrapping_cond = And(ULE(self.start, val), ULE(val, self.end))
        # 0 <= val <= end or start <= val <= 2**32-1
        # (omit checking 0 <= val and val <= 2**32-1 since they're always true)
        wrapping_cond = Or(ULE(val, self.end), ULE(self.start, val))
        return If(self.uwrapping, wrapping_cond, nonwrapping_cond)


class Wrange32(Wrange):
    SIZE = 32 # Working with 32-bit integers


class Wrange64(Wrange):
    SIZE = 64 # Working with 64-bit integers


__all__ = [
        'Wrange',
        'Wrange32',
        'Wrange64',
        'BitVec32',
        'BitVecVal32',
        'BitVec64',
        'BitVecVal64',
]


if __name__ == '__main__':
    print("wrange.py loaded successfully - use as a module")
