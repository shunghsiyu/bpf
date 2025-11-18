# Phase 4 Plan: BPF Verifier Integration

**Status**: 🔄 IN PROGRESS
**Goal**: Integrate wrange32 and wrange64 into the BPF verifier to replace separate min/max tracking

---

## Current State Analysis

### Register State Structure (include/linux/bpf_verifier.h)

Current tracking in `struct bpf_reg_state` (lines 124-131):

```c
struct bpf_reg_state {
    /* ... */
    struct tnum var_off;       /* Bit-level tracking */

    /* Current approach: 8 separate fields */
    s64 smin_value;            /* minimum possible (s64)value */
    s64 smax_value;            /* maximum possible (s64)value */
    u64 umin_value;            /* minimum possible (u64)value */
    u64 umax_value;            /* maximum possible (u64)value */
    s32 s32_min_value;         /* minimum possible (s32)value */
    s32 s32_max_value;         /* maximum possible (s32)value */
    u32 u32_min_value;         /* minimum possible (u32)value */
    u32 u32_max_value;         /* maximum possible (u32)value */
    /* ... */
};
```

**Current size**: 8 fields × 8 bytes = 64 bytes of tracking data

### Proposed wrange Integration

Replace with unified wrapped range tracking:

```c
struct bpf_reg_state {
    /* ... */
    struct tnum var_off;       /* Bit-level tracking (keep for now) */

    /* New approach: 2 wrange structures */
    struct wrange64 var_range;     /* 64-bit unified tracking */
    struct wrange32 var32_range;   /* 32-bit subregister tracking */
    /* ... */
};
```

**New size**: 16 bytes (wrange64) + 8 bytes (wrange32) = 24 bytes
**Savings**: 40 bytes per register (62.5% reduction)

---

## Integration Strategy

### Phase 4A: Add wrange Fields (Parallel Tracking)

**Goal**: Add wrange fields alongside existing min/max, verify they stay synchronized

**Changes**:
1. Add `var_range` and `var32_range` to `struct bpf_reg_state`
2. Update all operations to populate both old and new tracking
3. Add debug assertions to verify consistency
4. No functional changes yet - just dual tracking

**Benefits**:
- Safe: Old tracking still primary, new tracking validated
- Testable: Can compare results at every step
- Reversible: Can easily remove if problems found

### Phase 4B: Migrate Operations (Gradual Transition)

**Goal**: Convert operations one-by-one to use wrange

**Conversion order**:
1. Read operations (easier, no state changes)
   - `reg_bounds_sanity_check()`
   - `print_verifier_state()`

2. Simple operations (single range manipulation)
   - Constants: `mark_reg_known()`
   - Negation: `scalar_min_max_neg()`

3. Arithmetic operations
   - `scalar_min_max_add()`
   - `scalar_min_max_sub()`
   - `scalar_min_max_mul()`

4. Bitwise operations
   - `scalar_min_max_and()`
   - `scalar_min_max_or()`
   - `scalar_min_max_xor()`

5. Shift operations
   - `scalar_min_max_lsh()`
   - `scalar_min_max_rsh()`
   - `scalar_min_max_arsh()`

6. Complex operations
   - `__reg_bound_offset()` (32↔64 conversions)
   - `reg_bounds_sync()` (tnum ↔ wrange synchronization)

### Phase 4C: Remove Old Tracking

**Goal**: Remove old min/max fields once all operations migrated

**Changes**:
1. Remove old fields from `struct bpf_reg_state`
2. Update serialization/deserialization
3. Update BTF definitions if needed
4. Final cleanup

---

## Implementation Plan

### Step 1: Analyze Verifier Operations

**File**: `kernel/bpf/verifier.c` (~20,000 lines)

Key functions to update:

```bash
# Arithmetic operations (~8 functions)
scalar_min_max_add()
scalar_min_max_sub()
scalar_min_max_mul()
scalar_min_max_div()
scalar_min_max_mod()

# Bitwise operations (~3 functions)
scalar_min_max_and()
scalar_min_max_or()
scalar_min_max_xor()

# Shift operations (~3 functions)
scalar_min_max_lsh()
scalar_min_max_rsh()
scalar_min_max_arsh()

# Utility functions (~10+ functions)
mark_reg_known()
__mark_reg_known()
__mark_reg_const_zero()
__update_reg_bounds()
reg_bounds_sync()
tnum_subreg()
...
```

