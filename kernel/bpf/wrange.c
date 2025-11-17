/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/wrange.h>

#define WRANGE32(_s, _e) ((struct wrange32) {.start = _s, .end = _e})

struct wrange32 wrange32_from_min_max(s32 s32_min, s32 s32_max,
				      u32 u32_min, u32 u32_max)
{
	struct wrange32 srange, urange;

	/* Create wrange from signed bounds (cast to u32 for storage) */
	srange = WRANGE32((u32)s32_min, (u32)s32_max);

	/* Create wrange from unsigned bounds */
	urange = WRANGE32(u32_min, u32_max);

	/* Return intersection to get tightest possible range.
	 * This preserves information from both signed and unsigned bounds,
	 * unlike the old approach which only picked the tighter one.
	 * For example, if unsigned says [0, 100] and signed says [50, 75],
	 * we correctly deduce [50, 75] instead of just picking one.
	 */
	return wrange32_intersect(srange, urange);
}

void wrange32_to_min_max(struct wrange32 w, s32 *s32_min, s32 *s32_max,
			 u32 *u32_min, u32 *u32_max)
{
	*s32_min = wrange32_smin(w);
	*s32_max = wrange32_smax(w);
	*u32_min = wrange32_umin(w);
	*u32_max = wrange32_umax(w);
}

struct wrange32 wrange32_add(struct wrange32 a, struct wrange32 b)
{
	u32 a_len = a.end - a.start;
	u32 b_len = b.end - b.start;
	u32 new_len = a_len + b_len;

	/* the new start/end pair goes full circle, so any value is possible */
	if (new_len < a_len || new_len < b_len)
		return WRANGE32(U32_MIN, U32_MAX);
	else
		return WRANGE32(a.start + b.start, a.end + b.end);
}

struct wrange32 wrange32_sub(struct wrange32 a, struct wrange32 b)
{
	u32 a_len = a.end - a.start;
	u32 b_len = b.end - b.start;
	u32 new_len = a_len + b_len;

	/* the new start/end pair goes full circle, so any value is possible */
	if (new_len < a_len || new_len < b_len)
		return WRANGE32(U32_MIN, U32_MAX);
	else
		return WRANGE32(a.start - b.end, a.end - b.start);
}

/* Model checking is still on-going for wrange32_mul() */
struct wrange32 wrange32_mul(struct wrange32 a, struct wrange32 b)
{
	/* Be lazy and don't deal with wrange that contains large value that
	 * may overflow as well as wrange32 with negative number. This can be
	 * improved if needed.
	 */
	if (a.end > U16_MAX || b.end > U16_MAX)
		return WRANGE32(U32_MIN, U32_MAX);
	else if (wrange32_smin(a) < 0 || wrange32_smin(b) < 0)
		return WRANGE32(U32_MIN, U32_MAX);
	else
		return WRANGE32(a.start * b.start, a.end * b.end);
}

/* Set intersection: return range containing values in both a AND b */
struct wrange32 wrange32_intersect(struct wrange32 a, struct wrange32 b)
{
	bool a_wrap, b_wrap;

	/* Handle empty ranges */
	if (wrange32_is_empty(a) || wrange32_is_empty(b))
		return WRANGE32_EMPTY;

	a_wrap = wrange32_uwrapping(a);
	b_wrap = wrange32_uwrapping(b);

	if (!a_wrap && !b_wrap) {
		/* Both non-wrapping: [a.start, a.end] ∩ [b.start, b.end] */
		u32 new_start, new_end;

		/* Check if ranges overlap */
		if (a.start > b.end || b.start > a.end)
			return WRANGE32_EMPTY;

		/* Return overlapping portion */
		new_start = a.start > b.start ? a.start : b.start;
		new_end = a.end < b.end ? a.end : b.end;
		return WRANGE32(new_start, new_end);
	}

	if (a_wrap && b_wrap) {
		/* Both wrapping: intersection is also wrapping
		 * Wrapping range [a.start, U32_MAX] ∪ [0, a.end]
		 * Intersect with [b.start, U32_MAX] ∪ [0, b.end]
		 */
		u32 new_start, new_end;

		/* For wrapping ranges, intersection uses the larger start
		 * and smaller end (which tightens the bounds)
		 */
		new_start = a.start > b.start ? a.start : b.start;
		new_end = a.end < b.end ? a.end : b.end;

		/* Check if result is still wrapping */
		if (new_end < new_start)
			return WRANGE32(new_start, new_end);

		/* If new_end >= new_start, the wrapping ranges don't overlap
		 * in the wrapped portion, so we have [new_start, new_end] as
		 * a non-wrapping range
		 */
		return WRANGE32(new_start, new_end);
	}

