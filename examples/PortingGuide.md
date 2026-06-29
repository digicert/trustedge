## TrustEdge New OS Porting Guide (High-Level)

### 1) Add OS support in core dependencies (platform first)

1. **Create a new platform target**
   - Add a new OS macro (example: `__RTOS_NEWOS__`) in common compile definitions.
   - Mirror existing patterns from Linux/Windows/Zephyr ports.

2. **Implement platform abstraction layers**
   - In platform and related common wrappers, add/verify support for:
     - file I/O and path APIs
     - sockets/network APIs
     - threads, mutexes, sleep/timers
     - signals/process control (or no-op equivalents if unsupported)
     - entropy/random source
     - clock/time functions

3. **Map missing OS primitives**
   - If your OS lacks POSIX features, implement compatibility shims in platform files instead of changing business logic.

---

### 2) Enable TrustEdge-specific OS behavior

1. **Update OS-conditional logic in TrustEdge**
   - Review `src/trustedge/*` for `#ifdef __RTOS_LINUX__`, `__RTOS_WIN32__`, `__RTOS_ZEPHYR__`.
   - Add `__RTOS_NEWOS__` branches where needed (daemon/service mode, PID handling, signal shutdown, thread start/join, socket lifecycle).

2. **Service/daemon model**
   - Decide whether the new OS supports:
     - daemon/service mode
     - PID files
     - signal-based termination
   - If not supported, add safe fallbacks and explicit logs.

3. **TrustEdge agent/certificate flows**
   - Verify startup/shutdown paths in:
     - trustedge_main.c
     - agent REST/server paths
     - certificate enrollment paths
   - Ensure cleanup works even on early failures.

---

### 3) Update CMake build system

1. **Add OS option/toolchain integration**
   - Add a platform switch/option for `NEWOS`.
   - Add toolchain config (compiler, sysroot, flags).

2. **Add platform source selection**
   - Include new platform files in target source lists.
   - Add required compile definitions (for example `__RTOS_NEWOS__`).

3. **Link OS-specific libraries**
   - Add thread/network/system libs required by the new OS.
   - Keep Linux/Windows/Zephyr link logic unchanged.

4. **Build profiles**
   - Validate both library and executable modes (if used in your setup).

---

### 4) Validate with a minimum bring-up checklist

- Build succeeds with `NEWOS` profile.
- `trustedge --help` and `--version` run.
- Agent mode starts and exits cleanly.
- Certificate mode executes basic flow.
- REST API path (if enabled) accepts and responds.
- Thread/socket/file cleanup has no leaks or hangs.

---

### Security notes (important)

- Keep PID/service file handling hardened (avoid symlink-following, validate permissions).
- Ensure new OS wrappers do not weaken TLS, key storage, or randomness quality.
- Validate all external inputs on REST/CLI boundaries.

Also remember to sanitize user inputs and avoid hardcoded secrets.