### Step 2: Add wrange Fields to bpf_reg_state

**File**: `include/linux/bpf_verifier.h`

```c
struct bpf_reg_state {
    /* ... existing fields ... */
    struct tnum var_off;

    /* Keep old tracking for validation */
    s64 smin_value;
    s64 smax_value;
    u64 umin_value;
    u64 umax_value;
    s32 s32_min_value;
    s32 s32_max_value;
    u32 u32_min_value;
    u32 u32_max_value;

    /* NEW: Unified wrapped range tracking */
    struct wrange64 var_range;      /* 64-bit tracking */
    struct wrange32 var32_range;    /* 32-bit subregister */

    u32 id;
    /* ... rest of fields ... */
};
```

### Step 3: Add Helper Functions

**File**: `kernel/bpf/verifier.c`

Add conversion helpers:

```c
/* Sync wrange from old min/max values */
static void wrange_from_reg(struct bpf_reg_state *reg)
{
    reg->var_range = wrange64_from_min_max(
        reg->smin_value, reg->smax_value,
        reg->umin_value, reg->umax_value);

    reg->var32_range = wrange32_from_min_max(
        reg->s32_min_value, reg->s32_max_value,
        reg->u32_min_value, reg->u32_max_value);
}

/* Sync old min/max values from wrange */
static void wrange_to_reg(struct bpf_reg_state *reg)
{
    wrange64_to_min_max(reg->var_range,
        &reg->smin_value, &reg->smax_value,
        &reg->umin_value, &reg->umax_value);

    wrange32_to_min_max(reg->var32_range,
        &reg->s32_min_value, &reg->s32_max_value,
        &reg->u32_min_value, &reg->u32_max_value);
}

/* Verify synchronization (debug only) */
static void wrange_verify_sync(struct bpf_reg_state *reg)
{
    s64 smin, smax;
    u64 umin, umax;
    s32 s32_min, s32_max;
    u32 u32_min, u32_max;

    wrange64_to_min_max(reg->var_range, &smin, &smax, &umin, &umax);
    wrange32_to_min_max(reg->var32_range, &s32_min, &s32_max, &u32_min, &u32_max);

    WARN_ON(smin != reg->smin_value);
    WARN_ON(smax != reg->smax_value);
    WARN_ON(umin != reg->umin_value);
    WARN_ON(umax != reg->umax_value);
    WARN_ON(s32_min != reg->s32_min_value);
    WARN_ON(s32_max != reg->s32_max_value);
    WARN_ON(u32_min != reg->u32_min_value);
    WARN_ON(u32_max != reg->u32_max_value);
}
```

### Step 4: Convert First Operation (scalar_min_max_add)

**Before** (current code):
```c
static void scalar_min_max_add(struct bpf_reg_state *dst_reg,
                               struct bpf_reg_state *src_reg)
{
    s64 smin_val = src_reg->smin_value;
    s64 smax_val = src_reg->smax_value;
    u64 umin_val = src_reg->umin_value;
    u64 umax_val = src_reg->umax_value;

    /* Complex logic to handle overflow... */
    if (signed_add_overflows(dst_reg->smin_value, smin_val) ||
        signed_add_overflows(dst_reg->smax_value, smax_val)) {
        dst_reg->smin_value = S64_MIN;
        dst_reg->smax_value = S64_MAX;
    } else {
        dst_reg->smin_value += smin_val;
        dst_reg->smax_value += smax_val;
    }

    /* Similar logic for unsigned... */
    /* Similar logic for 32-bit... */
}
```

**After** (with wrange):
```c
static void scalar_min_max_add(struct bpf_reg_state *dst_reg,
                               struct bpf_reg_state *src_reg)
{
    /* NEW: Simple wrange operations */
    dst_reg->var_range = wrange64_add(dst_reg->var_range,
                                       src_reg->var_range);
    dst_reg->var32_range = wrange32_add(dst_reg->var32_range,
                                         src_reg->var32_range);

    /* Update old tracking (Phase 4A: keep in sync) */
    wrange_to_reg(dst_reg);

    /* Debug verification (Phase 4A only) */
    wrange_verify_sync(dst_reg);
}
```