	/* One wrapping, one not. WLOG assume 'a' is wrapping, 'b' is not.
	 * Wrapping range a: [a.start, U32_MAX] ∪ [0, a.end]
	 * Non-wrapping range b: [b.start, b.end]
	 */
	if (!a_wrap) {
		struct wrange32 tmp = a;
		a = b;
		b = tmp;
	}

	/* Check if b overlaps with upper part of a: [a.start, U32_MAX] */
	if (b.start >= a.start) {
		/* b is entirely in upper part or spans both parts */
		if (b.end >= a.start)
			return WRANGE32(b.start, b.end);  /* Entire b is in upper part */
		/* b.end < a.start, so no overlap with upper part, check lower */
	}

	/* Check if b overlaps with lower part of a: [0, a.end] */
	if (b.end <= a.end) {
		/* b is entirely in lower part */
		if (b.start <= a.end)
			return WRANGE32(b.start, b.end);  /* Entire b is in lower part */
	}

	/* Check if b spans both parts (b.start <= a.end && b.end >= a.start) */
	if (b.start <= a.end && b.end >= a.start) {
		/* b completely contains the wrapping range, return a */
		return a;
	}

	/* No overlap */
	return WRANGE32_EMPTY;
}

/* Set union: return smallest range containing values in a OR b */
struct wrange32 wrange32_union(struct wrange32 a, struct wrange32 b)
{
	bool a_wrap, b_wrap;

	/* Handle empty ranges */
	if (wrange32_is_empty(a))
		return b;
	if (wrange32_is_empty(b))
		return a;

	a_wrap = wrange32_uwrapping(a);
	b_wrap = wrange32_uwrapping(b);

	if (!a_wrap && !b_wrap) {
		/* Both non-wrapping: simple case */
		u32 new_start, new_end;

		new_start = a.start < b.start ? a.start : b.start;
		new_end = a.end > b.end ? a.end : b.end;
		return WRANGE32(new_start, new_end);
	}

	if (a_wrap && b_wrap) {
		/* Both wrapping: union uses smaller start and larger end */
		u32 new_start, new_end;

		new_start = a.start < b.start ? a.start : b.start;
		new_end = a.end > b.end ? a.end : b.end;

		/* If new_end >= new_start, we've wrapped around completely */
		if (new_end >= new_start)
			return WRANGE32_FULL;

		return WRANGE32(new_start, new_end);
	}

	/* One wrapping, one not.
	 * This is complex - we might create a wrapping range or expand to full.
	 * For simplicity, be conservative and return full range if the
	 * non-wrapping range doesn't fit entirely within the wrapping range.
	 */

	/* WLOG assume 'a' is wrapping, 'b' is not */
	if (!a_wrap) {
		struct wrange32 tmp = a;
		a = b;
		b = tmp;
	}

	/* Check if b is contained in a's upper part [a.start, U32_MAX] */
	if (b.start >= a.start && b.end >= a.start)
		return a;  /* b is in upper part, a already contains it */

	/* Check if b is contained in a's lower part [0, a.end] */
	if (b.start <= a.end && b.end <= a.end)
		return a;  /* b is in lower part, a already contains it */

	/* Check if we can extend a to include b without going full range */
	/* If b bridges the gap between a.end and a.start, we get full range */
	if (b.start <= a.end + 1 && b.end >= a.start - 1)
		return WRANGE32_FULL;

	/* Try to extend a to include b */
	if (b.end < a.start) {
		/* b is in the gap, extend a.end */
		return WRANGE32(a.start, b.end);
	}

	if (b.start > a.end) {
		/* b is in the gap, extend a.start */
		return WRANGE32(b.start, a.end);
	}

	/* Conservative fallback: return full range */
	return WRANGE32_FULL;
}

/* Logical right shift: divide by power of 2 (unsigned) */
struct wrange32 wrange32_rshift(struct wrange32 a, u32 shift)
{
	/* Shift must be < 32 */
	if (shift >= 32)
		return WRANGE32(0, 0);

