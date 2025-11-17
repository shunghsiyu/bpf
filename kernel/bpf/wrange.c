/* SPDX-License-Identifier: GPL-2.0-only */
#include <linux/wrange.h>

#define WRANGE32(_s, _e) ((struct wrange32) {.start = _s, .end = _e})

struct wrange32 wrange32_from_min_max(s32 s32_min, s32 s32_max,
				      u32 u32_min, u32 u32_max)
{
	u32 start, end, ulen, slen;

	ulen = u32_max - u32_min;
	slen = (u32)s32_max - (u32)s32_min;

	/* The assumption here is that only one of the two s32_{min,max} and
	 * u32_{min,max} ranges are useful at a time. So we just need to use
	 * the range that has a tighter bound.
	 */
	if (ulen <= slen) {
		start = u32_min;
		end = u32_max;
	} else {
		start = s32_min;
		end = s32_max;
	}
	return WRANGE32(start, end);
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
