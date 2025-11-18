// SPDX-License-Identifier: GPL-2.0
/*
 * Minimal user-space test for wrange - no kernel headers
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

/* Copy minimal wrange definitions directly */
struct wrange32 {
    uint32_t start;
    uint32_t end;
};

struct wrange64 {
    uint64_t start;
    uint64_t end;
};

#define WRANGE32(s, e) ((struct wrange32){ .start = (s), .end = (e) })
#define WRANGE64(s, e) ((struct wrange64){ .start = (s), .end = (e) })
#define WRANGE32_FULL WRANGE32(0, 0xFFFFFFFFU)
#define WRANGE64_FULL WRANGE64(0, 0xFFFFFFFFFFFFFFFFULL)
#define WRANGE32_EMPTY WRANGE32(1, 0)
#define WRANGE64_EMPTY WRANGE64(1, 0)

/* Test helper */
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST_ASSERT(cond, msg) do { \
    if (!(cond)) { \
        printf("  FAIL: %s\n", msg); \
        tests_failed++; \
        return; \
    } else { \
        tests_passed++; \
    } \
} while(0)

/* Tests */
static void test_wrange32_basic(void) {
    printf("Test: wrange32 basic construction\n");

    struct wrange32 r = WRANGE32(10, 20);
    TEST_ASSERT(r.start == 10, "start should be 10");
    TEST_ASSERT(r.end == 20, "end should be 20");

    printf("  PASS\n");
}

static void test_wrange64_basic(void) {
    printf("Test: wrange64 basic construction\n");

    struct wrange64 r = WRANGE64(1000, 2000);
    TEST_ASSERT(r.start == 1000, "start should be 1000");
    TEST_ASSERT(r.end == 2000, "end should be 2000");

    printf("  PASS\n");
}

static void test_wrange32_constants(void) {
    printf("Test: wrange32 constants\n");

    struct wrange32 full = WRANGE32_FULL;
    TEST_ASSERT(full.start == 0, "full.start should be 0");
    TEST_ASSERT(full.end == 0xFFFFFFFFU, "full.end should be U32_MAX");

    struct wrange32 empty = WRANGE32_EMPTY;
    TEST_ASSERT(empty.start == 1, "empty.start should be 1");
    TEST_ASSERT(empty.end == 0, "empty.end should be 0");

    printf("  PASS\n");
}

static void test_wrange64_constants(void) {
    printf("Test: wrange64 constants\n");

    struct wrange64 full = WRANGE64_FULL;
    TEST_ASSERT(full.start == 0, "full.start should be 0");
    TEST_ASSERT(full.end == 0xFFFFFFFFFFFFFFFFULL, "full.end should be U64_MAX");

    struct wrange64 empty = WRANGE64_EMPTY;
    TEST_ASSERT(empty.start == 1, "empty.start should be 1");
    TEST_ASSERT(empty.end == 0, "empty.end should be 0");

    printf("  PASS\n");
}

int main(void) {
    printf("Wrange Simple Unit Tests\n");
    printf("=========================\n\n");

    test_wrange32_basic();
    test_wrange64_basic();
    test_wrange32_constants();
    test_wrange64_constants();

    printf("\n=========================\n");
    printf("Results: %d passed, %d failed\n", tests_passed, tests_failed);

    if (tests_failed == 0) {
        printf("✓ All tests PASSED\n");
        return 0;
    } else {
        printf("✗ Some tests FAILED\n");
        return 1;
    }
}
