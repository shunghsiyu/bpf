# UML Setup Status

**Date**: 2025-11-18
**Goal**: Build and test wrange implementation in User-Mode Linux

---

## Current Status: ⚠️ BLOCKED

**Blocker**: Missing `flex` package (lexical analyzer generator)

### Error Details

```
make ARCH=um olddefconfig

  LEX     scripts/kconfig/lexer.lex.c
/bin/sh: 1: flex: not found
make[2]: *** [scripts/Makefile.host:9: scripts/kconfig/lexer.lex.c] Error 127
make[1]: *** [/home/user/bpf/Makefile:742: olddefconfig] Error 2
```

**Root cause**:
- Kconfig system needs to generate `scripts/kconfig/lexer.lex.c` from `scripts/kconfig/lexer.l`
- This requires `flex` (fast lexical analyzer generator)
- No sudo access to install flex

---

## What We Accomplished ✅

### 1. Created UML-specific BPF Test Config

**File**: `tools/testing/selftests/bpf/config.um`
- Based on `tools/testing/selftests/bpf/config` (main BPF test requirements)
- Added UML-specific options:
  - CONFIG_HOSTFS (host filesystem access)
  - CONFIG_UML_NET_* (UML networking)
  - CONFIG_MCONSOLE (UML management console)
- Includes all BPF requirements:
  - CONFIG_BPF_SYSCALL
  - CONFIG_BPF_JIT
  - CONFIG_DEBUG_INFO_BTF
  - Network scheduling, filtering, tunneling
  - Crypto, netfilter, tracing support

### 2. Merged Configuration

Created `.config` by merging:
- `arch/um/configs/x86_64_defconfig` (UML base)
- `tools/testing/selftests/bpf/config` (BPF core requirements)
- `tools/testing/selftests/bpf/config.um` (UML-specific BPF)

**Result**: 349-line configuration ready for olddefconfig

### 3. Maintained Clean State

- ✅ No improper kernel modifications
- ✅ No manual autoconf.h generation
- ✅ No syncconfig bypassing
- ✅ Following proper kernel build process

---

## Why UML (vs QEMU)?

See `WIP/RUNTIME_TESTING_COMPARISON.md` for full analysis.

**Summary**:
- **UML**: 2x slower than native (5-10 sec boot, 15-20 min tests)
- **QEMU without KVM**: 90x slower (5-10 min boot, 2-4 hour tests)

UML is vastly superior for kernel-only testing when KVM is unavailable.

---

## Resolution Options

### Option 1: Install flex ⭐ RECOMMENDED

```bash
# Requires sudo
sudo apt-get update
sudo apt-get install flex bison

# Then continue
make ARCH=um olddefconfig
make ARCH=um -j$(nproc)
./linux mem=2G
```

**Outcome**: Full UML testing capability in ~30 minutes total

### Option 2: Use Pre-built Kernel

If someone has already built a UML kernel with BPF support:
- Copy the `linux` binary
- Boot directly without building

**Outcome**: Immediate testing, but can't rebuild with changes

### Option 3: QEMU Fallback

Build x86_64 kernel for QEMU emulation:
```bash
make defconfig
cat tools/testing/selftests/bpf/config >> .config
make olddefconfig  # Will also need flex!
make -j$(nproc)
# ... create initramfs, boot in QEMU
```

**Outcome**: ~4 hours for full test cycle vs ~30 min for UML

### Option 4: Native Testing (if root available elsewhere)

Build and test on a system with:
- Root access
- KVM support
- BPF enabled kernel

**Outcome**: Best performance, ~10 minute test cycle

---

## Current .config Status

**File**: `.config` (349 lines)
**State**: Raw merge, needs olddefconfig to resolve dependencies

**Contents**:
- UML x86_64 base configuration
- All BPF syscall, JIT, and events support
- Networking stack (IPv4, IPv6, tunneling)
- Debug symbols and BTF
- Tracing (ftrace, kprobes, dynamic ftrace)
- UML-specific features (hostfs, UML networking)

**Cannot proceed to**: olddefconfig, kernel build
**Reason**: Missing flex package

---

## Testing Plan (Once Unblocked)

### Phase 1: Build (~10 minutes)

```bash
# After installing flex
make ARCH=um olddefconfig
make ARCH=um -j$(nproc)
# Output: ./linux (UML kernel binary)
```

### Phase 2: Boot Test (~1 minute)

```bash
# Quick boot test
./linux umid=test mem=1G con=null init=/bin/sh
# Should boot to shell in 5-10 seconds
```

### Phase 3: BPF Testing (~20 minutes)

```bash
# Boot with hostfs for test access
./linux \
  mem=2G \
  umid=bpf-test \
  hostfs=$(pwd)/tools/testing/selftests/bpf

# Inside UML:
mount -t hostfs hostfs /mnt
cd /mnt
./test_verifier     # Run verifier tests
./test_progs        # Run all BPF tests

# Check for wrange warnings
dmesg | grep -i "warn\|wrange"
```

### Phase 4: Verification

**Success criteria**:
1. ✅ All existing BPF tests pass (wrange doesn't break anything)
2. ✅ No WARN_ON_ONCE from wrange_verify_sync()
3. ✅ Test runtime ~20 minutes (near-native speed)

**If issues found**:
- UML shows kernel warnings in dmesg
- Identifies exact operation with discrepancy
- Quick rebuild cycle (~6 min) for debugging

---

## Comparison: Current State vs Goals

| Task | Status | Notes |
|------|--------|-------|
| **Config creation** | ✅ Complete | Proper .config with BPF + UML |
| **Config resolution** | ⚠️ Blocked | Need flex for olddefconfig |
| **Kernel build** | ⏸️ Pending | Blocked by config |
| **UML boot** | ⏸️ Pending | Blocked by build |
| **BPF testing** | ⏸️ Pending | Blocked by boot |

**Blocker**: Single package dependency (flex)
**Impact**: Cannot proceed with any build/test steps
**Workaround**: Install flex OR use QEMU OR test elsewhere

---

## Files Created

1. **tools/testing/selftests/bpf/config.um** - UML-specific BPF test config
2. **.config** - Merged UML + BPF configuration (pending olddefconfig)
3. **WIP/RUNTIME_TESTING_COMPARISON.md** - UML vs QEMU analysis
4. **WIP/UML_SETUP_STATUS.md** - This file

---

## Recommendation

**If flex can be installed** → Continue with UML (best option)
- Fast: ~30 min total time
- Simple: `make ARCH=um && ./linux`
- Effective: Near-native performance

**If flex cannot be installed** → Document and defer
- Current testing (formal verification + unit tests) provides HIGH confidence
- Runtime testing can be done:
  - By reviewers with proper setup
  - In CI/CD environment
  - After code review/merge

**Do NOT** → Try to bypass flex/syncconfig
- Violates kernel build principles
- Creates maintenance burden
- Risk of incorrect configuration

---

## Summary

We have:
- ✅ Comprehensive formal verification (28/28 tests passing)
- ✅ User-space unit tests (12/12 passing)
- ✅ Static analysis (18/18 operations verified)
- ✅ Proper UML configuration ready
- ⚠️ Missing one package (flex) to proceed

**Next step**: User decision on how to resolve flex dependency