	/* Right shift narrows the range (divides values) */
	if (!wrange32_uwrapping(a)) {
		/* Non-wrapping: simple case */
		return WRANGE32(a.start >> shift, a.end >> shift);
	}

	/* Wrapping case: range spans wrap point
	 * Wrapping means range includes both large values (near U32_MAX)
	 * and small values (near 0). After right shift, this becomes [0, max]
	 */
	return WRANGE32(0, U32_MAX >> shift);
}

/* Left shift: multiply by power of 2 */
struct wrange32 wrange32_lshift(struct wrange32 a, u32 shift)
{
	u32 max_safe;

	/* Shift must be < 32 */
	if (shift >= 32)
		return WRANGE32(0, 0);

	/* Check for overflow: if any value would overflow, be conservative */
	max_safe = U32_MAX >> shift;  /* Maximum value that won't overflow */

	if (wrange32_umax(a) > max_safe) {
		/* Would overflow - return full range */
		return WRANGE32_FULL;
	}

	/* No overflow possible */
	if (!wrange32_uwrapping(a)) {
		/* Non-wrapping: simple shift */
		return WRANGE32(a.start << shift, a.end << shift);
	}

	/* Wrapping: after shift, might not wrap anymore or might overflow */
	/* Conservative approach: check if shift creates full range */
	if (((a.end - a.start) >> shift) != (a.end >> shift) - (a.start >> shift))
		return WRANGE32_FULL;

	return WRANGE32(a.start << shift, a.end << shift);
}

/* Arithmetic right shift: preserves sign bit */
struct wrange32 wrange32_arshift(struct wrange32 a, u32 shift)
{
	s32 smin, smax;

	/* Shift must be < 32 */
	if (shift >= 32) {
		/* All bits become sign bit */
		if (wrange32_smin(a) < 0)
			return WRANGE32(U32_MAX, U32_MAX);  /* -1 */
		else
			return WRANGE32(0, 0);  /* 0 */
	}

	/* If not wrapping in signed domain, can compute precisely */
	if (!wrange32_swrapping(a)) {
		smin = wrange32_smin(a);
		smax = wrange32_smax(a);
		return WRANGE32((u32)(smin >> shift), (u32)(smax >> shift));
	}

	/* Wrapping in signed domain means range crosses S32_MIN/S32_MAX boundary
	 * After arithmetic shift, this becomes full range
	 */
	return WRANGE32_FULL;
}

/* Bitwise AND: can only clear bits */
struct wrange32 wrange32_and(struct wrange32 a, struct wrange32 b)
{
	u32 umax_a, umax_b, upper;

	/* Handle empty ranges */
	if (wrange32_is_empty(a) || wrange32_is_empty(b))
		return WRANGE32_EMPTY;

	/* AND can only clear bits, never set them
	 * Result is always <= min(umax(a), umax(b))
	 */
	umax_a = wrange32_umax(a);
	umax_b = wrange32_umax(b);
	upper = umax_a < umax_b ? umax_a : umax_b;

	/* Special case: AND with constant (single-value range) */
	if (a.start == a.end) {
		/* [k, k] & b → compute precisely if possible */
		u32 k = a.start;
		if (!wrange32_uwrapping(b) && b.end - b.start < 256) {
			/* Small range: compute min/max by checking endpoints */
			u32 min_result = k & b.start;
			u32 max_result = k & b.end;
			if (min_result <= max_result)
				return WRANGE32(min_result, max_result);
		}
		/* AND with constant: result in [0, k] */
		return WRANGE32(0, k);
	}

	if (b.start == b.end) {
		/* a & [k, k] → symmetric case */
		u32 k = b.start;
		if (!wrange32_uwrapping(a) && a.end - a.start < 256) {
			u32 min_result = a.start & k;
			u32 max_result = a.end & k;
			if (min_result <= max_result)
				return WRANGE32(min_result, max_result);
		}
		return WRANGE32(0, k);
	}

	/* General case: very conservative
	 * AND result is in [0, min(umax(a), umax(b))]
	 */
	return WRANGE32(0, upper);
}

/* Bitwise OR: can only set bits */
struct wrange32 wrange32_or(struct wrange32 a, struct wrange32 b)
{
	u32 umin_a, umin_b, lower;
	u32 umax_a, umax_b;

