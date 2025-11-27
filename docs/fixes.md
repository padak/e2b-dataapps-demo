# App Builder - Bug Analysis and Fixes

**Date:** 2024-11-27
**Status:** Deep analysis complete, pending review
**Analysts:** Main agent + 3 explore sub-agents

---

## Executive Summary

App Builder running in local mode (`SANDBOX_MODE=local`) has multiple bugs ranging from critical to low severity. The deep analysis revealed **27 distinct issues** across the backend codebase.

**Critical Issues:** 6
**High Severity:** 7
**Medium Severity:** 10
**Low Severity:** 4

---

## Original User-Reported Problems

### Problem 1: Messages Stick Together in Chat

**Symptoms:**
- Multiple assistant responses appear merged into one message bubble
- Text flows together without proper separation

### Problem 2: Dev Server Starts on Port 3000

**Symptoms:**
- Agent starts Next.js dev server on port 3000
- Port 3000 is already used by frontend (Vite dev server)
- Preview URL points to wrong application

---

## Root Cause Analysis

### Problem 1: Messages Stick Together

#### Primary Cause: React StrictMode Double-Mounting

In `frontend/src/main.tsx:9`:
```jsx
<React.StrictMode>
```

React 18 StrictMode intentionally runs effects twice in development:

1. **First mount:** Creates session, WebSocket, calls `setWsClient(client)`
2. **Cleanup triggered:** `wsClient` is still `null` (async), so disconnect never happens
3. **Second mount:** Creates ANOTHER session and WebSocket

**Evidence:**
```
23:25:54,452 - Created new session: cb72b3c2...
23:25:54,453 - Created new session: 14cc6de9...
```

#### Contributing Factor: Race Condition in chat_received

**File:** `backend/app/websocket.py:126-134`

```python
await self.send_message(session_id, {"type": "chat_received", ...})
async for event in agent.chat(user_message):
    await self.send_message(session_id, event)
```

`chat_received` may arrive AFTER first `text` event because `send_message()` returns when message is queued, not delivered.

### Problem 2: Port 3000

#### Primary Cause: Tool Description Specifies Port 3000

In `backend/app/tools/sandbox_tools.py:354`:
```python
port: Port to run on (default: 3000)
```

Claude reads this and uses 3000. The `LocalSandboxManager` uses the agent's requested port instead of enforcing allocated port.

---

## Deep Analysis Findings

### CRITICAL Issues

#### C1. Memory Leak: Unclosed Background Processes
**File:** `local_sandbox_manager.py:249-257`
**Problem:** Background `Popen` processes are created but never stored or cleaned up. Creates zombie processes.
**Fix:** Track all background processes in a list, terminate in `destroy()`.

#### C2. Race Condition: ConnectionManager Without Locking
**File:** `websocket.py:15-16`
**Problem:** `active_connections` and `agents` dicts accessed concurrently without locks. Can cause KeyError or lost connections.
**Fix:** Add `asyncio.Lock()` for all dictionary operations.

#### C3. Error Loop Doesn't Break on Exception
**File:** `main.py:183-194`
**Problem:** After exception in message handling, loop continues instead of breaking. Causes resource waste.
**Fix:** Always break after error, even if error message sends successfully.

#### C4. Global Sandbox Manager Singleton - Session Isolation Failure
**File:** `tools/sandbox_tools.py:17,21-24`
**Problem:** `_sandbox_manager` is global. Multiple sessions overwrite each other's manager. Only last session works correctly!
**Fix:** Use `contextvars.ContextVar` for session-local storage.

#### C5. Race Condition: chat_received vs text Events
**File:** `websocket.py:126-134`
**Problem:** No guarantee `chat_received` arrives before first `text` event.
**Fix:** Add small delay after ack, or combine ack with first content.

#### C6. Port Allocation Race Condition
**File:** `local_sandbox_manager.py:79-91`
**Problem:** TOCTOU race - port checked as available, but another process could claim it before use.
**Fix:** Either hold socket open until use, or retry on port-in-use error.

### HIGH Severity Issues

#### H1. No Timeout for Agent Responses
**File:** `websocket.py:132-134`
**Problem:** No timeout mechanism. Stuck agent hangs connection indefinitely.
**Fix:** Wrap streaming in `asyncio.timeout(300)`.

