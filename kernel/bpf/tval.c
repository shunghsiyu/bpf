/* SPDX-License-Identifier: GPL-2.0-only */
/* Copyright (C) 2024 SUSE LLC */
#include <linux/overflow.h>
#include <linux/tnum.h>
#include <linux/tval.h>
#include <linux/limits.h>

static void scalar32_min_max_add(struct tval *dst_val,
				 const struct tval *src_val)
{
	s32 *dst_smin = &dst_val->s32_min;
	s32 *dst_smax = &dst_val->s32_max;
	u32 *dst_umin = &dst_val->u32_min;
	u32 *dst_umax = &dst_val->u32_max;

	if (check_add_overflow(*dst_smin, src_val->s32_min, dst_smin) ||
	    check_add_overflow(*dst_smax, src_val->s32_max, dst_smax)) {
		*dst_smin = S32_MIN;
		*dst_smax = S32_MAX;
	}
	if (check_add_overflow(*dst_umin, src_val->u32_min, dst_umin) ||
	    check_add_overflow(*dst_umax, src_val->u32_max, dst_umax)) {
		*dst_umin = 0;
		*dst_umax = U32_MAX;
	}
}

static void scalar_min_max_add(struct tval *dst_val,
			       const struct tval *src_val)
{
	s64 *dst_smin = &dst_val->smin;
	s64 *dst_smax = &dst_val->smax;
	u64 *dst_umin = &dst_val->umin;
	u64 *dst_umax = &dst_val->umax;

	if (check_add_overflow(*dst_smin, src_val->smin, dst_smin) ||
	    check_add_overflow(*dst_smax, src_val->smax, dst_smax)) {
		*dst_smin = S64_MIN;
		*dst_smax = S64_MAX;
	}
	if (check_add_overflow(*dst_umin, src_val->umin, dst_umin) ||
	    check_add_overflow(*dst_umax, src_val->umax, dst_umax)) {
		*dst_umin = 0;
		*dst_umax = U64_MAX;
	}
}

void tval_add(struct tval *dst_val, const struct tval *src_val)
{
	scalar32_min_max_add(dst_val, src_val);
	scalar_min_max_add(dst_val, src_val);
	dst_val->var_off = tnum_add(dst_val->var_off, src_val->var_off);
}

static void scalar32_min_max_sub(struct tval *dst_val,
				 const struct tval *src_val)
{
	s32 *dst_smin = &dst_val->s32_min;
	s32 *dst_smax = &dst_val->s32_max;
	u32 umin_val = src_val->u32_min;
	u32 umax_val = src_val->u32_max;

	if (check_sub_overflow(*dst_smin, src_val->s32_max, dst_smin) ||
	    check_sub_overflow(*dst_smax, src_val->s32_min, dst_smax)) {
		/* Overflow possible, we know nothing */
		*dst_smin = S32_MIN;
		*dst_smax = S32_MAX;
	}
	if (dst_val->u32_min < umax_val) {
		/* Overflow possible, we know nothing */
		dst_val->u32_min = 0;
		dst_val->u32_max = U32_MAX;
	} else {
		/* Cannot overflow (as long as bounds are consistent) */
		dst_val->u32_min -= umax_val;
		dst_val->u32_max -= umin_val;
	}
}

static void scalar_min_max_sub(struct tval *dst_val,
			       const struct tval *src_val)
{
	s64 *dst_smin = &dst_val->smin;
	s64 *dst_smax = &dst_val->smax;
	u64 umin_val = src_val->umin;
	u64 umax_val = src_val->umax;

	if (check_sub_overflow(*dst_smin, src_val->smax, dst_smin) ||
	    check_sub_overflow(*dst_smax, src_val->smin, dst_smax)) {
		/* Overflow possible, we know nothing */
		*dst_smin = S64_MIN;
		*dst_smax = S64_MAX;
	}
	if (dst_val->umin < umax_val) {
		/* Overflow possible, we know nothing */
		dst_val->umin = 0;
		dst_val->umax = U64_MAX;
	} else {
		/* Cannot overflow (as long as bounds are consistent) */
		dst_val->umin -= umax_val;
		dst_val->umax -= umin_val;
	}
}

void tval_sub(struct tval *dst_val, const struct tval *src_val)
{
	scalar32_min_max_sub(dst_val, src_val);
	scalar_min_max_sub(dst_val, src_val);
	dst_val->var_off = tnum_sub(dst_val->var_off, src_val->var_off);
}
