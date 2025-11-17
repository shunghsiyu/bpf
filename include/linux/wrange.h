/* SPDX-License-Identifier: GPL-2.0-only */
/* wrange: wrapped range
 *
 * A wrange tracks knowledge about a range of possible values using two bound,
 * start and end. The possible value could be any of the values (inclusively)
 * between start and end, and this can work even when end < start. Below is
 * some pseudo code for inferring the possible values within the 32-bit version
 * of wrange:
 *
 *   bool[U32_MAX] possible_values = { false };
 *   for (u32 i = start; i < end; i++)
 *   	possible_values[i] = true;
 *
 * For an intuitive visualization of wrange, one can imagine the 32-bit numeric
 * domain as a circle, where 0 sits at 6 o'clock, and the number increment as
 * we go in clockwise direction. Thus 2^30 sits at 9 o'clock, 2^31 at 12
 * o'clock, 2^31+2^30 at 3 o'clock, so on and so forth. This place 2^32-1 just
 * besides 0, one position away in the counter-clockwise direction. With this
 * visualization wrange can be seen as a line drawn on the circle, starting at
 * start, and goes in clockwise direction until it reaches end, where all the
 * numbers on such line is considered to be a possible value represented by
 * such wrange.
 */
#ifndef _LINUX_WRANGE_H
#define _LINUX_WRANGE_H

#include <linux/types.h>
#include <linux/limits.h>

struct wrange32 {
	/* Allow end < start */
	u32 start;
	u32 end;
};

/* Empty range: Use start=1, end=0 (non-wrapping) as sentinel value */
#define WRANGE32_EMPTY ((struct wrange32) {.start = 1, .end = 0})

/* Full range: All possible u32 values */
#define WRANGE32_FULL ((struct wrange32) {.start = U32_MIN, .end = U32_MAX})

/* Create wrange32 from bpf_reg_state's s32_min/s32_max/u32_min/u32_max */
struct wrange32 wrange32_from_min_max(s32 s32_min, s32 s32_max,
		                      u32 u32_min, u32 u32_max);
/* Turn wrange32 back into s32_min/s32_max/u32_min/u32_max */
void wrange32_to_min_max(struct wrange32 w, s32 *s32_min, s32 *s32_max,
			 u32 *u32_min, u32 *u32_max);

/* Arithmetic operations */
struct wrange32 wrange32_add(struct wrange32 a, struct wrange32 b);
struct wrange32 wrange32_sub(struct wrange32 a, struct wrange32 b);
struct wrange32 wrange32_mul(struct wrange32 a, struct wrange32 b);

/* Set operations */
struct wrange32 wrange32_intersect(struct wrange32 a, struct wrange32 b);
struct wrange32 wrange32_union(struct wrange32 a, struct wrange32 b);

/* Bitwise operations */
struct wrange32 wrange32_and(struct wrange32 a, struct wrange32 b);
struct wrange32 wrange32_or(struct wrange32 a, struct wrange32 b);
struct wrange32 wrange32_xor(struct wrange32 a, struct wrange32 b);

/* Shift operations */
struct wrange32 wrange32_lshift(struct wrange32 a, u32 shift);
struct wrange32 wrange32_rshift(struct wrange32 a, u32 shift);
struct wrange32 wrange32_arshift(struct wrange32 a, u32 shift);

static inline bool wrange32_is_empty(struct wrange32 w) {
	/* Empty range is represented as start=1, end=0 (non-wrapping) */
	return w.start == 1 && w.end == 0;
}

static inline bool wrange32_uwrapping(struct wrange32 w) {
	/* Don't treat empty range as wrapping */
	if (wrange32_is_empty(w))
		return false;
	return w.end < w.start;
}

static inline u32 wrange32_umin(struct wrange32 w) {
	if (wrange32_uwrapping(w))
		return U32_MIN;
	else
		return w.start;
}

static inline u32 wrange32_umax(struct wrange32 w) {
	if (wrange32_uwrapping(w))
		return U32_MAX;
	else
		return w.end;
}