#### H2. Concurrent Reset During Streaming
**File:** `websocket.py:142-149`
**Problem:** Reset can destroy agent while chat is streaming.
**Fix:** Add `_chat_in_progress` flag, reject reset during streaming.

#### H3. Agent Init Failure Not Communicated
**File:** `websocket.py:27-48`
**Problem:** WebSocket accepted before agent init. If init fails, client gets no error message.
**Fix:** Initialize agent BEFORE accepting WebSocket.

#### H4. Dev Server Process Not Properly Managed
**File:** `local_sandbox_manager.py:356-364`
**Problem:** Multiple `start_dev_server()` calls orphan previous process.
**Fix:** Check and kill existing process before starting new one.

#### H5. No Dev Server Health Check
**File:** `local_sandbox_manager.py:366-368`
**Problem:** Fixed 5s sleep, no actual health check. Server might not be ready.
**Fix:** Implement HTTP health probe with timeout.

#### H6. Missing Disconnect Cleanup Locking
**File:** `websocket.py:88-91`
**Problem:** Disconnect called without waiting for completion. Race with other operations.
**Fix:** Use lock to ensure atomic cleanup.

#### H7. Path Traversal Vulnerability
**File:** `local_sandbox_manager.py:93-140`
**Problem:** `_resolve_path()` doesn't validate final path is within sandbox.
**Fix:** After resolution, verify `final_path.startswith(sandbox_root)`.

### MEDIUM Severity Issues

#### M1. No Message Ordering Guarantee
**File:** `websocket.py:73-91`
**Problem:** Concurrent `send_message()` calls may deliver out of order.
**Fix:** Add per-session send lock.

#### M2. Agent State Not Reset After Error
**File:** `websocket.py:116-134`
**Problem:** Exception during streaming leaves agent in bad state.
**Fix:** Reset state flags (`_sandbox_notified`, etc.) on error.

#### M3. No Backpressure for Fast Events
**File:** `websocket.py:133-134`
**Problem:** Fast event generation can overflow WebSocket buffer.
**Fix:** Implement backpressure or rate limiting.

#### M4. Missing Input Validation in Tools
**File:** `tools/sandbox_tools.py:40,84,194`
**Problem:** File paths and ports not validated. Could allow path traversal.
**Fix:** Validate all inputs before use.

#### M5. Timeout Inconsistency Between E2B and Local
**File:** `local_sandbox_manager.py` vs `sandbox_manager.py`
**Problem:** Different timeout handling (0 means different things).
**Fix:** Normalize timeout handling in both implementations.

#### M6. Shell Injection Risk
**File:** `local_sandbox_manager.py:353`
**Problem:** `project_dir` not escaped in shell command.
**Fix:** Use `shlex.quote()` for all user-influenced values.

#### M7. Destroy Error Swallowed
**File:** `agent.py:494`
**Problem:** Exception in cleanup is logged but swallowed.
**Fix:** Re-raise or log as critical.

#### M8. Missing Bounds Check on Port
**File:** `tools/sandbox_tools.py:244`
**Problem:** Port not validated (could be negative or >65535).
**Fix:** Validate `1 <= port <= 65535`.

#### M9. Process Group Not Used
**File:** `local_sandbox_manager.py:249-257`
**Problem:** Background processes not in process group. Children become orphans.
**Fix:** Use `start_new_session=True`.

#### M10. Incomplete Reset Error Recovery
**File:** `websocket.py:143-149`
**Problem:** If `agent.initialize()` fails after cleanup, agent is broken.
**Fix:** Add error handling around reset.

### LOW Severity Issues

#### L1. Logging Configuration Duplicated
**File:** Multiple files
**Problem:** `basicConfig()` called in multiple modules.
**Fix:** Configure once in `main.py`.

#### L2. Hardcoded /tmp Path
**File:** `local_sandbox_manager.py:150`
**Problem:** Won't work on Windows.
**Fix:** Use `tempfile.gettempdir()`.

#### L3. Missing Shutdown Timeout
**File:** `main.py:44-52`
**Problem:** Cleanup can hang indefinitely.
**Fix:** Add timeout to cleanup.

#### L4. Inconsistent Error Response Format
**File:** `tools/sandbox_tools.py`
**Problem:** Error responses use different formats.
**Fix:** Standardize error response structure.

---

## Recommended Solutions

### For Problem 1 (Messages Sticking)

**Option B: Ref-based cleanup pattern (RECOMMENDED)**