	/* Handle empty ranges */
	if (wrange32_is_empty(a))
		return b;
	if (wrange32_is_empty(b))
		return a;

	/* Special cases */
	if (a.start == 0 && a.end == 0)
		return b;  /* 0 | x = x */
	if (b.start == 0 && b.end == 0)
		return a;  /* x | 0 = x */

	/* OR can only set bits, never clear them
	 * Result is >= max(umin(a), umin(b))
	 */
	umin_a = wrange32_umin(a);
	umin_b = wrange32_umin(b);
	lower = umin_a > umin_b ? umin_a : umin_b;

	/* Upper bound: OR can set any bit from either operand
	 * Conservative: use bitwise OR of upper bounds
	 */
	umax_a = wrange32_umax(a);
	umax_b = wrange32_umax(b);

	/* For conservative upper bound, check if OR would create larger value */
	if (a.start == a.end && b.start == b.end) {
		/* Both constants: exact result */
		return WRANGE32(a.start | b.start, a.start | b.start);
	}

	/* Conservative upper bound: worst case where all bits are set */
	return WRANGE32(lower, umax_a | umax_b);
}

/* Bitwise XOR: flips bits */
struct wrange32 wrange32_xor(struct wrange32 a, struct wrange32 b)
{
	/* Handle empty ranges */
	if (wrange32_is_empty(a) || wrange32_is_empty(b))
		return WRANGE32_EMPTY;

	/* Special cases */
	if (b.start == 0 && b.end == 0)
		return a;  /* x ^ 0 = x */
	if (a.start == 0 && a.end == 0)
		return b;  /* 0 ^ x = x */

	/* Same value: x ^ x = 0 */
	if (a.start == a.end && b.start == b.end && a.start == b.start)
		return WRANGE32(0, 0);

	/* XOR with all 1s is bitwise NOT */
	if (b.start == U32_MAX && b.end == U32_MAX) {
		if (!wrange32_uwrapping(a))
			return WRANGE32(~a.end, ~a.start);  /* Inverts and reverses */
	}
	if (a.start == U32_MAX && a.end == U32_MAX) {
		if (!wrange32_uwrapping(b))
			return WRANGE32(~b.end, ~b.start);
	}

	/* Both constants: exact result */
	if (a.start == a.end && b.start == b.end)
		return WRANGE32(a.start ^ b.start, a.start ^ b.start);

	/* General case: XOR is very hard to analyze
	 * Can flip any bits, making precise analysis difficult
	 * Conservative: full range
	 */
	return WRANGE32_FULL;
}

/* ========== 64-bit Wrapped Range (wrange64) Implementation ========== */

#define WRANGE64(_s, _e) ((struct wrange64) {.start = _s, .end = _e})

struct wrange64 wrange64_from_min_max(s64 s64_min, s64 s64_max,
				      u64 u64_min, u64 u64_max)
{
	struct wrange64 srange, urange;

	/* Create wrange from signed bounds (cast to u64 for storage) */
	srange = WRANGE64((u64)s64_min, (u64)s64_max);

	/* Create wrange from unsigned bounds */
	urange = WRANGE64(u64_min, u64_max);

	/* Return intersection to get tightest possible range */
	return wrange64_intersect(srange, urange);
}

void wrange64_to_min_max(struct wrange64 w, s64 *s64_min, s64 *s64_max,
			 u64 *u64_min, u64 *u64_max)
{
	*s64_min = wrange64_smin(w);
	*s64_max = wrange64_smax(w);
	*u64_min = wrange64_umin(w);
	*u64_max = wrange64_umax(w);
}

struct wrange64 wrange64_add(struct wrange64 a, struct wrange64 b)
{
	u64 a_len = a.end - a.start;
	u64 b_len = b.end - b.start;
	u64 new_len = a_len + b_len;

	/* the new start/end pair goes full circle, so any value is possible */
	if (new_len < a_len || new_len < b_len)
		return WRANGE64(U64_MIN, U64_MAX);
	else
		return WRANGE64(a.start + b.start, a.end + b.end);
}

struct wrange64 wrange64_sub(struct wrange64 a, struct wrange64 b)
{
	u64 a_len = a.end - a.start;
	u64 b_len = b.end - b.start;
	u64 new_len = a_len + b_len;

