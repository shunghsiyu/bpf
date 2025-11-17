# Wrapped Range (wrange) Design Document

## Executive Summary

This document outlines the design and implementation plan for completing the wrapped range (wrange) system in the BPF verifier. The wrange approach unifies signed and unsigned range tracking using just two values (start, end) instead of four separate values (smin, smax, umin, umax), significantly reducing complexity.

## Current Status (Completed)

✅ **Core wrange32 structure** (Patches 1-3)
- Basic definition with start/end fields
- Support for "wrapping" ranges (where end < start)
- Helpers for extracting umin/umax and smin/smax
- Z3Py formal verification models

✅ **Arithmetic operations** (Patches 4-6, FIXED)
- `wrange32_add()` - Addition with overflow handling
- `wrange32_sub()` - Subtraction with underflow handling
- `wrange32_mul()` - Multiplication (BUG FIXED: now uses multiplication instead of subtraction)

✅ **Conversion helpers** (Patch 7)
- `wrange32_from_min_max()` - Convert from separate s32/u32 bounds
- `wrange32_to_min_max()` - Convert back to separate bounds

✅ **Z3Py Validation**
- All three arithmetic operations formally verified
- Soundness proofs pass for add/sub/mul

## Remaining Work

### Phase 1: Critical Operations for Conditional Jumps

#### 1.1 Implement wrange32_intersect()

**Purpose**: Used when narrowing range based on conditional branches (e.g., `if (x < 10)`)

**Algorithm**:
```c
struct wrange32 wrange32_intersect(struct wrange32 a, struct wrange32 b)
{
    // If ranges don't overlap, return empty range (special case)
    // Otherwise, return the overlapping portion

    bool a_wrap = wrange32_uwrapping(a);
    bool b_wrap = wrange32_uwrapping(b);

    if (!a_wrap && !b_wrap) {
        // Both non-wrapping: [a.start, a.end] ∩ [b.start, b.end]
        if (b.start > a.end || a.start > b.end)
            return WRANGE32_EMPTY;  // No overlap
        return WRANGE32(max(a.start, b.start), min(a.end, b.end));
    }

    if (a_wrap && b_wrap) {
        // Both wrapping: complex case
        // Need to check if they overlap
        u32 new_start = max(a.start, b.start);
        u32 new_end = min(a.end, b.end);
        return WRANGE32(new_start, new_end);
    }

    // One wrapping, one not: check containment
    // ... (detailed implementation needed)
}
```

**Z3Py Test**: Create `wrange_intersect.py` to verify:
```python
# For all x, if x ∈ a and x ∈ b, then x ∈ intersect(a, b)
# Conversely, if x ∈ intersect(a, b), then x ∈ a and x ∈ b
```

#### 1.2 Implement wrange32_union()

**Purpose**: Used when merging ranges from different code paths

**Algorithm**:
```c
struct wrange32 wrange32_union(struct wrange32 a, struct wrange32 b)
{
    // Return smallest wrange that contains both a and b
    // This may be conservative (contain values not in a or b)

    bool a_wrap = wrange32_uwrapping(a);
    bool b_wrap = wrange32_uwrapping(b);

    if (!a_wrap && !b_wrap) {
        // Simple case: return [min(a.start, b.start), max(a.end, b.end)]
        return WRANGE32(min(a.start, b.start), max(a.end, b.end));
    }

    // If either wraps, check if they can be combined without full range
    // ... (detailed implementation needed)
}
```

**Z3Py Test**: Create `wrange_union.py` to verify:
```python
# For all x, if x ∈ a or x ∈ b, then x ∈ union(a, b)
```

#### 1.3 Handle Empty Ranges

Currently, wrange32 cannot represent an empty set. We need to decide:

**Option A**: Add a flag to mark empty ranges
```c
struct wrange32 {
    u32 start;
    u32 end;
    bool empty;
};
```

**Option B**: Use a special value (e.g., start=1, end=0) to denote empty
```c
#define WRANGE32_EMPTY ((struct wrange32) {.start = 1, .end = 0})

static inline bool wrange32_is_empty(struct wrange32 w) {
    return w.start == 1 && w.end == 0 && !wrange32_uwrapping(w);
}
```

**Recommendation**: Option B is simpler and doesn't increase structure size.

### Phase 2: Improve Conversion Logic

#### 2.1 Better wrange32_from_min_max()

**Current Issue**: The current implementation picks the tighter bound:
```c
if (ulen <= slen) {
    start = u32_min; end = u32_max;
} else {
    start = s32_min; end = s32_max;
}
```

This loses precision when both signed and unsigned bounds contain useful information.