```javascript
useEffect(() => {
  const wsClientRef = { current: null };
  let mounted = true;

  const initSession = async () => {
    if (!mounted) return;
    const response = await fetch('/api/session', { method: 'POST' });
    const data = await response.json();
    if (!mounted) return;

    const client = new WebSocketClient(data.session_id);
    wsClientRef.current = client;
    await client.connect();

    if (!mounted) {
      client.disconnect();
      return;
    }
    setWsClient(client);
  };

  initSession();

  return () => {
    mounted = false;
    wsClientRef.current?.disconnect();
  };
}, []);
```

**Why this solution:**
- Maintains StrictMode benefits
- Properly handles async cleanup race conditions
- Follows React best practices

### For Problem 2 (Port 3000)

**Option A: Ignore port parameter in local mode (RECOMMENDED)**

```python
async def start_dev_server(self, project_dir: str = ".", port: Optional[int] = None):
    # In local mode, always use allocated port
    server_port = self._allocated_port
    if not server_port:
        server_port = self._find_available_port(start_port=3001)
        self._allocated_port = server_port

    if port and port != server_port:
        logger.info(f"Ignoring requested port {port}, using allocated port {server_port}")
```

**Why this solution:**
- Guarantees no port conflicts in local dev
- Simple and deterministic
- Agent doesn't need to know about port management

### For Critical Issue C4 (Global Sandbox Manager)

**Use contextvars for session isolation:**

```python
from contextvars import ContextVar

_sandbox_manager: ContextVar = ContextVar('sandbox_manager', default=None)

def set_sandbox_manager(manager):
    _sandbox_manager.set(manager)

def get_manager():
    manager = _sandbox_manager.get()
    if manager is None:
        raise RuntimeError("Sandbox manager not initialized")
    return manager
```

---

## Implementation Priority

### Phase 1: Immediate (Blocks Testing)
1. [ ] Fix port allocation (Problem 2) - `local_sandbox_manager.py`
2. [ ] Fix WebSocket cleanup (Problem 1) - `AppBuilder.tsx`
3. [ ] Fix global sandbox manager (C4) - `sandbox_tools.py`

### Phase 2: High Priority (Stability)
4. [ ] Add ConnectionManager locking (C2)
5. [ ] Fix error loop (C3)
6. [ ] Add agent response timeout (H1)
7. [ ] Fix agent init order (H3)

### Phase 3: Medium Priority (Robustness)
8. [ ] Track background processes (C1)
9. [ ] Add message ordering lock (M1)
10. [ ] Add input validation (M4)
11. [ ] Fix path traversal (H7)

### Phase 4: Low Priority (Polish)
12. [ ] Consolidate logging (L1)
13. [ ] Cross-platform paths (L2)
14. [ ] Standardize error formats (L4)

---

## Testing Checklist

After implementing fixes:

- [ ] Create new app - messages appear as separate bubbles
- [ ] Dev server starts on port 3001+
- [ ] Preview URL is correct (`http://localhost:3001`)
- [ ] Multiple sessions don't interfere
- [ ] Page refresh creates clean new session
- [ ] Long-running operations have proper timeout
- [ ] Reset during streaming shows proper error
- [ ] Path traversal attempts are blocked

---

## Appendix: Issue Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| C1 | CRITICAL | local_sandbox_manager.py | Unclosed background processes |
| C2 | CRITICAL | websocket.py | ConnectionManager race condition |
| C3 | CRITICAL | main.py | Error loop doesn't break |
| C4 | CRITICAL | sandbox_tools.py | Global sandbox manager |
| C5 | CRITICAL | websocket.py | chat_received race condition |
| C6 | CRITICAL | local_sandbox_manager.py | Port allocation race |
| H1 | HIGH | websocket.py | No agent timeout |
| H2 | HIGH | websocket.py | Reset during streaming |
| H3 | HIGH | websocket.py | Agent init after accept |
| H4 | HIGH | local_sandbox_manager.py | Dev server process leak |
| H5 | HIGH | local_sandbox_manager.py | No health check |
| H6 | HIGH | websocket.py | Disconnect race |
| H7 | HIGH | local_sandbox_manager.py | Path traversal |
| M1-M10 | MEDIUM | Various | See detailed list above |
| L1-L4 | LOW | Various | See detailed list above |

---

## Codex Second Opinion (OpenAI GPT-5.1)

**Model:** gpt-5.1-codex-max
**Confidence Level:** Medium