**Complexity**: ~100 lines → ~10 lines (90% reduction)

### Step 5: Testing Strategy

**Regression Tests**:
1. Run full BPF selftest suite
   ```bash
   cd tools/testing/selftests/bpf
   make && ./test_verifier
   ```

2. Check for precision regressions
   - Old approach: May accept/reject certain programs
   - New approach: Should accept same or more programs (wrange can be more precise)

3. Performance testing
   - Measure verifier time on complex programs
   - Check memory usage (should decrease due to smaller struct)

**Expected Issues**:
- Initial mismatches between old and new tracking (debug and fix)
- Edge cases in 32↔64 conversion (zext vs sext)
- tnum synchronization (keep tnum, sync with wrange)

---

## Phase 4 Substeps

### 4.1 Foundation [CURRENT]
- ✅ Analyze verifier structure
- ⏳ Create Phase 4 implementation plan
- ⏳ Add wrange fields to bpf_reg_state
- ⏳ Implement helper functions

### 4.2 Parallel Tracking
- ⏳ Update __mark_reg_known() to populate both
- ⏳ Update scalar_min_max_add() with dual tracking
- ⏳ Add debug verification
- ⏳ Test with simple BPF programs

### 4.3 Gradual Migration
- ⏳ Convert all arithmetic operations
- ⏳ Convert all bitwise operations
- ⏳ Convert all shift operations
- ⏳ Convert utility functions
- ⏳ Run full selftest suite

### 4.4 Cleanup
- ⏳ Remove old min/max fields
- ⏳ Remove dual tracking code
- ⏳ Final testing and validation

---

## Expected Benefits

### Code Simplification
- **Before**: ~100-200 lines per operation (handling 8 fields)
- **After**: ~10-20 lines per operation (2 wrange calls)
- **Reduction**: ~85% less code

### Memory Savings
- **Before**: 64 bytes per register for range tracking
- **After**: 24 bytes per register
- **Savings**: 40 bytes × ~11 registers × N states = significant reduction

### Maintenance
- Single source of truth for range semantics (wrange.c)
- Formally verified operations (Z3 proofs)
- Easier to reason about correctness

### Precision Improvements
- Intersection in from_min_max() preserves more information
- Unified tracking prevents inconsistencies
- Wrapping semantics handled correctly

---

## Risks and Mitigations

### Risk 1: Behavioral Changes
**Risk**: wrange may compute different bounds than old code
**Mitigation**: Parallel tracking phase catches mismatches early

### Risk 2: Performance Regression
**Risk**: wrange operations might be slower than direct min/max
**Mitigation**: Profile and optimize hot paths; inline critical functions

### Risk 3: Breaking Existing Programs
**Risk**: Verifier might reject previously-accepted programs
**Mitigation**: Extensive testing; keep old code as fallback initially

### Risk 4: Complex Edge Cases
**Risk**: Subtle interactions with tnum, pointer arithmetic, etc.
**Mitigation**: Gradual migration allows fixing issues incrementally

---

## Timeline Estimate

| Phase | Tasks | Estimated Lines | Time |
|-------|-------|----------------|------|
| 4A | Add fields, helpers | ~200 lines | 2-3 hours |
| 4B | Convert 1 operation | ~50 lines | 1 hour |
| 4C | Convert remaining ops | ~500 lines | 4-6 hours |
| 4D | Testing & debugging | Variable | 2-4 hours |
| 4E | Cleanup | ~100 lines | 1 hour |
| **Total** | | **~850 lines** | **10-15 hours** |

---

## Next Steps

1. Implement foundation (add fields to struct)
2. Add helper functions (conversion and sync)
3. Convert scalar_min_max_add() as proof of concept
4. Test with simple BPF program
5. Iterate on remaining operations

**Current focus**: Starting with Phase 4.1 - Foundation implementation