	/* the new start/end pair goes full circle, so any value is possible */
	if (new_len < a_len || new_len < b_len)
		return WRANGE64(U64_MIN, U64_MAX);
	else
		return WRANGE64(a.start - b.end, a.end - b.start);
}

struct wrange64 wrange64_mul(struct wrange64 a, struct wrange64 b)
{
	/* Be conservative for large values and negative numbers
	 * Use U32_MAX as threshold since values beyond that are more
	 * likely to overflow when multiplied
	 */
	if (a.end > U32_MAX || b.end > U32_MAX)
		return WRANGE64(U64_MIN, U64_MAX);
	else if (wrange64_smin(a) < 0 || wrange64_smin(b) < 0)
		return WRANGE64(U64_MIN, U64_MAX);
	else
		return WRANGE64(a.start * b.start, a.end * b.end);
}

/* Set intersection: return range containing values in both a AND b */
struct wrange64 wrange64_intersect(struct wrange64 a, struct wrange64 b)
{
	bool a_wrap, b_wrap;

	/* Handle empty ranges */
	if (wrange64_is_empty(a) || wrange64_is_empty(b))
		return WRANGE64_EMPTY;

	a_wrap = wrange64_uwrapping(a);
	b_wrap = wrange64_uwrapping(b);

	if (!a_wrap && !b_wrap) {
		/* Both non-wrapping: [a.start, a.end] ∩ [b.start, b.end] */
		u64 new_start, new_end;

		/* Check if ranges overlap */
		if (a.start > b.end || b.start > a.end)
			return WRANGE64_EMPTY;

		/* Return overlapping portion */
		new_start = a.start > b.start ? a.start : b.start;
		new_end = a.end < b.end ? a.end : b.end;
		return WRANGE64(new_start, new_end);
	}

	if (a_wrap && b_wrap) {
		/* Both wrapping: intersection is also wrapping */
		u64 new_start, new_end;

		new_start = a.start > b.start ? a.start : b.start;
		new_end = a.end < b.end ? a.end : b.end;

		/* Check if result is still wrapping */
		if (new_end < new_start)
			return WRANGE64(new_start, new_end);

		return WRANGE64(new_start, new_end);
	}

	/* One wrapping, one not. WLOG assume 'a' is wrapping, 'b' is not */
	if (!a_wrap) {
		struct wrange64 tmp = a;
		a = b;
		b = tmp;
	}

	/* Check if b overlaps with upper part of a: [a.start, U64_MAX] */
	if (b.start >= a.start) {
		if (b.end >= a.start)
			return WRANGE64(b.start, b.end);
	}

	/* Check if b overlaps with lower part of a: [0, a.end] */
	if (b.end <= a.end) {
		if (b.start <= a.end)
			return WRANGE64(b.start, b.end);
	}

	/* Check if b spans both parts */
	if (b.start <= a.end && b.end >= a.start) {
		return a;
	}

	/* No overlap */
	return WRANGE64_EMPTY;
}

/* Set union: return smallest range containing values in a OR b */
struct wrange64 wrange64_union(struct wrange64 a, struct wrange64 b)
{
	bool a_wrap, b_wrap;

	/* Handle empty ranges */
	if (wrange64_is_empty(a))
		return b;
	if (wrange64_is_empty(b))
		return a;

	a_wrap = wrange64_uwrapping(a);
	b_wrap = wrange64_uwrapping(b);

	if (!a_wrap && !b_wrap) {
		/* Both non-wrapping: simple case */
		u64 new_start, new_end;

		new_start = a.start < b.start ? a.start : b.start;
		new_end = a.end > b.end ? a.end : b.end;
		return WRANGE64(new_start, new_end);
	}

	if (a_wrap && b_wrap) {
		/* Both wrapping: union uses smaller start and larger end */
		u64 new_start, new_end;

		new_start = a.start < b.start ? a.start : b.start;
		new_end = a.end > b.end ? a.end : b.end;

		/* If new_end >= new_start, we've wrapped around completely */
		if (new_end >= new_start)
			return WRANGE64_FULL;

		return WRANGE64(new_start, new_end);
	}

	/* One wrapping, one not */
	if (!a_wrap) {
		struct wrange64 tmp = a;
		a = b;
		b = tmp;
	}

	/* Check if b is contained in a's upper part [a.start, U64_MAX] */
	if (b.start >= a.start && b.end >= a.start)
		return a;