### Overall Assessment

> "Generally solid, but several root causes/solutions are speculative, some severities are overstated, and a few important gaps/duplicated issues exist. Needs evidence and scope tightening."

### Agreement Points

Codex agrees with:
- StrictMode double-mount contributing to duplicate sessions is plausible in dev
- Port hint of 3000 in tool description likely nudges LLM to choose wrong port
- Global sandbox manager singleton can break session isolation
- Lack of health checks/timeout for dev server is a real risk
- Missing input/path validation and port bounds checks are legitimate issues

### Disagreement Points

Codex challenges:
1. **Message merging root cause** - Primary cause may be UI rendering/state handling, not necessarily double WebSocket sessions. Evidence is thin without confirming duplicate client instances in React tree.
2. **chat_received ordering (C5)** - Labeled critical but likely medium/low. WebSockets often arrive out of order; clients should handle it.
3. **ConnectionManager locking (C2)** - In single-threaded asyncio context, dict access is not inherently racy. Critical severity overstated unless multithreading involved.
4. **Port TOCTOU race (C6)** - Minor unless ports highly contended. Severity inflated.
5. **Reset during streaming (H2)** - May be acceptable if API contract allows cancellation. Needs spec, not default high severity.
6. **Path traversal duplication** - H7 and M4 flag same class of issue. Should consolidate.

### Missed Issues (Codex Found)

1. No confirmation of frontend rendering logic for message grouping (message id/key handling)
2. No mention of WebSocket reconnect cleanup on navigation outside StrictMode
3. LLM port choice could stem from prompt/tool instructions, not just docstring
4. Dev server missing stdout/stderr capture and failure reporting to user
5. No evidence tying backpressure to resource exhaustion thresholds
6. Testing gaps: no plan to verify StrictMode issue in production build

### Priority Reassessment Suggestions

1. **Deprioritize C2/C6** to medium unless proven concurrent issues exist
2. **Elevate server-side port override** to top priority - deterministic fix regardless of LLM behavior
3. **Verify message rendering first** before StrictMode workaround - confirm actual cause
4. **Merge path validation issues** (H7 + M4) into single task

### Alternative Solutions Proposed

1. **For message sticking:** First assert single WebSocket/client instance and inspect message grouping logic. Use stable message IDs and render per-id to avoid merges.
2. **For port conflicts:** Enforce backend port override and ignore model-chosen ports. Also adjust tool metadata to not suggest 3000.
3. **For session isolation:** Prefer dependency injection over ContextVar if request-scoped lifecycle exists.
4. **For event ordering:** Use bounded queues or `asyncio.StreamWriter.drain`-based flow control instead of ad-hoc delays.

---

## Synthesis: Claude + Codex Consensus

### High Confidence Fixes (Both Agree)
1. **Port 3000 conflict** - Backend must enforce allocated port, ignore LLM preference
2. **Global sandbox manager** - Must fix session isolation
3. **Dev server health check** - Need proper startup validation
4. **Input validation** - Path and port validation needed

### Needs More Investigation
1. **Message sticking** - Before implementing StrictMode fix, verify:
   - Are there actually duplicate WebSocket connections?
   - Is message ID/key handling correct in React?
   - Is message grouping logic merging same-author messages?

### Severity Adjustments
| Issue | Original | Adjusted | Reason |
|-------|----------|----------|--------|
| C2 | CRITICAL | MEDIUM | Single-threaded asyncio, no proven race |
| C5 | CRITICAL | MEDIUM | Client should handle message ordering |
| C6 | CRITICAL | MEDIUM | Low port contention in dev |
| H7+M4 | HIGH+MEDIUM | HIGH (merged) | Same issue, consolidate |

### Revised Implementation Priority

#### Phase 1: Immediate (Deterministic Fixes)
1. [ ] **Backend port override** - Ignore LLM port, use 3001+
2. [ ] **Fix global sandbox manager** - Session isolation critical
3. [ ] **Investigate message rendering** - Verify actual root cause

#### Phase 2: After Investigation
4. [ ] **StrictMode/WebSocket cleanup** - Only if verified as cause
5. [ ] **Add response timeout** - H1 agreed by both
6. [ ] **Path validation** - Consolidated H7+M4

#### Phase 3: Robustness
7. [ ] Track background processes (C1)
8. [ ] Dev server health check (H5)
9. [ ] Error loop fix (C3)
