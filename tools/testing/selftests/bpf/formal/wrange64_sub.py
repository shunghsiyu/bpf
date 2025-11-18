#!/usr/bin/env python3
from z3 import *
from wrange import *


def wrange_sub(a: Wrange, b: Wrange):
    wrange_class = type(a)
    assert(a.SIZE == b.SIZE)

    new_length = a.length + b.length
    too_wide = Or(ULT(new_length, a.length), ULT(new_length, b.length))
    new_start = If(too_wide, BitVecVal(0, a.SIZE), a.start - b.end)
    new_end = If(too_wide, BitVecVal(2**a.SIZE-1, a.SIZE), a.end - b.start)
    return wrange_class(f'{a.name} - {b.name}', new_start, new_end)


def main():
    x = BitVec64('x')
    w = wrange_sub(
        # {1, 2, 3}
        Wrange64('w1', start=BitVecVal64(1), end=BitVecVal64(3)),
        # - {0}
        Wrange64('w2', start=BitVecVal64(0), end=BitVecVal64(0)),
    )   # = {1, 2, 3}
    print('Checking {1, 2, 3} - {0} = {1, 2, 3}')
    prove(               # 1 <= x <= 3
        w.contains(x) == And(1 <= x, x <= 3)
    )

    w = wrange_sub(
        # {-1}
        Wrange64('w1', start=BitVecVal64(-1), end=BitVecVal64(-1)),
        # - {0, 1, 2}
        Wrange64('w2', start=BitVecVal64(0), end=BitVecVal64(2)),
    )   # = {-3, -2, -1}
    print('\nChecking {-1} - {0, 1, 2} = {-3, -2, -1}')
    prove(               # -3 <= x <= -1
        w.contains(x) == And(-3 <= x, x <= -1),
    )

    # A general check to make sure wrange_sub() is sound
    w1 = Wrange64('w1')
    w2 = Wrange64('w2')
    w = wrange_sub(w1, w2)
    x = BitVec64('x')
    y = BitVec64('y')
    premise = And(
        w1.wellformed(),
        w2.wellformed(),
        w1.contains(x),
        w2.contains(y),
    )
    print('\nChecking that if w1.contains(x) and w2.contains(y), then wrange64_sub(w1, w2).contains(x-y)')
    print('(note: this may take awhile)')
    prove(
        Implies(
            premise,
            And(
                w.contains(x - y),
                w.wellformed(),
            ),
        )
    )

if __name__ == '__main__':
    main()