**Improved Algorithm**:
```c
struct wrange32 wrange32_from_min_max(s32 s32_min, s32 s32_max,
                                      u32 u32_min, u32 u32_max)
{
    // Create wrange from both signed and unsigned ranges
    struct wrange32 srange = WRANGE32(s32_min, s32_max);
    struct wrange32 urange = WRANGE32(u32_min, u32_max);

    // Return their intersection (tightest possible range)
    return wrange32_intersect(srange, urange);
}
```

This preserves all information from both signed and unsigned bounds.

#### 2.2 Sync with tnum

Currently, the verifier has 3 value tracking mechanisms:
- 64-bit range (smin64, smax64, umin64, umax64)
- 32-bit range (smin32, smax32, umin32, umax32)
- tnum (tracks individual bits)

With wrange, we'll have:
- wrange64 (64-bit wrapped range)
- wrange32 (32-bit wrapped range)
- tnum

We need functions to:
```c
// Extract bounds from tnum
struct wrange32 wrange32_from_tnum(struct tnum t);

// Constrain tnum based on wrange
struct tnum tnum_intersect_wrange32(struct tnum t, struct wrange32 w);
```

### Phase 3: Enhance wrange32_mul()

**Current Limitations**:
- Only handles values ≤ U16_MAX
- Rejects all negative numbers
- Falls back to full range too often

**Improved Implementation**:

Study the reference implementation: https://github.com/caballa/wrapped-intervals/blob/master/lib/RangeAnalysis/WrappedRange.cpp

Key ideas:
1. For non-wrapping ranges with small positive values: use current approach
2. For ranges containing negative values: handle sign combinations
3. For large values: consider splitting into multiple cases

**Algorithm Sketch**:
```c
struct wrange32 wrange32_mul(struct wrange32 a, struct wrange32 b)
{
    // Check for trivial cases
    if (wrange32_contains(a, 0) && wrange32_contains(b, 0))
        return WRANGE32(0, U32_MAX);  // Conservative

    // Non-wrapping positive ranges
    if (!wrange32_uwrapping(a) && !wrange32_uwrapping(b) &&
        wrange32_smin(a) >= 0 && wrange32_smin(b) >= 0) {
        // Check for overflow
        if (a.end <= U16_MAX && b.end <= U16_MAX)
            return WRANGE32(a.start * b.start, a.end * b.end);
    }

    // Handle signed ranges by considering all 4 corner cases
    u32 corners[4] = {
        a.start * b.start,
        a.start * b.end,
        a.end * b.start,
        a.end * b.end
    };

    // Find min/max of corners and construct range
    // ... (detailed implementation needed)

    // Conservative fallback
    return WRANGE32(U32_MIN, U32_MAX);
}
```

### Phase 4: 64-bit wrange64 Implementation

#### 4.1 Define wrange64

```c
struct wrange64 {
    u64 start;
    u64 end;
};

static inline bool wrange64_uwrapping(struct wrange64 w);
static inline u64 wrange64_umin(struct wrange64 w);
static inline u64 wrange64_umax(struct wrange64 w);
static inline bool wrange64_swrapping(struct wrange64 w);
static inline s64 wrange64_smin(struct wrange64 w);
static inline s64 wrange64_smax(struct wrange64 w);
```

#### 4.2 Implement wrange64 operations

Parallel implementation of all wrange32 operations:
- `wrange64_add()`
- `wrange64_sub()`
- `wrange64_mul()`
- `wrange64_intersect()`
- `wrange64_union()`
- `wrange64_from_min_max()`
- `wrange64_to_min_max()`

#### 4.3 Knowledge exchange between wrange32 and wrange64

**Truncation (64-bit → 32-bit)**:
```c
struct wrange32 wrange32_from_wrange64(struct wrange64 w64)
{
    // If the 64-bit range fits in 32 bits, preserve precision
    if (w64.start <= U32_MAX && w64.end <= U32_MAX)
        return WRANGE32((u32)w64.start, (u32)w64.end);

    // Otherwise, only keep lower 32 bits
    // This creates a wrapping range if necessary
    return WRANGE32((u32)w64.start, (u32)w64.end);
}
```

**Extension (32-bit → 64-bit)**:
```c
// Zero extension
struct wrange64 wrange64_from_wrange32_zext(struct wrange32 w32)
{
    if (wrange32_uwrapping(w32))
        return WRANGE64(0, U32_MAX);  // Wrapping becomes full 32-bit range
    return WRANGE64(w32.start, w32.end);
}

// Sign extension
struct wrange64 wrange64_from_wrange32_sext(struct wrange32 w32)
{
    if (wrange32_swrapping(w32))
        return WRANGE64((u64)S32_MIN, (u64)S32_MAX);  // Wrapping becomes full s32 range

    // Sign-extend start and end
    s64 start = (s64)(s32)w32.start;
    s64 end = (s64)(s32)w32.end;
    return WRANGE64((u64)start, (u64)end);
}
```

