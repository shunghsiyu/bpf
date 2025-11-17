# Phase 2 Implementation Plan: Enhanced Operations

**Status**: 🚧 IN PROGRESS
**Goal**: Complete set of wrange32 operations for full BPF verifier support

---

## Objectives

Phase 2 focuses on implementing all remaining operations needed for the BPF verifier to fully adopt wrange32, with emphasis on bitwise operations and improved arithmetic.

### Priority 1: Bitwise Operations (Essential)

These are critical for the verifier to handle bitwise BPF instructions:

1. **wrange32_and()** - Bitwise AND
   - Used for: Masking operations, alignment checks
   - Complexity: Medium - can narrow ranges significantly
   - Example: `x & 0xFF` → `[0, 255]`

2. **wrange32_or()** - Bitwise OR
   - Used for: Flag setting, combining values
   - Complexity: Medium - expands ranges
   - Example: `x | 0x1` → sets bit 0

3. **wrange32_xor()** - Bitwise XOR
   - Used for: Toggling bits, hashing
   - Complexity: Medium-High
   - Example: `x ^ 0xFFFFFFFF` → bitwise NOT

4. **wrange32_lshift()** - Left shift
   - Used for: Multiplication by powers of 2
   - Complexity: Medium - can cause overflow
   - Example: `x << 3` → multiply by 8

5. **wrange32_rshift()** - Logical right shift
   - Used for: Division by powers of 2 (unsigned)
   - Complexity: Low-Medium - narrows range
   - Example: `x >> 3` → divide by 8

6. **wrange32_arshift()** - Arithmetic right shift
   - Used for: Division by powers of 2 (signed)
   - Complexity: Medium - preserves sign bit
   - Example: `(s32)x >> 3` → signed divide by 8

### Priority 2: Enhanced Multiplication (Optional but Valuable)

**wrange32_mul_enhanced()** - Better multiplication
- Current limitation: Only handles values ≤ U16_MAX, rejects negatives
- Improvements:
  - Handle negative numbers correctly
  - Use corner case analysis for larger values
  - More precise range computation

---

## Implementation Strategy

### Approach for Bitwise Operations

Bitwise operations are challenging because they can create complex patterns. We'll use a pragmatic approach:

1. **Exact for small ranges** - Enumerate all possibilities when feasible
2. **Conservative for large ranges** - Use sound over-approximations
3. **Special case common patterns** - Optimize for masks, powers of 2, etc.

### Key Principles

- **Soundness first**: Never return a range that doesn't contain all possible results
- **Precision where possible**: Tight bounds for common cases
- **Performance aware**: O(1) operations, avoid enumeration when possible

---

## Detailed Operation Specifications

### 1. wrange32_and()

**Signature**: `struct wrange32 wrange32_and(struct wrange32 a, struct wrange32 b)`

**Algorithm**:
```c
// Special cases
if (b == [k, k]) {  // AND with constant
    // Result is always in [0, k]
    return wrange32_intersect(a, [0, k]);
}

// For power-of-2 minus 1 masks (0xFF, 0xFFFF, etc.)
if (b == [mask, mask] && is_pow2_minus_1(mask)) {
    return [0, mask];
}

// General case: conservative
// AND can only clear bits, so result ≤ min(umax(a), umax(b))
u32 upper = min(wrange32_umax(a), wrange32_umax(b));
return [0, upper];
```

**Z3 verification**: Prove `∀x∈a, ∀y∈b: (x & y) ∈ wrange32_and(a,b)`

### 2. wrange32_or()

**Signature**: `struct wrange32 wrange32_or(struct wrange32 a, struct wrange32 b)`

**Algorithm**:
```c
// Special cases
if (a == [0, 0]) return b;  // 0 | x = x
if (b == [0, 0]) return a;  // x | 0 = x

// OR can only set bits, so result ≥ max(umin(a), umin(b))
u32 lower = max(wrange32_umin(a), wrange32_umin(b));

// Upper bound: conservative - all bits from either operand
// Use bit manipulation to find upper bound
u32 upper = compute_or_upper_bound(a, b);

return [lower, upper];
```

### 3. wrange32_xor()

**Signature**: `struct wrange32 wrange32_xor(struct wrange32 a, struct wrange32 b)`

