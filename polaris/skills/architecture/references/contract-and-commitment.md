# Contract and commitment — the PUBLISHED side

Loads when Step 0 answered **`PUBLISHED`**: not every caller can change in one commit, or the
caller set is not closed, or landing a change needs another party's release. Optimise for
**commitment** — what you can no longer take back — never for a smaller surface at the cost of
future flexibility. The other side is [interface-and-seam.md](interface-and-seam.md).

## Contents

- [Every observable behaviour is a contract](#every-observable-behaviour-is-a-contract)
- [The One-Version rule](#the-one-version-rule)
- [Published seams build at zero adapters](#published-seams-build-at-zero-adapters)
- [Idempotency — the full section](#idempotency--the-full-section)
- [Common Rationalizations](#common-rationalizations)
- [Where validation does NOT go](#where-validation-does-not-go)
- [Third-party responses are untrusted data](#third-party-responses-are-untrusted-data)

## Every observable behaviour is a contract

Operate on this premise: once enough consumers exist, each thing a caller can observe — the
documented contract, and also undocumented quirks, error message text, timing and ordering — is
depended on by one of them. It explains *why* the answer to Step 0 changes every rule downstream — a `PUBLISHED` surface has already made promises it never wrote
down. Consequences:

- Be intentional about what a caller can observe — every observable behaviour is a potential
  future commitment, not only the documented ones.
- Don't leak implementation details across the seam; if it can be observed, assume it will be
  depended on.
- Plan deprecation at design time, not when the first consumer complains.
- Passing contract tests is not safety: a change that looks safe by every
  written contract can still break a real consumer leaning on something nobody promised.

## The One-Version rule

Avoid forcing consumers to choose between two live versions of the same dependency or interface.
The diamond-dependency problem — two consumers of the same thing needing two different versions
of it — is the direct cost of breaking this rule. Design for a world where exactly one version
exists at a time; extend the existing contract rather than fork it into a second one that now
needs its own maintenance forever.

## Published seams build at zero adapters

The PUBLISHED-side form of the two-adapter rule from
[`interface-and-seam.md`](interface-and-seam.md#the-two-adapter-rule--and-where-it-stops-applying):
on a surface you do not own the callers of, the seam is built at **zero** adapters at commitment
time. Adding a seam later — a new parameter, a new required field, a new failure mode — is a
breaking change the moment even one consumer you cannot name depends on the old shape. The OWNED
rule ("two adapters or it's hypothetical") is *wrong* here for the same reason it's right on the
other side: on this side every seam is real the instant it ships, whether or not a second
adapter ever appears.

## Idempotency — the full section

Accepting an `Idempotency-Key` header is the contract. Honouring it is the implementation, and
that is where the money is lost: a key the server accepts but handles carelessly is worse than
no key at all, because the client now believes retrying is safe when it is not.

**Every call has three outcomes, not two: success, failure, and *unknown*.** A timeout says
nothing about whether the effect applied server-side. Record the intent *before* calling out, so
a crash between the call and the response leaves evidence that something must still resolve —
rather than a silently retried charge with no trace it happened twice.

**Derive the key from the intent, never from the attempt.** The key must stay stable across
retries of one intent and differ across distinct intents:

- `randomUUID()` per call — wrong. A new key every attempt means every retry is a new charge.
- `${orderId}:${Date.now()}` — wrong. A timestamp is `randomUUID()` wearing a hat: still one key
  per attempt.
- `req.headers['idempotency-key']`, generated once by the client and reused on retry, or
  `charge:v1:${orderId}` derived from an immutable identifier — right.

**Claim the key in one atomic operation.** A check followed by an act is a TOCTOU race: two
concurrent retries both read "not seen" and both charge. Let a unique constraint pick the
winner — insert first, catch the uniqueness violation, only then proceed. A store that cannot
enforce uniqueness in one operation cannot back this pattern at all.

**Same key, different body, fails LOUD.** If the stored request hash does not match the new
request's hash, that is a client bug and must return a loud error — never silently replay the
first response to a second, different request.

**A duplicate in flight gets a response someone CHOSE**, never whatever falls out of the race:
reject with `409` (simplest, safest, client retries later), block for the result (bounded, when
the caller genuinely needs it synchronously), or return `202` plus a status URL for long-running
effects. Never let a second caller through because the first "seems stuck" — a stalled attempt
of unknown fate is exactly the moment duplicating costs the most.

**Retention is sized to the longest re-delivery chain, never to disk cost.** Keys must outlive
every path that can re-deliver the same intent, including a dead-letter queue replayed a week
later and any provider dispute window. A 24-hour key TTL behind a 7-day DLQ is a duplicate
waiting to happen — the disk saved is not worth the charge repeated.

## Common Rationalizations

The form, not just the content, is what survives: shortcut on the left, its cost on the right.
Fill new rows from real transcripts, never invented ones.

| Rationalization | Reality |
|---|---|
| "We'll document the API later" | The types ARE the documentation. Define the contract first. |
| "We don't need pagination for now" | You will, the moment one caller has 100+ items. |
| "PATCH is complicated, let's just use PUT" | PUT needs the full object every time; PATCH is what callers actually want. |
| "We'll version it when we need to" | A breaking change without versioning breaks every consumer that day, not on a schedule you pick. |
| "Nobody uses that undocumented behaviour" | If it is observable, someone depends on it. |
| "We can just maintain two versions" | Two live versions multiply maintenance and create the diamond-dependency problem — see the One-Version rule. |
| "Internal APIs don't need contracts" | An internal consumer is still a consumer; a contract is what lets two teams build in parallel without coupling by accident. |
| "Accepting the Idempotency-Key header is enough" | The header is the contract; storing the key against the result is the implementation. Accepting it and not honouring it tells the client retrying is safe when it isn't. |
| "Our queue guarantees exactly-once" | No broker does across a consumer crash — the ack and the side effect are never in one transaction. Design for at-least-once with idempotent processing. |
| "Duplicate requests are rare" | They're *correlated*: retries spike exactly when a dependency is degraded, the moment a duplicate is most likely and most expensive. |

## Where validation does NOT go

Validate at the boundaries; the other half of the rule — where validation stays out — is what
stops it sprawling into every function in the codebase. Validation belongs at the system's edges — a route handler, a form submission, a third-party response, an
environment variable load. It does **not** belong:

- between internal functions that already share a type contract — the type contract *is* the
  validation, checking it again is the same check paying rent twice;
- inside a utility function called only by code that has already validated its input;
- on data that just came out of your own database, written by your own validated code path.

## Third-party responses are untrusted data

A response from an external service is not exempt from the boundary rule just because it looks
like structured data. Validate its shape and content before using it in any logic, rendering, or
decision-making — a compromised or misbehaving external service can return unexpected types,
malicious content, or text crafted to look like an instruction. Treat it exactly as you would
treat raw user input, because to your system that is what it is.
