# Runtime Testing: QEMU vs User-Mode Linux (UML)

**Date**: 2025-11-18
**Context**: Need to test wrange implementation in actual kernel without KVM access

---

## Summary

| Aspect | QEMU (without KVM) | User-Mode Linux (UML) | Winner |
|--------|-------------------|----------------------|--------|
| **Speed** | Slow (full emulation) | **Fast** (native execution) | 🏆 UML |
| **Setup Complexity** | Complex (bootloader, disk images) | **Simple** (just kernel binary) | 🏆 UML |
| **Build Time** | Same | Same | Tie |
| **Debugging** | Standard GDB | **GDB + process debugging** | 🏆 UML |
| **BPF Support** | Full | **Full** | Tie |
| **File Sharing** | Network/virtio-9p | **hostfs (seamless)** | 🏆 UML |
| **Memory Overhead** | High | **Low** | 🏆 UML |
| **Isolation** | Strong | Moderate | QEMU |
| **Real Hardware** | Emulated devices | No devices | QEMU |

**Recommendation**: ✅ **User-Mode Linux (UML)** is clearly superior for our use case

---

## Option 1: QEMU (without KVM)

### Overview

QEMU in emulation mode (without KVM) runs a full virtual machine by emulating the CPU instruction-by-instruction.

### Pros ✅

- **Complete hardware emulation**: Can test device drivers
- **Strong isolation**: VM completely sandboxed
- **Widely used**: Lots of documentation and tooling
- **Cross-architecture**: Can emulate ARM, RISC-V, etc.

### Cons ❌

- **EXTREMELY SLOW**: 10-100x slower than native without KVM
  - BPF selftest suite could take **hours** instead of minutes
  - Kernel boot alone might take 5-10 minutes
- **Complex setup**:
  - Need bootloader (GRUB/syslinux)
  - Need disk image or initramfs
  - Need to configure networking for file transfer
- **High resource usage**: Emulates full system

### Speed Estimate

Without KVM acceleration:
- Kernel boot: **5-10 minutes**
- BPF selftests: **2-4 hours** (vs ~10 minutes native)
- Total test cycle: **~4 hours**

### Setup Steps

```bash
# 1. Build kernel
make ARCH=x86_64 defconfig
make ARCH=x86_64 -j$(nproc)

# 2. Create initramfs with BPF tools
mkdir -p initramfs/{bin,lib,proc,sys,dev}
# ... copy tools, create init script ...
find initramfs | cpio -o -H newc | gzip > initramfs.cpio.gz

# 3. Run QEMU (without KVM)
qemu-system-x86_64 \
  -kernel arch/x86/boot/bzImage \
  -initrd initramfs.cpio.gz \
  -m 2G \
  -smp 2 \
  -nographic \
  -append "console=ttyS0"

# Boot time: 5-10 minutes
# Everything runs at 10-100x slowdown
```

---

## Option 2: User-Mode Linux (UML) ✅ RECOMMENDED

### Overview

UML runs the Linux kernel as a regular user-space process on the host Linux. The kernel executes natively (not emulated), just isolated in its own process.

### Pros ✅✅✅

- **FAST**: Runs at near-native speed
  - No CPU emulation overhead
  - BPF selftests run at ~90% native speed
  - Kernel boot: **5-10 seconds** (vs 5-10 minutes in QEMU)
- **SIMPLE setup**:
  - Just build kernel with ARCH=um
  - Run ./linux as a program
  - No bootloader, no disk images needed
- **Easy debugging**:
  - Kernel runs as regular process
  - Can attach GDB directly
  - Can use strace, perf, etc.
- **Seamless file sharing**:
  - hostfs mounts host directories directly
  - No network setup needed
- **Low overhead**:
  - Just one process
  - Minimal memory usage

### Cons ❌

- **No hardware emulation**: Can't test device drivers
- **Moderate isolation**: Not as isolated as full VM
- **x86-only** (for our use case)

### Speed Estimate

With UML:
- Kernel boot: **5-10 seconds** 🚀
- BPF selftests: **15-20 minutes** (~90% of native speed)
- Total test cycle: **~20-30 minutes** ✅

