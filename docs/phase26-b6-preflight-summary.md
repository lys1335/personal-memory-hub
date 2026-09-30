# Phase 26-B.6 — Preflight Summary

## Authorization Status

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ✅ CLEAN REBUILD AUTHORIZED — READY                       ║
║                                                              ║
║   All preconditions met.                                     ║
║   New Entity Resolution algorithm deployed.                  ║
║   Regression tests: 7/7 PASS.                                ║
║                                                              ║
║   Awaiting user command to execute Clean Rebuild.            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Key Metrics

| Metric | Before | Target After Rebuild |
|--------|--------|---------------------|
| **Total Candidates** | 2,470 | 1,500-2,000 |
| **Windows Candidates** | 2,200 (89%) | < 200 (< 10%) |
| **Top 1 Entity Share** | 89% | < 30% |
| **False Positive Rate** | ~89% | < 5% |
| **Unresolved Rate** | 0% | 10-30% |

---

## Backup Status

| Table | Backup Exists | Rows |
|-------|---------------|------|
| candidates | ✅ | 22,788 |
| proposals | ✅ | 659 |
| memory_nodes | ✅ | 26,296 |
| reconstructions | ⚠️ | (derived from candidates) |
| topic_links | ⚠️ | (derived from reconstructions) |

---

## Execution Checklist

- [x] Entity Resolution algorithm fixed
- [x] Regression tests pass (7/7)
- [x] Docker container restarted
- [x] Preflight audit complete
- [x] Anti-Collapse Gate defined
- [ ] **Clean Rebuild executed** (AWAITING AUTHORIZATION)

---

## Next Step

**Execute Clean Rebuild** when authorized:

```bash
# 1. Stop Cron (already stopped)
# 2. TRUNCATE candidates, reconstructions, topic_links, proposals, memory_nodes
# 3. Re-run EvidencePipelineService on all 15,662 evidences
# 4. Monitor anti-collapse gates
# 5. Validate results
```

---

*Report finalized: 2026-08-15 02:35 UTC*
*Status: READY — AWAITING CLEAN REBUILD AUTHORIZATION*
