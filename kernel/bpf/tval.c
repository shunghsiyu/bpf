/* SPDX-License-Identifier: GPL-2.0-only */
/* Copyright (C) 2024 SUSE LLC */
#include <linux/overflow.h>
#include <linux/tnum.h>
#include <linux/tval.h>
#include <linux/limits.h>

static void scalar32_min_max_add(struct tval *dst_val,
				 struct tval *src_val)
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

static void scalar_min_max_add(struct tval *dst_tval,
			       struct tval *src_tval)
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

void tval_add(struct tval *dst_val, struct tval *src_val)
{
	scalar32_min_max_add(dst_val, src_val);
	scalar_min_max_add(dst_val, src_val);
	dst_val->var_off = tnum_add(dst_val->var_off, src_val->var_off);
}
