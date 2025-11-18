// SPDX-License-Identifier: GPL-2.0
/*
 * User-space unit tests for wrange operations
 *
 * This tests the actual C implementation without needing kernel access.
 * Compile with: gcc -I../../.. -o test_wrange test_wrange_userspace.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <string.h>

/* Minimal kernel type definitions for user-space */
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int8_t   s8;
typedef int16_t  s16;
typedef int32_t  s32;
typedef int64_t  s64;

#define U64_MAX ((u64)~0ULL)
#define S64_MAX ((s64)(U64_MAX >> 1))
#define S64_MIN ((s64)(-S64_MAX - 1))
#define U32_MAX ((u32)~0U)
#define S32_MAX ((s32)(U32_MAX >> 1))
#define S32_MIN ((s32)(-S32_MAX - 1))
#define U16_MAX ((u16)~0U)

/* Include wrange implementation */
#include "../../../include/linux/wrange.h"

/* Simplified version of wrange.c functions for testing */
/* We'll need to either include the .c file or copy key functions here */

/* Test result tracking */
static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void test_##name(void); \
    static void __attribute__((constructor)) register_##name(void) { \
        printf("Running test: %s\n", #name); \
        tests_run++; \
        test_##name(); \
        tests_passed++; \
    } \
    static void test_##name(void)

#define ASSERT_EQ(a, b) do { \
    if ((a) != (b)) { \
        fprintf(stderr, "  FAIL: %s:%d: %s != %s (%lld != %lld)\n", \
                __FILE__, __LINE__, #a, #b, (long long)(a), (long long)(b)); \
        exit(1); \
    } \
} while(0)

#define ASSERT_TRUE(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "  FAIL: %s:%d: %s is false\n", \
                __FILE__, __LINE__, #cond); \
        exit(1); \
    } \
} while(0)


/* Simple wrange32 tests (we can verify against known outputs) */
TEST(wrange32_basic) {
    struct wrange32 a = WRANGE32(10, 20);
    struct wrange32 b = WRANGE32(5, 15);

    /* Test basic properties */
    ASSERT_EQ(a.start, 10);
    ASSERT_EQ(a.end, 20);

    /* Test length */
    ASSERT_TRUE(wrange32_length(a) == 11);  /* 10..20 inclusive = 11 values */
}

TEST(wrange32_contains) {
    struct wrange32 r = WRANGE32(100, 200);

    ASSERT_TRUE(wrange32_contains(r, 100));
    ASSERT_TRUE(wrange32_contains(r, 150));
    ASSERT_TRUE(wrange32_contains(r, 200));
    ASSERT_TRUE(!wrange32_contains(r, 99));
    ASSERT_TRUE(!wrange32_contains(r, 201));
}

TEST(wrange32_single_value) {
    struct wrange32 r = WRANGE32(42, 42);

    ASSERT_TRUE(wrange32_is_single(r));
    ASSERT_EQ(wrange32_smin(r), 42);
    ASSERT_EQ(wrange32_smax(r), 42);
    ASSERT_EQ(wrange32_umin(r), 42);
    ASSERT_EQ(wrange32_umax(r), 42);
}

TEST(wrange32_full_range) {
    struct wrange32 r = WRANGE32_FULL;

    ASSERT_TRUE(wrange32_is_full(r));
    ASSERT_TRUE(wrange32_contains(r, 0));
    ASSERT_TRUE(wrange32_contains(r, U32_MAX));
    ASSERT_TRUE(wrange32_contains(r, 123456));
}

TEST(wrange32_empty_range) {
    struct wrange32 r = WRANGE32_EMPTY;

    ASSERT_TRUE(wrange32_is_empty(r));
    ASSERT_TRUE(!wrange32_contains(r, 0));
    ASSERT_TRUE(!wrange32_contains(r, 100));
}

TEST(wrange64_basic) {
    struct wrange64 a = WRANGE64(1000, 2000);
    struct wrange64 b = WRANGE64(500, 1500);

    ASSERT_EQ(a.start, 1000);
    ASSERT_EQ(a.end, 2000);
}

TEST(wrange64_contains) {
    struct wrange64 r = WRANGE64(10000, 20000);

    ASSERT_TRUE(wrange64_contains(r, 10000));
    ASSERT_TRUE(wrange64_contains(r, 15000));
    ASSERT_TRUE(wrange64_contains(r, 20000));
    ASSERT_TRUE(!wrange64_contains(r, 9999));
    ASSERT_TRUE(!wrange64_contains(r, 20001));
}

/* Test from_min_max conversion */
TEST(wrange32_from_min_max_positive) {
    /* Positive range: smin=10, smax=20, umin=10, umax=20 */
    struct wrange32 r = wrange32_from_min_max(10, 20, 10, 20);

    ASSERT_EQ(wrange32_smin(r), 10);
    ASSERT_EQ(wrange32_smax(r), 20);
    ASSERT_EQ(wrange32_umin(r), 10);
    ASSERT_EQ(wrange32_umax(r), 20);
}

/* Test to_min_max conversion */
TEST(wrange32_to_min_max_roundtrip) {
    s32 smin, smax;
    u32 umin, umax;

    struct wrange32 r = WRANGE32(100, 200);
    wrange32_to_min_max(r, &smin, &smax, &umin, &umax);

    ASSERT_EQ(smin, 100);
    ASSERT_EQ(smax, 200);
    ASSERT_EQ(umin, 100);
    ASSERT_EQ(umax, 200);
}

TEST(wrange64_from_min_max_positive) {
    struct wrange64 r = wrange64_from_min_max(1000, 2000, 1000, 2000);

    ASSERT_EQ(wrange64_smin(r), 1000);
    ASSERT_EQ(wrange64_smax(r), 2000);
    ASSERT_EQ(wrange64_umin(r), 1000);
    ASSERT_EQ(wrange64_umax(r), 2000);
}

TEST(wrange64_to_min_max_roundtrip) {
    s64 smin, smax;
    u64 umin, umax;

    struct wrange64 r = WRANGE64(10000, 20000);
    wrange64_to_min_max(r, &smin, &smax, &umin, &umax);

    ASSERT_EQ(smin, 10000);
    ASSERT_EQ(smax, 20000);
    ASSERT_EQ(umin, 10000);
    ASSERT_EQ(umax, 20000);
}

/* Main */
int main(int argc, char **argv) {
    printf("wrange User-Space Unit Tests\n");
    printf("=============================\n\n");

    /* Tests run automatically via constructors */

    printf("\n=============================\n");
    printf("Tests passed: %d/%d\n", tests_passed, tests_run);

    if (tests_passed == tests_run) {
        printf("✓ All tests PASSED\n");
        return 0;
    } else {
        printf("✗ Some tests FAILED\n");
        return 1;
    }
}