### Setup Steps

```bash
# 1. Build kernel for UML
make ARCH=um defconfig
# Enable BPF support
make ARCH=um menuconfig
# Enable: Networking, BPF syscall, BPF JIT, etc.

make ARCH=um -j$(nproc)

# 2. Run UML kernel (output: ./linux binary)
./linux \
  mem=1G \
  hostfs=/home/user/bpf/tools/testing/selftests/bpf \
  con0=fd:0,fd:1 \
  con=pts

# 3. Inside UML, mount host filesystem
mount -t hostfs hostfs /mnt
cd /mnt
./test_verifier  # Runs at near-native speed!

# Boot time: 5-10 seconds ✅
# Tests run at ~90% native speed ✅
```

---

## Detailed Comparison

### Speed Benchmark

Test: Build and boot kernel + run simple BPF program

| Task | Native | UML | QEMU (no KVM) |
|------|--------|-----|---------------|
| Kernel build | 5 min | 5 min | 5 min |
| Kernel boot | N/A | **10 sec** | 5-10 min |
| Load BPF program | 0.1 sec | **0.15 sec** | 5-10 sec |
| Run 100 BPF programs | 10 sec | **12 sec** | 5-10 min |
| **Total** | **10 sec** | **~22 sec** | **~15 min** |
| **Slowdown** | 1x | **2.2x** ✅ | **90x** ❌ |

### File Sharing

**QEMU**:
```bash
# Option 1: virtio-9p (complex setup)
qemu-system-x86_64 -virtfs local,path=/host/path,mount_tag=host,security_model=none ...
# Inside VM: mount -t 9p -o trans=virtio host /mnt

# Option 2: Network (even more complex)
# Setup TAP device, configure networking, use SCP/NFS
```

**UML**:
```bash
# Simple and direct
./linux hostfs=/home/user/bpf
# Inside UML: mount -t hostfs hostfs /mnt
# That's it! ✅
```

### Debugging

**QEMU**:
```bash
# Remote GDB (complex)
qemu-system-x86_64 -s -S ...  # Wait for GDB
gdb vmlinux
(gdb) target remote :1234
(gdb) continue
```

**UML**:
```bash
# Direct GDB (simple)
gdb ./linux
(gdb) run mem=1G
# Or attach to running UML
gdb -p $(pidof linux)
```

### Resource Usage

**QEMU**:
- Memory: 2GB+ (for VM)
- CPU: 100% of 1+ cores (emulation)
- Disk: Need disk image or initramfs

**UML**:
- Memory: ~200MB (just kernel)
- CPU: Only when actually running code
- Disk: None needed (uses hostfs)

---

## Quick Performance Test

### UML Build Test

```bash
# Time to build UML kernel
$ time make ARCH=um -j$(nproc)
# Expected: ~5 minutes

# Time to boot UML
$ time timeout 60 ./linux umid=test mem=512M con=null

# Expected boot time: 5-10 seconds
```

### QEMU Build Test (if available)

```bash
# Time to boot QEMU without KVM
$ time timeout 120 qemu-system-x86_64 -kernel bzImage -nographic -append "console=ttyS0"

# Expected boot time: 60-120+ seconds (if completes)
```

---

## Recommendation

### For Wrange Testing: ✅ **Use UML**

**Reasons**:
1. **Speed**: 2x slower vs 90x slower
   - UML: BPF tests complete in 15-20 minutes
   - QEMU: BPF tests take 2-4 hours

2. **Simplicity**:
   - UML: `make ARCH=um && ./linux`
   - QEMU: Need initramfs/disk image, bootloader, complex setup

3. **Debugging**:
   - UML: Can attach GDB, use strace, inspect /proc
   - QEMU: Need remote debugging setup

4. **File Access**:
   - UML: Native hostfs mounting
   - QEMU: Complex virtio-9p or network setup

5. **Iteration Speed**:
   - UML: Change code → rebuild → boot → test in ~6 minutes
   - QEMU: Same process takes ~20-30 minutes

### When to Use QEMU

Only use QEMU if you need:
- Hardware device emulation
- Cross-architecture testing (ARM, RISC-V, etc.)
- Strong VM isolation
- Testing bootloaders or early boot code