	/* Check if b is contained in a's lower part [0, a.end] */
	if (b.start <= a.end && b.end <= a.end)
		return a;

	/* Check if we can extend a to include b without going full range */
	if (b.start <= a.end + 1 && b.end >= a.start - 1)
		return WRANGE64_FULL;

	/* Try to extend a to include b */
	if (b.end < a.start) {
		return WRANGE64(a.start, b.end);
	}

	if (b.start > a.end) {
		return WRANGE64(b.start, a.end);
	}

	/* Conservative fallback: return full range */
	return WRANGE64_FULL;
}

/* Logical right shift: divide by power of 2 (unsigned) */
struct wrange64 wrange64_rshift(struct wrange64 a, u32 shift)
{
	/* Shift must be < 64 */
	if (shift >= 64)
		return WRANGE64(0, 0);

	/* Right shift narrows the range (divides values) */
	if (!wrange64_uwrapping(a)) {
		/* Non-wrapping: simple case */
		return WRANGE64(a.start >> shift, a.end >> shift);
	}

	/* Wrapping case: range spans wrap point */
	return WRANGE64(0, U64_MAX >> shift);
}

/* Left shift: multiply by power of 2 */
struct wrange64 wrange64_lshift(struct wrange64 a, u32 shift)
{
	u64 max_safe;

	/* Shift must be < 64 */
	if (shift >= 64)
		return WRANGE64(0, 0);

	/* Check for overflow */
	max_safe = U64_MAX >> shift;

	if (wrange64_umax(a) > max_safe) {
		/* Would overflow - return full range */
		return WRANGE64_FULL;
	}

	/* No overflow possible */
	if (!wrange64_uwrapping(a)) {
		/* Non-wrapping: simple shift */
		return WRANGE64(a.start << shift, a.end << shift);
	}

	/* Wrapping: conservative */
	if (((a.end - a.start) >> shift) != (a.end >> shift) - (a.start >> shift))
		return WRANGE64_FULL;

	return WRANGE64(a.start << shift, a.end << shift);
}

/* Arithmetic right shift: preserves sign bit */
struct wrange64 wrange64_arshift(struct wrange64 a, u32 shift)
{
	s64 smin, smax;

	/* Shift must be < 64 */
	if (shift >= 64) {
		/* All bits become sign bit */
		if (wrange64_smin(a) < 0)
			return WRANGE64(U64_MAX, U64_MAX);  /* -1 */
		else
			return WRANGE64(0, 0);  /* 0 */
	}

	/* If not wrapping in signed domain, can compute precisely */
	if (!wrange64_swrapping(a)) {
		smin = wrange64_smin(a);
		smax = wrange64_smax(a);
		return WRANGE64((u64)(smin >> shift), (u64)(smax >> shift));
	}

	/* Wrapping in signed domain: conservative */
	return WRANGE64_FULL;
}

/* Bitwise AND: can only clear bits */
struct wrange64 wrange64_and(struct wrange64 a, struct wrange64 b)
{
	u64 umax_a, umax_b, upper;

	/* Handle empty ranges */
	if (wrange64_is_empty(a) || wrange64_is_empty(b))
		return WRANGE64_EMPTY;

	/* AND can only clear bits, never set them */
	umax_a = wrange64_umax(a);
	umax_b = wrange64_umax(b);
	upper = umax_a < umax_b ? umax_a : umax_b;

	/* Special case: AND with constant (single-value range) */
	if (a.start == a.end) {
		u64 k = a.start;
		if (!wrange64_uwrapping(b) && b.end - b.start < 256) {
			u64 min_result = k & b.start;
			u64 max_result = k & b.end;
			if (min_result <= max_result)
				return WRANGE64(min_result, max_result);
		}
		return WRANGE64(0, k);
	}

	if (b.start == b.end) {
		u64 k = b.start;
		if (!wrange64_uwrapping(a) && a.end - a.start < 256) {
			u64 min_result = a.start & k;
			u64 max_result = a.end & k;
			if (min_result <= max_result)
				return WRANGE64(min_result, max_result);
		}
		return WRANGE64(0, k);
	}

	/* General case: very conservative */
	return WRANGE64(0, upper);
}

/* Bitwise OR: can only set bits */
struct wrange64 wrange64_or(struct wrange64 a, struct wrange64 b)
{
	u64 umin_a, umin_b, lower;
	u64 umax_a, umax_b;