static inline bool wrange32_swrapping(struct wrange32 w) {
	return (s32)w.end < (s32)w.start;
}

/* Helper functions that will be required later */
static inline s32 wrange32_smin(struct wrange32 w) {
	if (wrange32_swrapping(w))
		return S32_MIN;
	else
		return w.start;
}

static inline s32 wrange32_smax(struct wrange32 w) {
	if (wrange32_swrapping(w))
		return S32_MAX;
	else
		return w.end;
}

/* ========== 64-bit Wrapped Range (wrange64) ========== */

struct wrange64 {
	/* Allow end < start */
	u64 start;
	u64 end;
};

/* Empty range: Use start=1, end=0 (non-wrapping) as sentinel value */
#define WRANGE64_EMPTY ((struct wrange64) {.start = 1, .end = 0})

/* Full range: All possible u64 values */
#define WRANGE64_FULL ((struct wrange64) {.start = U64_MIN, .end = U64_MAX})

/* Create wrange64 from bpf_reg_state's s64_min/s64_max/u64_min/u64_max */
struct wrange64 wrange64_from_min_max(s64 s64_min, s64 s64_max,
		                      u64 u64_min, u64 u64_max);
/* Turn wrange64 back into s64_min/s64_max/u64_min/u64_max */
void wrange64_to_min_max(struct wrange64 w, s64 *s64_min, s64 *s64_max,
			 u64 *u64_min, u64 *u64_max);

/* Arithmetic operations */
struct wrange64 wrange64_add(struct wrange64 a, struct wrange64 b);
struct wrange64 wrange64_sub(struct wrange64 a, struct wrange64 b);
struct wrange64 wrange64_mul(struct wrange64 a, struct wrange64 b);

/* Set operations */
struct wrange64 wrange64_intersect(struct wrange64 a, struct wrange64 b);
struct wrange64 wrange64_union(struct wrange64 a, struct wrange64 b);

/* Bitwise operations */
struct wrange64 wrange64_and(struct wrange64 a, struct wrange64 b);
struct wrange64 wrange64_or(struct wrange64 a, struct wrange64 b);
struct wrange64 wrange64_xor(struct wrange64 a, struct wrange64 b);

/* Shift operations */
struct wrange64 wrange64_lshift(struct wrange64 a, u32 shift);
struct wrange64 wrange64_rshift(struct wrange64 a, u32 shift);
struct wrange64 wrange64_arshift(struct wrange64 a, u32 shift);

/* Conversion between wrange32 and wrange64 */
struct wrange64 wrange64_from_wrange32_zext(struct wrange32 w32);
struct wrange64 wrange64_from_wrange32_sext(struct wrange32 w32);
struct wrange32 wrange32_from_wrange64(struct wrange64 w64);

static inline bool wrange64_is_empty(struct wrange64 w) {
	/* Empty range is represented as start=1, end=0 (non-wrapping) */
	return w.start == 1 && w.end == 0;
}

static inline bool wrange64_uwrapping(struct wrange64 w) {
	/* Don't treat empty range as wrapping */
	if (wrange64_is_empty(w))
		return false;
	return w.end < w.start;
}

static inline u64 wrange64_umin(struct wrange64 w) {
	if (wrange64_uwrapping(w))
		return U64_MIN;
	else
		return w.start;
}

static inline u64 wrange64_umax(struct wrange64 w) {
	if (wrange64_uwrapping(w))
		return U64_MAX;
	else
		return w.end;
}

static inline bool wrange64_swrapping(struct wrange64 w) {
	return (s64)w.end < (s64)w.start;
}

static inline s64 wrange64_smin(struct wrange64 w) {
	if (wrange64_swrapping(w))
		return S64_MIN;
	else
		return w.start;
}

static inline s64 wrange64_smax(struct wrange64 w) {
	if (wrange64_swrapping(w))
		return S64_MAX;
	else
		return w.end;
}

#endif /* _LINUX_WRANGE_H */