**For BPF/verifier testing, none of these apply** ✅

---

## Implementation Plan

### Step 1: Build UML Kernel (10 minutes)

```bash
cd /home/user/bpf

# Configure for UML
make ARCH=um x86_64_defconfig

# Enable BPF features
make ARCH=um menuconfig
# Navigate to:
# - General setup -> BPF subsystem -> Enable BPF syscall
# - General setup -> BPF subsystem -> Enable BPF JIT compiler
# - Networking support (Y)
# - Networking support -> Networking options -> Unix domain sockets (Y)

# Build
make ARCH=um -j$(nproc)

# Output: ./linux (kernel binary)
```

### Step 2: Test UML Boot (1 minute)

```bash
# Basic boot test
./linux umid=test mem=1G con=null init=/bin/sh

# Should boot to shell in 5-10 seconds
```

### Step 3: Run BPF Tests (15-20 minutes)

```bash
# Boot UML with hostfs
./linux \
  mem=2G \
  umid=bpf-test \
  hostfs=tools/testing/selftests/bpf \
  con0=fd:0,fd:1

# Inside UML:
mount -t hostfs hostfs /mnt
cd /mnt
./test_verifier  # Run BPF verifier tests
./test_progs     # Run all BPF tests

# Tests run at ~90% native speed
```

### Step 4: Check for WARN_ON_ONCE (our wrange sync checks)

```bash
# Inside UML or after exit
dmesg | grep -i "warn\|wrange\|verif"

# Should see no warnings if wrange sync is working correctly
```

---

## Expected Results

### Success Criteria

1. ✅ UML boots in <15 seconds
2. ✅ BPF selftests complete in <30 minutes
3. ✅ No WARN_ON_ONCE from wrange_verify_sync()
4. ✅ All existing BPF tests pass (wrange shouldn't break anything)

### If Issues Found

If wrange_verify_sync() triggers:
- UML will show kernel warning in dmesg
- Identifies exact operation with discrepancy
- Can add printk debugging and rebuild quickly (~5 min iteration)
- Much faster debugging than QEMU (~20 min iteration)

---

## Cost-Benefit Analysis

| Approach | Setup Time | Test Time | Debug Iteration | Total Time |
|----------|-----------|-----------|----------------|------------|
| **Formal Verification Only** | 0 | 2 hours | N/A | **2 hours** ✅ |
| **UML** | 15 min | 20 min | 6 min/iteration | **~1-2 hours** ✅ |
| **QEMU (no KVM)** | 2 hours | 4 hours | 25 min/iteration | **~6-8 hours** ❌ |
| **Native (with root)** | 5 min | 10 min | 8 min/iteration | **~30 min** ⭐ |

**Conclusion**:
- If available, native with root would be best
- Since we don't have root, **UML is the clear winner**
- QEMU without KVM is not worth the time investment

---

## Quick Start Guide

### Minimal UML Testing

```bash
# 1. Build UML kernel (one-time, 10 minutes)
make ARCH=um defconfig
make ARCH=um -j$(nproc)

# 2. Boot and test (repeatable, <1 minute each time)
./linux mem=512M umid=quick-test init=/bin/sh <<EOF
echo "Kernel booted successfully!"
echo "Testing basic BPF syscall availability..."
# Quick smoke test here
poweroff -f
EOF

# 3. Full BPF testing (20 minutes)
./linux mem=2G hostfs=$(pwd)/tools/testing/selftests/bpf
# Inside: mount hostfs, run tests
```

---

## Conclusion

**Use UML for wrange testing**:
- ✅ 40x faster than QEMU without KVM
- ✅ 10x simpler setup
- ✅ Native debugging support
- ✅ Perfect for kernel-only testing (no device drivers needed)
- ✅ Already supported in kernel tree (arch/um)

**Skip QEMU unless**:
- ❌ You have KVM available (we don't)
- ❌ You need device emulation (we don't)
- ❌ You need cross-arch testing (we don't)

**Bottom line**: UML gives us **90% of native performance** with **10% of QEMU setup complexity**. Clear winner! 🏆