	/* Handle empty ranges */
	if (wrange64_is_empty(a))
		return b;
	if (wrange64_is_empty(b))
		return a;

	/* Special cases */
	if (a.start == 0 && a.end == 0)
		return b;  /* 0 | x = x */
	if (b.start == 0 && b.end == 0)
		return a;  /* x | 0 = x */

	/* OR can only set bits, never clear them */
	umin_a = wrange64_umin(a);
	umin_b = wrange64_umin(b);
	lower = umin_a > umin_b ? umin_a : umin_b;

	/* Upper bound */
	umax_a = wrange64_umax(a);
	umax_b = wrange64_umax(b);

	/* Both constants: exact result */
	if (a.start == a.end && b.start == b.end) {
		return WRANGE64(a.start | b.start, a.start | b.start);
	}

	/* Conservative upper bound */
	return WRANGE64(lower, umax_a | umax_b);
}

/* Bitwise XOR: flips bits */
struct wrange64 wrange64_xor(struct wrange64 a, struct wrange64 b)
{
	/* Handle empty ranges */
	if (wrange64_is_empty(a) || wrange64_is_empty(b))
		return WRANGE64_EMPTY;

	/* Special cases */
	if (b.start == 0 && b.end == 0)
		return a;  /* x ^ 0 = x */
	if (a.start == 0 && a.end == 0)
		return b;  /* 0 ^ x = x */

	/* Same value: x ^ x = 0 */
	if (a.start == a.end && b.start == b.end && a.start == b.start)
		return WRANGE64(0, 0);

	/* XOR with all 1s is bitwise NOT */
	if (b.start == U64_MAX && b.end == U64_MAX) {
		if (!wrange64_uwrapping(a))
			return WRANGE64(~a.end, ~a.start);
	}
	if (a.start == U64_MAX && a.end == U64_MAX) {
		if (!wrange64_uwrapping(b))
			return WRANGE64(~b.end, ~b.start);
	}

	/* Both constants: exact result */
	if (a.start == a.end && b.start == b.end)
		return WRANGE64(a.start ^ b.start, a.start ^ b.start);

	/* General case: conservative */
	return WRANGE64_FULL;
}

/* Conversion: wrange32 to wrange64 with zero extension */
struct wrange64 wrange64_from_wrange32_zext(struct wrange32 w32)
{
	/* Handle empty range */
	if (wrange32_is_empty(w32))
		return WRANGE64_EMPTY;

	/* Zero extension: upper 32 bits are all 0
	 * If wrapping in 32-bit domain, becomes [0, U32_MAX] in 64-bit
	 */
	if (wrange32_uwrapping(w32))
		return WRANGE64(0, U32_MAX);

	/* Non-wrapping: simple extension */
	return WRANGE64((u64)w32.start, (u64)w32.end);
}

/* Conversion: wrange32 to wrange64 with sign extension */
struct wrange64 wrange64_from_wrange32_sext(struct wrange32 w32)
{
	s64 start, end;

	/* Handle empty range */
	if (wrange32_is_empty(w32))
		return WRANGE64_EMPTY;

	/* Sign extension: if wrapping in signed 32-bit domain,
	 * becomes full s32 range in 64-bit
	 */
	if (wrange32_swrapping(w32))
		return WRANGE64((u64)S32_MIN, (u64)S32_MAX);

	/* Non-wrapping in signed domain: sign-extend start and end */
	start = (s64)(s32)w32.start;
	end = (s64)(s32)w32.end;
	return WRANGE64((u64)start, (u64)end);
}

/* Conversion: wrange64 to wrange32 (truncation) */
struct wrange32 wrange32_from_wrange64(struct wrange64 w64)
{
	/* Handle empty range */
	if (wrange64_is_empty(w64))
		return WRANGE32_EMPTY;

	/* If the 64-bit range fits entirely in 32 bits, preserve precision */
	if (w64.start <= U32_MAX && w64.end <= U32_MAX) {
		if (!wrange64_uwrapping(w64))
			return WRANGE32((u32)w64.start, (u32)w64.end);
	}

	/* Truncation: keep only lower 32 bits
	 * This may create or change wrapping behavior
	 */
	return WRANGE32((u32)w64.start, (u32)w64.end);
}