**Algorithm**:
```c
// Special cases
if (b == [0, 0]) return a;  // x ^ 0 = x
if (a == [k, k] && b == [k, k]) return [0, 0];  // k ^ k = 0

// XOR with constant all-ones is bitwise NOT
if (b == [U32_MAX, U32_MAX]) {
    return [~a.end, ~a.start];  // Inverts the range
}

// General case: very conservative
// XOR can flip any bits, making analysis hard
return [0, U32_MAX];  // Conservative fallback for general case
```

### 4. wrange32_lshift()

**Signature**: `struct wrange32 wrange32_lshift(struct wrange32 a, u32 shift)`

**Algorithm**:
```c
// Shift must be < 32
if (shift >= 32) return [0, 0];

// Check for overflow
u32 max_value_before_overflow = U32_MAX >> shift;

if (wrange32_umax(a) > max_value_before_overflow) {
    // Would overflow - conservative
    return [0, U32_MAX];
}

// No overflow - simple shift
return [a.start << shift, a.end << shift];
```

### 5. wrange32_rshift()

**Signature**: `struct wrange32 wrange32_rshift(struct wrange32 a, u32 shift)`

**Algorithm**:
```c
// Shift must be < 32
if (shift >= 32) return [0, 0];

// Right shift narrows the range
if (!wrange32_uwrapping(a)) {
    return [a.start >> shift, a.end >> shift];
}

// Wrapping case: conservative
return [0, U32_MAX >> shift];
```

### 6. wrange32_arshift()

**Signature**: `struct wrange32 wrange32_arshift(struct wrange32 a, u32 shift)`

**Algorithm**:
```c
// Arithmetic right shift - preserves sign bit
if (shift >= 32) {
    // All bits become sign bit
    if (wrange32_smin(a) < 0)
        return [U32_MAX, U32_MAX];  // -1
    else
        return [0, 0];
}

if (!wrange32_swrapping(a)) {
    // Non-wrapping in signed domain
    s32 smin = wrange32_smin(a);
    s32 smax = wrange32_smax(a);
    return [(u32)(smin >> shift), (u32)(smax >> shift)];
}

// Wrapping in signed domain: conservative
return [U32_MIN, U32_MAX];
```

---

## Z3 Verification Strategy

For each operation, create a test file `wrange_<op>.py` that verifies:

1. **Soundness**: All actual results are contained in computed range
2. **Specific test cases**: Known inputs/outputs
3. **Edge cases**: Wrapping, overflow, underflow, zeros, max values

Example structure:
```python
def wrange_<op>(a, b):
    # Z3 model of the C implementation
    ...

def test_<op>():
    # Test case 1: Concrete example
    # Test case 2: Another concrete example
    # Test case 3: General soundness proof
    prove(
        Implies(
            And(a.contains(x), b.contains(y)),
            result.contains(x <op> y)
        )
    )
```

---

## Implementation Order

1. **wrange32_rshift()** - Simplest, good starting point
2. **wrange32_lshift()** - Similar to rshift
3. **wrange32_and()** - Very useful, moderate complexity
4. **wrange32_or()** - Similar to AND
5. **wrange32_arshift()** - Builds on rshift
6. **wrange32_xor()** - Most complex bitwise
7. **wrange32_mul_enhanced()** - If time permits

---

## Testing Plan

### Unit Tests (Z3)
- Each operation gets its own verification file
- Test non-wrapping cases thoroughly
- Test wrapping cases where feasible
- Prove soundness for at least non-wrapping cases

### Integration Tests
- Test combinations of operations
- Verify operations compose correctly
- Example: `(a & b) | c` should be sound

### Performance Tests
- Ensure all operations are O(1)
- No expensive enumeration in implementation

---

## Success Criteria

Phase 2 is complete when:

- ✅ All 6 bitwise operations implemented
- ✅ All operations have Z3 verification tests
- ✅ All verification tests pass
- ✅ Code is documented and clean
- ✅ Operations handle edge cases correctly
- ✅ Phase 2 completion report written

---

## Timeline Estimate

- Bitwise operations: 3-5 days
  - Design & implement: 2 days
  - Z3 verification: 2 days
  - Testing & refinement: 1 day

- Enhanced multiplication: 1-2 days (optional)

**Total**: 3-7 days for complete Phase 2

---

## Next Steps

1. Start with `wrange32_rshift()` - simplest operation
2. Create Z3 verification as we go
3. Build up to more complex operations
4. Document each operation thoroughly
5. Wrap up with completion report

Let's begin! 🚀