### Phase 5: Verifier Integration

#### 5.1 Update scalar32_min_max_* functions

Convert all 32-bit scalar operations to use wrange32:
- ✅ `scalar32_min_max_add()` (already done in patch 8)
- `scalar32_min_max_sub()`
- `scalar32_min_max_mul()`
- `scalar32_min_max_and()`
- `scalar32_min_max_or()`
- `scalar32_min_max_xor()`
- `scalar32_min_max_lsh()`
- `scalar32_min_max_rsh()`
- `scalar32_min_max_arsh()`

#### 5.2 Update scalar_min_max_* functions

Convert all 64-bit scalar operations to use wrange64:
- `scalar_min_max_add()`
- `scalar_min_max_sub()`
- ... (all 64-bit operations)

#### 5.3 Update conditional jump handling

Modify `reg_set_min_max()` and related functions to use wrange intersect:

```c
static void reg_set_min_max(struct bpf_reg_state *true_reg,
                           struct bpf_reg_state *false_reg,
                           u64 val, u8 opcode)
{
    struct wrange64 val_range;

    switch (opcode) {
    case BPF_JLT:  // if (reg < val)
        // true_reg: [0, val-1]
        val_range = WRANGE64(0, val - 1);
        true_reg->wrange = wrange64_intersect(true_reg->wrange, val_range);

        // false_reg: [val, U64_MAX]
        val_range = WRANGE64(val, U64_MAX);
        false_reg->wrange = wrange64_intersect(false_reg->wrange, val_range);
        break;

    // ... other opcodes
    }
}
```

#### 5.4 Remove old min/max fields

Once wrange is fully integrated and tested:
1. Remove `s32_min_value`, `s32_max_value`, `u32_min_value`, `u32_max_value` from `bpf_reg_state`
2. Remove `smin_value`, `smax_value`, `umin_value`, `umax_value` from `bpf_reg_state`
3. Keep only `wrange32` and `wrange64`

This reduces `struct bpf_reg_state` size significantly.

### Phase 6: Testing and Validation

#### 6.1 Unit tests

Create comprehensive Z3Py tests for all operations:
- `wrange_intersect.py`
- `wrange_union.py`
- `wrange64_add.py`, `wrange64_sub.py`, `wrange64_mul.py`
- `wrange_conversion.py` (test 32↔64 bit conversions)

#### 6.2 BPF selftests

Run full BPF selftest suite:
```bash
cd tools/testing/selftests/bpf
make
./test_progs -t verifier
./test_progs -t align
./test_progs -t bounds
```

#### 6.3 Regression testing

Compare verifier behavior before and after wrange integration:
- Ensure no previously passing programs are rejected
- Verify that precision is maintained or improved
- Check for performance regressions

#### 6.4 Fuzzing

Use verifier fuzzer to find edge cases:
```bash
./test_progs -t verifier_array_access
./test_progs -t verifier_bounds
./test_progs -t verifier_value_ptr_arith
```

## Implementation Priority

1. **High Priority** (needed for basic functionality):
   - wrange32_intersect()
   - wrange32_union()
   - Improved wrange32_from_min_max()
   - Convert remaining scalar32_min_max_* functions

2. **Medium Priority** (needed for completeness):
   - Enhanced wrange32_mul()
   - wrange64 implementation
   - wrange32 ↔ wrange64 conversions
   - Conditional jump integration

3. **Low Priority** (optimization/cleanup):
   - Remove old min/max fields
   - Performance optimization
   - Extended fuzzing

## Performance Considerations

**Expected Benefits**:
- Reduced memory: ~32 bytes saved per register state
- Simpler code: 6-way sync instead of 20-way
- Potentially faster: fewer comparisons needed

**Potential Concerns**:
- Wrapping checks add overhead
- More complex algorithms (intersect, union)

**Mitigation**:
- Profile before/after to measure impact
- Optimize hot paths if needed
- Consider caching wrapping flags if beneficial

## References

1. Theoretical foundation: https://dl.acm.org/doi/10.1145/2651360
2. Reference implementation: https://github.com/caballa/wrapped-intervals
3. Original proposal: https://lore.kernel.org/bpf/ZTZxoDJJbX9mrQ9w@u94a/
4. Model checking: https://lore.kernel.org/r/1DA1AC52-6E2D-4CDA-8216-D1DD4648AD55@cs.rutgers.edu

## Timeline Estimate

- **Phase 1** (Critical operations): 1-2 weeks
- **Phase 2** (Conversion improvements): 1 week
- **Phase 3** (Enhanced mul): 1 week
- **Phase 4** (wrange64): 2-3 weeks
- **Phase 5** (Full integration): 2-3 weeks
- **Phase 6** (Testing): 1-2 weeks

**Total**: 8-12 weeks for complete implementation and testing
