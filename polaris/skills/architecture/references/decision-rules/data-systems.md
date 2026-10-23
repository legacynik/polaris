# Data-systems rules

These rules settle data-systems forks: the data model, the storage engine, replication, partitioning,
encoding, transactions, consistency, consensus, batch and stream processing, and the correctness of
derived data. Each rule reads condition → decision → why → check, and every guarantee is paired with
what it costs, because none comes free. A step loads only the rule ids it names, never the whole file.

## Where these rules stop

| Question | Who decides it instead |
|---|---|
| How to decompose services, where module boundaries fall, what granularity to pick | the decomposition rules |
| How architectural decisions stay governed over time and become mechanically checkable | the governance rules |
| Who owns which system and how teams form around the boundaries | the ownership rules |
| Hiring, evaluating, motivating or coaching the people doing the work | people and roles — outside this skill |
| Whether to build it at all, whether the product bet is right | strategy — outside this skill |
| Byzantine fault tolerance, blockchain and distributed-ledger design | a specialist in that field — outside this skill |
| Hard real-time systems (airbags, flight control, robotics) | real-time systems engineering — outside this skill |
| Encryption, key management, authentication, access control | a security review — outside this skill; encoding is a separate concern from encryption |
| Information retrieval, ranking, NLP, machine-learning model design | the specialist discipline — outside this skill |
| A checkable gate for data residency or regulatory placement | nobody yet: write that check as its own gate. These rules give only the vocabulary (partitioning by jurisdiction, true deletion versus tombstone, `data-collection-minimization`) |

## Conditions that change a rule's footing

**Scale.** Several rules presume a system larger than one machine. Below that size they are cost with no
benefit.
- Distribution itself: if everything fits on one machine, keep it there. Of the three reasons to
  distribute (load, fault tolerance, geographic latency), only the last two are out of reach on one
  node.
- `partitioning-scheme`, `hot-key-handling`, `rebalancing-strategy`, `rebalancing-automation`,
  `secondary-index-placement` presume a dataset or query load beyond one machine.
- A separate data warehouse presumes a large organisation; a small company's data usually fits a
  conventional SQL database, sometimes a spreadsheet.
- `graph-processing-scale`: below the single-machine threshold a single-threaded algorithm wins
  outright.
- `materialize-or-pipeline`: the write-every-stage-to-disk fault-tolerance design was tuned for clusters
  where about 5% of tasks are preempted each hour; where tasks are rarely killed it loses its reason.
- `unbundle-or-integrate`: one product that meets every requirement beats a composition.
- Early-stage or unproven products: fast iteration on features outranks scaling for a load that may
  never arrive.

**Instrumentation.** These rules take a measurement as input. Getting the measurement is the first task;
the fallback holds until it exists.
- `lsm-or-btree` and every storage-engine choice: your own read/write mix and p99 target. Fallback: the
  conservative option (B-tree), revisited once measured.
- `timeout-and-clock-discipline`: round-trip distribution over a long period, across many machines.
  Fallback: an adaptive failure detector instead of a constant.
- `hash-index-or-lsm`: the count of distinct keys, not of writes. Fallback: no hash index.
- `hot-key-handling`, `batch-hot-key`: key-frequency distribution from a sampling pass. Fallback:
  declare hot keys by hand, or accept the stall.
- `staleness-as-a-metric`: a staleness signal (replication lag, or a proxy for it). Fallback: none — no
  honest promise of eventual consistency downstream.
- `lsm-compaction-monitoring`: compaction backlog. Fallback: no LSM under high sustained writes.
- `isolation-level-selection`: an inventory of read-decide-write paths. Fallback: serializable, paid
  for.
- `write-path-read-path-boundary`: today's read-path cost. Fallback: none — a cache cannot be judged.
- `audit-your-derived-data`: a re-derivation to compare against. Fallback: none — no corruption signal.
- Any latency target: client-side p50/p95/p99/p999. Server-side figures and means both look better than
  what users get; without client percentiles every latency claim is unverified.

## Rules that yield a number or a closure predicate

- `audit-your-derived-data` — number: mismatched re-derivations / re-derivations run; auditing nothing
  leaves the ratio undefined, never perfect. Closure: a derived dataset is done when re-deriving it from
  its source reproduces it.
- `staleness-as-a-metric` with `lag-guarantee-selection` — number: observed violations / guarantees
  declared per store. The denominator counts declared guarantees, so declaring none earns nothing.
- `loose-constraint-or-linearizable` — number: compensations issued / constraints deliberately checked
  after the write. Pair it with an availability measure; optimising it alone drives over-coordination.
- `end-to-end-operation-id` — closure: a write path is done when a client-generated operation id reaches
  every hop and a test that submits one operation twice finds exactly one row.
- `log-compaction-for-bootstrap` — closure: a derived store is done when it rebuilds from offset 0 of
  the compacted topic into a scratch namespace, diffs clean, and the source database is never read.

---

## data model

### relationship-shape
- **condition:** choosing or revisiting an application's primary data model, or refactoring a schema.
- **decision:** pick by relationship shape. A self-contained tree read whole (one-to-many, locality
  wins) → document. Many-to-many relationships that matter → relational. Densely connected data walked
  to variable, unpredictable depth → graph; for such data graph fits best, relational is acceptable,
  document is awkward.
- **why:** each model buys the access its shape needs: trees get locality, many-to-many gets joins,
  graphs get traversal. Document moves joins into application code and forces denormalisation the app
  must keep consistent as many-to-many grows; relational charges join and impedance cost on tree reads;
  graph adds a second query language and an operational learning curve.
- **check:** state today's shape and its direction — features tend to add connections, so a join-free
  document fit at v1 is a snapshot. Halt if the debate runs on syntax, ORM comfort or vendor preference
  instead of shape. Relational stores now carry JSON types and document stores gain joins; the edges
  soften, the fork stands.

## storage engine

### hash-index-or-lsm
- **condition:** choosing a key-value engine for a key set you can characterise.
- **decision:** many writes per key over a small key set that fits in RAM, and no range scans ever → a
  Bitcask-style hash index over an append-only log. Every other shape → B-tree or LSM.
- **why:** buys one-seek reads and the cheapest writes. Costs: every key must live in memory (on-disk
  hash maps need heavy random I/O, grow expensively and complicate collisions), and range queries become
  impossible rather than slow.
- **check:** count distinct keys, not writes; the working set depends on distinct keys alone. Halt if
  that count cannot be bounded or any requirement mentions a range query — both make this a one-way
  door.

### lsm-or-btree
- **condition:** picking between a log-structured (LSM) engine and an update-in-place (B-tree) engine.
- **decision:** write throughput is the bottleneck → LSM. Predictable latency or transaction isolation
  is the bottleneck → B-tree. Treat this as a hypothesis and test it on your own workload before
  committing.
- **why:** LSM gains sustained write throughput (sequential writes, better compression, no page
  fragmentation, and often lower write amplification) and pays with spiky high percentiles when
  compaction fights for disk, plus several copies of a key across segments. B-tree gains steady latency
  and one copy per key, which lets range locks sit on the tree itself; it pays write amplification from
  WAL, page writes, splits and whole-page granularity.
- **check:** know whether write throughput or p99 read latency binds; without that you are guessing.
  Halt when the choice rests on a vendor benchmark — such results swing with workload details.

### lsm-compaction-monitoring
- **condition:** an LSM engine under high write throughput.
- **decision:** instrument compaction backlog and alert on it before go-live; treat it as an operating
  signal, not an engine internal.
- **why:** buys early warning for the price of an alert someone owns. LSM engines keep accepting writes
  when compaction falls behind, so unmerged segments pile up until the disk fills and reads slow as they
  probe more files — the failure stays silent until it is total.
- **check:** unconditional for LSM at load. If it cannot be instrumented, the design has accepted
  unbounded disk growth; record that or pick another engine.

### row-or-column
- **condition:** a wide table whose queries touch few columns.
- **decision:** a typical query reads 4–5 of 100+ columns across many rows → column-oriented. Queries
  fetch whole records by key → row-oriented.
- **why:** column storage reads only the needed column files and enables bitmap and run-length
  compression plus vectorised execution over cache-sized chunks. It gives up in-place updates on sorted,
  compressed columns: writes gather in an LSM-style memtable and merge in bulk. All columns share one
  row order; sorting columns independently destroys the positional match that rebuilds a row.
- **check:** the query pattern is stable enough to fix one sort order, and writes come in bulk loads,
  not scattered single-row updates. If both patterns must be served by one store at production latency,
  you need two engines — say so. Columnar formats (Parquet, Arrow, lakehouse tables) confirm the
  direction.

### in-memory-database
- **condition:** the active dataset fits in RAM and an in-memory store is proposed for speed.
- **decision:** choose it for the data models it makes possible (priority queues, sets) and for skipping
  the encode-to-disk-layout step. Avoiding disk reads is not a valid reason.
- **why:** buys freedom from encoding in-memory structures into a disk format, and structures that are
  awkward on disk. Costs: a disk engine with ample RAM seldom touches disk anyway because the OS caches
  blocks, so the gain is smaller than expected; and a restart must reload state from disk or a replica.
- **check:** a durability story exists first — battery-backed RAM, a disk log, periodic snapshots, or
  replication. Halt if the case rests on avoiding disk reads; that premise misleads the rest of the
  design.

### index-count
- **condition:** someone proposes a new index.
- **decision:** every index names the query pattern that needs it; no pattern, no index. Databases leave
  indexing off by default because only the application knows its patterns.
- **why:** an index speeds reads and slows every write, permanently.
- **check:** the query pattern exists today, not in anticipation. Reject an index justified as perhaps
  useful later — a write tax forever for a read that may never come.

### secondary-index-placement
- **condition:** a partitioned dataset needs a secondary index.
- **decision:** writes dominate, or reads tolerate scatter/gather → local (document-partitioned) index.
  Reads dominate and tolerate staleness → global (term-partitioned) index.
- **why:** local keeps each write on one partition but sends reads to all of them, where the slowest
  sets the response time — tail latency amplification, worse as partitions grow. Global keeps reads on
  one partition but spreads writes over several, which in practice must be asynchronous (DynamoDB
  usually propagates in under a second, longer under faults).
- **check:** measure or bound scatter/gather fan-out at the current and projected partition count.
  Escalate if the global index must be synchronously consistent with base data — that needs a
  distributed transaction across index partitions.

---

## replication

### replication-architecture
- **condition:** choosing single-leader, multi-leader or leaderless replication.
- **decision:** default to single-leader. Multi-leader only for offline clients, collaborative editing,
  or write availability across datacenters. Leaderless only when concurrent conflicting writes are
  tolerable and you will write merge logic.
- **why:** single-leader removes write conflicts outright and keeps the mental model simple, at the
  price of one write bottleneck and a failover problem. Multi-leader and leaderless ride out node
  failure, network cuts and latency spikes, but offer only weak consistency and hand conflict resolution
  to you.
- **check:** name which of the four goals you need: high availability, disconnected operation, latency,
  read scaling. A bare wish for replication names none. Halt on multi-leader inside one datacenter; its
  complexity almost never pays back there.

### synchronous-follower-count
- **condition:** configuring replication durability.
- **decision:** exactly one synchronous follower (semi-synchronous), the rest asynchronous, with an
  async follower promoted into the sync role automatically if the sync one stalls.
- **why:** guarantees a current copy on at least two nodes; writes block while the sync follower is slow
  or down, until promotion completes. Fully asynchronous keeps writes available whatever the followers
  do, but acknowledged writes are lost if the leader dies for good.
- **check:** the database supports per-follower sync settings. Reject all-synchronous: a single node
  outage then stops every write.

### replication-log-format
- **condition:** choosing how the leader ships changes to followers.
- **decision:** prefer a logical (row-based) log. Accept WAL shipping only if database upgrades may take
  downtime. Statement-based only where the engine enforces determinism.
- **why:** a logical log lets leader and followers run different versions or storage engines and gives
  external consumers change data capture for free, at the cost of a second log format. WAL shipping is
  simple but binds replication to the storage layout, so leader and followers usually must match
  versions — ruling out upgrade-followers-then-fail-over, and with it zero-downtime upgrades.
- **check:** know whether zero-downtime version upgrades are required. Halt on statement-based
  replication over nondeterministic work (`NOW()`, `RAND()`, autoincrement, order-dependent `UPDATE …
  WHERE`, triggers with side effects). The version-lock cost describes older physical WAL shipping;
  Postgres native logical replication (version 10 and later) eases it — re-verify against current
  tooling and the version actually in use before acting.

### failover-automation
- **condition:** deciding whether leader failover runs without a human.
- **decision:** automate only with all three in place: (a) fencing enforced at the resource, (b) a
  timeout derived from experiment, (c) a plan for unreplicated writes that get discarded. Any missing →
  keep a human in the loop.
- **why:** automation buys fast recovery. It costs silently dropped writes that break client durability
  expectations; split brain when fencing is absent or flawed (a poor design can shut both nodes down);
  and a timeout with no right value — too short, and an overloaded but live node is declared dead and
  its load lands on a cluster already struggling.
- **check:** list every external system consuming identifiers the leader issues (caches, Redis, message
  keys, external IDs). Halt if any shares primary keys or counters with the database: in one known
  incident a lagging follower was promoted, its autoincrement counter reissued keys already in use,
  those keys doubled as Redis keys, and private data reached the wrong users.

### lag-guarantee-selection
- **condition:** users see data read from an asynchronous replica.
- **decision:** pick the guarantee needed (read-after-write, monotonic reads, consistent prefix), then
  build it explicitly.
- **why:** read-after-write shows users their own writes by sending those reads to the leader, which
  erodes read scaling; across devices it also needs a central last-write timestamp and all of one user's
  devices routed to one datacenter. Monotonic reads stop a user seeing time run backwards by hashing
  each user to a fixed replica, plus a reroute plan for when that replica fails.
- **check:** ask what the application does if lag reaches minutes or hours. If nothing breaks, no
  guarantee is needed. Halt if the answer is a poor user experience and nobody will own the
  implementation — treating async replication as synchronous fails later.

### conflict-resolution-strategy
- **condition:** a multi-leader or leaderless store will accept concurrent writes to one key.
- **decision:** avoid conflicts first by routing every write for a record through one leader. If that is
  impossible, use CRDTs or explicit sibling merge. Last-write-wins (LWW) only for keys written once and
  immutable afterwards.
- **why:** LWW converges with almost no machinery and loses data silently: several writes all report
  success, one survives, and clock skew can drop writes that were not even concurrent (it is Cassandra's
  only method). Explicit merge keeps all data but needs merge code that is intricate and easy to get
  wrong — a cart merge that kept additions and ignored removals brought deleted items back.
- **check:** have an answer for when avoidance breaks, such as datacenter failover or a user changing
  region. Halt if removals exist and the merge is a union: union resurrects deletions, so tombstones are
  needed, which is a data-model change. CRDT tooling has matured, strengthening the case against LWW;
  re-verify current options before acting.

### quorum-parameters
- **condition:** setting `n`, `w`, `r` in a Dynamo-style store.
- **decision:** set `w + r > n` to raise the odds of reading the current value, and treat it as a shift
  in probability, never a guarantee.
- **why:** `w = r = (n+1)/2` tolerates ⌊n/2⌋ failures with reasonable latency both ways. `w = n, r = 1`
  makes reads fast, but one failed node halts all writes. `w + r ≤ n` lowers latency and raises
  availability, at a higher stale-read rate.
- **check:** decide whether sloppy quorums are on; they break the overlap that gives `w + r > n` its
  meaning. Their defaults have differed by store (historically on in Riak, off in Cassandra and
  Voldemort) — re-verify against current tooling before acting. Halt if correctness needs the latest
  value: six known edge cases defeat even strict quorums, so that need calls for transactions or
  consensus.

### anti-entropy-required
- **condition:** running leaderless replication.
- **decision:** if no anti-entropy background process runs, treat rarely read keys as less durable, then
  add one or accept that exposure explicitly.
- **why:** read repair alone adds no background load, but cold data stays under-replicated and nobody
  sees it until a read arrives.
- **check:** identify which keys are read rarely. Halt for regulated or financial data whose only repair
  path is read repair — a value there can be arbitrarily old. The usual example of a store without
  anti-entropy (Voldemort) is effectively unmaintained; re-verify against a live system before acting.

### staleness-as-a-metric
- **condition:** operating any asynchronously replicated system.
- **decision:** measure replica staleness and alert on it. Leader-based: leader log position minus
  follower log position. Leaderless: build a proxy.
- **why:** turns eventual into a number operations can use; eventual consistency is vague by design.
  Costs instrumentation work, which is genuinely hard in leaderless systems that lack a fixed write
  order.
- **check:** unconditional. If no staleness signal can be built, nobody downstream can be honestly
  promised eventual consistency; escalate.

---

## partitioning

### partitioning-scheme
- **condition:** deciding how a dataset spreads across nodes.
- **decision:** range scans needed → key-range. Even load needed → hash. Both → compound key: hash the
  first component, sort on the rest.
- **why:** key-range gives efficient scans and treats the key as a concatenated index, but sequential
  access creates hot spots. Hash spreads load evenly and gives up range queries entirely: MongoDB in
  hash-sharding mode fans every range query to all partitions; Riak, Couchbase and Voldemort offer no
  primary-key range queries. Compound keeps most of both, minus range scans on the first column.
- **check:** know the dominant access pattern and whether the leading key component is monotonic. Halt
  if it is a timestamp on live writes — every write lands on the current partition.

### hot-key-handling
- **condition:** one key draws disproportionate traffic (a celebrity, a viral object).
- **decision:** hashing cannot help, since identical IDs hash identically. Append a random suffix to
  split that key across partitions, and keep a registry of which keys are split.
- **why:** spreads writes across as many partitions as there are suffix values (two decimal digits → 100
  keys). Costs: every read queries all splits and combines them, and the registry needs upkeep —
  splitting every key would be pure overhead.
- **check:** hot keys can be found by sampling or by declaration. Halt if the plan expects the datastore
  to notice and compensate; almost none do, so the application owns it.

### rebalancing-strategy
- **condition:** choosing how partitions map to nodes.
- **decision:** never `hash mod N`. Choose one of: a fixed partition count with many more partitions
  than nodes; dynamic split/merge; a fixed number of partitions per node — always decoupling partition
  count from node count.
- **why:** a fixed count is simple to run and lets stronger nodes take more partitions, but caps node
  count and adds per-partition overhead. Dynamic tracks data volume (HBase splits at a 10 GB default),
  but an empty database starts with one partition, so early writes all hit one node until the first
  split. Pre-splitting avoids that, but for key ranges it requires knowing the distribution in advance.
  `hash mod N` moves nearly every key whenever N changes.
- **check:** bound how far the dataset may grow; under a fixed count, the setup-time number caps the
  nodes you will ever run. Halt on a fixed count for a dataset whose size swings widely: partitions grow
  with data, and oversized ones make rebalancing and recovery costly. Default vnode counts in common
  stores have changed between versions; re-verify against current tooling before acting.

### rebalancing-automation
- **condition:** deciding whether rebalancing runs without a human.
- **decision:** require a human commit step unless you can show that an overloaded but live node cannot
  trigger automatic rebalancing.
- **why:** a manual commit removes operational surprises and slows recovery. Several stores (Couchbase,
  Riak, Voldemort) generate the assignment automatically and wait for an administrator to commit it.
- **check:** applies where automatic failure detection and automatic rebalancing share a cluster. Halt
  if they do with no damping: a slow node gets declared dead, its load moves onto an already loaded
  network and cluster, and the failure can cascade.

---

## encoding

### encoding-format
- **condition:** choosing how data crosses a process boundary.
- **decision:** inside the organisation → a binary schema-driven format (Avro, protobuf, Thrift). Across
  organisations → JSON, XML or CSV. A language's built-in serialization only for data that dies with the
  process.
- **why:** binary schema formats are compact (one sample record takes 81 bytes in JSON, 34 in Thrift
  CompactProtocol, 33 in protobuf, 32 in Avro), keep the schema as documentation that cannot drift
  because decoding needs it, and allow compile-time checks and pre-deploy compatibility checks through a
  registry; the price is data people cannot read without decoding. Built-in serialization carries four
  defects: language lock-in, arbitrary class instantiation that opens remote code execution, versioning
  bolted on late, and poor efficiency.
- **check:** know whether the boundary sits inside your organisational control. Halt when a binary
  format is proposed across organisations — getting separate organisations to agree costs more than the
  format saves.

### avro-or-protobuf
- **condition:** a binary schema format is chosen and one must be picked.
- **decision:** schemas generated by programs, or files that must describe themselves → Avro. Schemas
  hand-written and stable, with generated types in a statically typed language → protobuf or Thrift.
- **why:** Avro matches fields by name, so order is irrelevant and generated schemas work, and its
  container file reads without code generation; the writer's schema must reach the reader somehow (file
  header, version number plus registry, or connection negotiation). protobuf gives generated types and
  IDE support at the cost of hand-allocated tags under a permanent rule: a tag never changes and a
  retired tag is never reused.
- **check:** know whether a person or a program writes the schemas. Halt if schemas are regenerated per
  run (for example from a relational schema on every export) and protobuf is proposed — each change
  would need hand-assigned tags and a generator that never reuses a retired one. Schema registries are
  now the standard way to deliver Avro writer schemas; re-verify against current tooling before acting.

### schema-field-addition
- **condition:** adding a field to a schema already in production.
- **decision:** protobuf/Thrift: give it a new tag and mark it `optional` or give it a default. Avro:
  the new field gets a default value. For either format, test that a decode/re-encode round trip keeps
  unknown fields.
- **why:** keeps compatibility both ways during a rollout; the lasting cost is that no field added after
  deployment can be mandatory. One trap sits outside the format: old code decodes a record holding an
  unknown field into a model object and writes it back, so the encoding kept the field and the object
  mapping dropped it. The fix is easy once someone looks for it.
- **check:** assume rolling upgrades, which multi-node deployments always have. Halt if the new field
  must be `required` (protobuf) or default-free (Avro): new code then fails on old data, which needs its
  own decision.

### rpc-or-rest
- **condition:** designing service-to-service calls.
- **decision:** REST for public APIs and calls across organisations; binary RPC for internal calls
  within one datacenter and organisation. Either way the interface keeps the network visible.
- **why:** binary RPC is faster but gives up the REST ecosystem: calls straight from a browser or `curl`
  with nothing generated or installed, plus the servers, caches, load balancers, proxies, firewalls,
  monitoring and test tools that speak HTTP. Across organisations clients cannot be forced to upgrade,
  so compatibility lasts indefinitely, often as several API versions served side by side.
- **check:** decide whether idempotence is built into the protocol. Halt if a design treats a timeout as
  a failure: a timeout leaves the outcome unknown, and a retry without deduplication can run it twice.

---

## transactions

### need-transactions
- **condition:** deciding whether the application needs multi-object transactions.
- **decision:** it does if any of these holds: foreign-key or graph-edge references must stay valid
  across inserts; denormalised data spans several documents; the store keeps secondary indexes.
- **why:** a transaction collapses a wide fault space (concurrent writes, constraint violations,
  crashes, network cuts, disk failures) into commit or abort. It costs performance and, when
  distributed, availability. Claims that transactions kill scalability, and claims that serious systems
  cannot live without them, both overstate.
- **check:** list the objects that one user action must change together. Halt if the store cannot group
  operations: a multi-put API is not a transaction — some keys can succeed while others fail, leaving
  partial state.

### isolation-level-selection
- **condition:** choosing or auditing an isolation level.
- **decision:** list the anomalies the level still allows and test each against your invariants. Any
  read → decide → write path whose write invalidates its own premise needs serializable.
- **why:** read committed stops dirty reads and writes cheaply, and still allows read skew, lost
  updates, write skew and phantoms. Snapshot isolation gives consistent point-in-time reads; that is how
  a live database supports consistent backups and long analytic queries; it still allows write skew and,
  by vendor, lost updates. Serializable removes them all and costs throughput, latency stability or
  scale, by mechanism.
- **check:** identify every read-decide-write path; in a large codebase that is the hard part. If they
  cannot be enumerated, the code alone cannot show that a weaker level is safe — use serializable and
  pay for it.

### repeatable-read-is-meaningless
- **condition:** a vendor, a config file or a colleague names repeatable read as the isolation level.
- **decision:** ignore the label; establish empirically which anomalies the level prevents.
- **why:** buys accuracy for the cost of testing; skipping the test buys a bug class that appears only
  under concurrency and load. The label differs by vendor: PostgreSQL and MySQL name snapshot isolation
  repeatable read, Oracle names it serializable, and IBM DB2 uses repeatable read to mean
  serializability.
- **check:** you can test, or you have the vendor's documented anomaly list. Halt any compliance or
  design argument that rests on the label alone.

### lost-update-defense
- **condition:** the application does read-modify-write on a shared value.
- **decision:** in order of preference: (1) an atomic write operation; (2) letting the engine detect
  lost updates; (3) explicit locking with `SELECT … FOR UPDATE`; (4) compare-and-set, once your engine's
  CAS is verified safe.
- **why:** atomic operations are correct with no discipline but cannot express arbitrary logic such as
  free-text editing. Auto-detection is a defence nobody can forget, paid for in aborts and retries.
  Explicit locks allow any logic in the critical section, and a missing lock somewhere is easy to
  overlook. CAS fails silently when the engine lets the `WHERE` clause read an old snapshot.
- **check:** know whether your engine detects lost updates. It does under PostgreSQL repeatable read,
  SQL Server snapshot and Oracle serializable; it does not under MySQL/InnoDB repeatable read. Halt in a
  multi-leader or leaderless store — locks and CAS presume a single current copy, and there is none; use
  sibling merge or commutative operations.

### write-skew-recognition
- **condition:** reviewing code that checks a condition and then writes.
- **decision:** if the write changes the check's outcome, it is write skew. When the check tests that
  rows are absent, `SELECT FOR UPDATE` has nothing to lock.
- **why:** serializable isolation prevents it automatically. Materialising conflicts creates a lock
  target where none existed, at the price of fiddly design that leaks concurrency control into the data
  model, so it is a last resort. A unique constraint covers the username case cheaply and does not
  generalise.
- **check:** the SELECT and the write after it are visible in one transaction. If the invariant spans
  several rows and no database constraint (uniqueness, foreign key) can express it, the options are
  serializable, materialised conflicts, or a live bug — choose one explicitly.

### serializability-mechanism
- **condition:** serializable isolation has been decided.
- **decision:** an in-memory dataset with low write throughput → serial execution through stored
  procedures. Predictable access under high contention → two-phase locking (2PL). Low to moderate
  contention with spare capacity → serializable snapshot isolation (SSI).
- **why:** serial execution has no coordination overhead and can beat concurrent engines, but caps at
  one CPU core, needs whole transactions as stored procedures, and cross-partition transactions reach
  about 1,000 writes/second (VoltDB) — orders of magnitude below single-partition, and adding machines
  does not help. 2PL is mature and well understood, but readers and writers block each other, latency is
  unstable with bad high percentiles under contention, and deadlocks discard whole transactions. SSI
  never blocks, keeps latency predictable, runs read-only queries without locks and can distribute
  conflict detection, but aborts under contention, and retries can deepen saturation.
- **check:** know your contention level; optimistic control degrades badly when contention is high. For
  serial execution, halt if any transaction can be slow or the active dataset exceeds memory — one slow
  transaction stalls them all. SSI is now an established, production-proven mechanism.

### retry-discipline
- **condition:** implementing retries after a transaction abort.
- **decision:** retry only transient errors, with a cap and exponential backoff; handle overload errors
  on their own path; deduplicate at the application level; treat external side effects separately.
- **why:** safe retry is what aborts exist for. Five hazards come with it: the transaction may have
  succeeded with only the acknowledgement lost; retrying overload deepens it; retrying a permanent error
  achieves nothing; external side effects repeat; a client crash mid-loop loses the data anyway. Common
  ORMs (Rails ActiveRecord, Django) do not retry by default and so waste that benefit.
- **check:** errors split into transient (deadlock, isolation violation, network cut, failover) and
  permanent (constraint violation). Halt when the transaction sends email, charges a card or otherwise
  acts outside the database — those effects happen even when it aborts.

---

## consistency

### linearizability-necessity
- **condition:** deciding whether an operation needs linearizability.
- **decision:** required for locks and leader election, hard uniqueness constraints, and timing
  dependencies across channels. Not required for foreign-key or attribute constraints, nor where the
  constraint may be read loosely.
- **why:** the system behaves as one copy, so causality across channels holds with no extra machinery.
  The cost is permanent, not only during faults: response time is provably bounded below by the
  uncertainty of network delay, and no faster algorithm exists. Under a partition, linearizable replicas
  that lose contact must stop serving.
- **check:** look for a second communication channel between the two components; the requirement hides
  there. If one exists and cannot be controlled (a message queue racing the store's replication),
  linearizability is the simplest correct answer.

### causal-instead-of-linearizable
- **condition:** a design asks for linearizability but the real need is ordering.
- **decision:** test whether causal consistency is enough; it usually is.
- **why:** causal consistency is the strongest model that neither slows with network delay nor loses
  availability under network failure; the CAP trade-off does not touch it. It costs tracking causal
  dependencies with generalised version vectors and passing that metadata along.
- **check:** phrase the need as: every write that led to what the reader sees is visible to that reader — not the latest
  value. Halt if the need is genuine recency (an atomic compare-and-set, a uniqueness decision made
  now); causality cannot supply that. Production tooling for causal consistency has advanced — re-verify
  against current tooling before ruling it out.

### stop-using-cap
- **condition:** someone cites the CAP theorem to justify a design.
- **decision:** set the framing aside and restate the question: which consistency model, under which
  fault.
- **why:** buys a discussion of the real trade-off at the social cost of contradicting a widely cited
  result. Pick-two-of-three misleads because a partition is a fault, not a choice; the proven result is
  about a single fault type and a single consistency model (linearizability); and its notion of
  availability differs from everyday usage, so many fault-tolerant systems fail its definition.
- **check:** always applies; this position is now the mainstream expert view.

### quorums-are-not-linearizable
- **condition:** a leaderless store is pitched as strongly consistent.
- **decision:** treat it as not linearizable unless it does synchronous read repair on reads and reads a
  quorum before writing.
- **why:** making Dynamo-style quorums linearizable restores recency at a performance penalty Riak
  declines to pay; Cassandra waits for read repair on quorum reads yet still loses linearizability
  through LWW conflict resolution.
- **check:** inspect the store's read-repair timing. Halt if you need a linearizable compare-and-set:
  quorums cannot build one at all; it takes a consensus algorithm.

---

## consensus

### when-you-need-consensus
- **condition:** you are about to build any of: a lock, leader election, a uniqueness constraint, atomic
  commit, a membership service, a totally ordered log.
- **decision:** these are one problem. Use ZooKeeper, etcd or an equivalent; leave the consensus
  algorithm to them.
- **why:** agreement, integrity and validity hold as safety properties even when a majority fails — an
  outage can halt processing but cannot push the system into a wrong decision. Costs: progress needs a
  strict majority (3 nodes survive 1 failure, 5 survive 2); voting is a form of synchronous replication;
  dynamic membership is far less understood than static; and under variable network delay, spurious
  leader elections can consume more time than useful work.
- **check:** accept the operational shape first: a fixed set of three or five voters, majority quorum,
  timeout-based failure detection. Halt and escalate before anyone writes a consensus algorithm;
  homegrown ones have a poor track record.

### total-order-not-enough
- **condition:** you have a total order of operations and want it to enforce a uniqueness constraint.
- **decision:** a total order is not enough; you also need to know when it can no longer change. That
  takes total order broadcast; timestamps cannot give it.
- **why:** total order broadcast gives finality: append the claim, wait until it is delivered back,
  check whether it came first. It costs a round trip through the log before the client gets an answer
  and, being equivalent to consensus, carries the majority-quorum cost.
- **check:** applies when the decision is made now, not reconstructed later. Halt on
  lowest-Lamport-timestamp-wins: it only works once all operations are collected; at decision time
  another node may hold a lower timestamp you have not seen, and polling every node stalls whenever one
  is unreachable.

### two-phase-commit-decision
- **condition:** one atomic commit must span heterogeneous systems.
- **decision:** avoid it where you can. Where XA is unavoidable, run the coordinator as a replicated,
  critical database and staff it that way.
- **why:** buys real atomicity across systems and with it exactly-once message processing (ack the
  message and commit the database writes together). Costs: a participant that voted yes holds its locks
  for the whole in-doubt period — 20 minutes if the coordinator needs 20 to restart, forever if its log
  is lost, and rebooting the database cannot release them because correct 2PC keeps them across
  restarts; MySQL's distributed transactions are reported at more than 10× the cost of single-node ones;
  XA has no cross-system deadlock detection and is incompatible with SSI; and 2PC needs every
  participant to respond, so it amplifies failures.
- **check:** decide where the coordinator's log lives and how it stays available. Halt if the
  coordinator runs inside the application server: its log becomes durable state as important as the
  databases, and the server stops being stateless, breaking add-and-remove deployment. Distributed SQL
  engines with Spanner-style transactions are now mainstream — re-verify against current tooling before
  acting; the critique of XA itself stands.

### zookeeper-scope
- **condition:** deciding what goes into a coordination service.
- **decision:** slow-changing cluster metadata only, for example which node at which address leads
  partition 7. Application runtime state lives elsewhere.
- **why:** you get four features: linearizable atomic operations, change notifications, monotonic
  fencing tokens (`zxid`), and failure detection through sessions and ephemeral nodes; only the first
  needs consensus, and the value lies in the combination. Costs an external dependency and a fixed
  voting-node count.
- **check:** the data changes on a scale of minutes or hours and fits in RAM on an ensemble of 3–5
  nodes. Halt if it changes thousands of times per second, or if majority votes across thousands of
  nodes are on the table — hopelessly inefficient.

### service-discovery-consistency
- **condition:** choosing a service-discovery mechanism.
- **decision:** service discovery runs without consensus; leader election needs it.
- **why:** DNS-style discovery gives availability, caching and resilience to network cuts, at the cost
  of staleness that is normally harmless. When the consensus system already knows who leads, publishing
  that fact through read-only caching replicas (fed the decision log asynchronously, not voting) gets
  both.
- **check:** slightly stale endpoints are tolerable, as DNS users already accept. Halt if the discovery
  result decides who leads rather than where to connect.

### fencing-tokens
- **condition:** a lock or lease guards a shared resource across a network.
- **decision:** every grant carries a monotonically increasing token; every write must present it; the
  resource refuses any token below the highest one it has already accepted.
- **why:** stops a stale lock holder from corrupting data (a real HBase corruption bug had this shape).
  Costs a server-side check, which is healthy anyway: a service should not count on clients behaving. A
  malicious node that forges tokens gets through; that is a Byzantine fault and outside these rules.
- **check:** the resource can check tokens, or the token can ride inside something it already checks
  (for example a filename). Halt if only clients check their own lock status — a paused process wakes up
  believing no time has passed.

### timeout-and-clock-discipline
- **condition:** code checks an expiry set on another machine against the local clock, or sorts events
  by timestamp.
- **decision:** measure durations with monotonic clocks, order events with logical clocks, and keep
  time-of-day clocks for display. Derive timeouts from a measured round-trip distribution, or use an
  adaptive detector.
- **why:** adaptive detection (Phi Accrual, as used in Akka and Cassandra) tracks reality at the cost of
  implementation effort. Ordering by physical timestamps loses data silently: even with skew under 3 ms,
  better than usual, a worked case orders two writes wrongly and drops one. NTP cannot fix it, since its
  accuracy is bounded by network round-trip time; the clock source would have to be far more precise
  than the thing it measures.
- **check:** round trips have been measured over a long period across many machines. Halt if a constant
  timeout is picked by intuition, or correctness rests on wall-clock ordering. Cloud providers now offer
  microsecond-class time sync, so the classic figures (35 ms best-case internet NTP, 200 ppm drift) need
  re-verifying against current tooling before acting; the structural point — a clock reading is an
  interval, not a point — stands.

### monitor-clock-offsets
- **condition:** operating any system whose correctness depends on clocks.
- **decision:** track the clock offset of every machine against the others and remove any node whose
  drift exceeds the limit.
- **why:** catches a failure that looks exactly like normal operation: a faulty quartz clock or a
  misconfigured NTP client leaves most things working and produces subtle data loss instead of a crash.
  Costs monitoring infrastructure.
- **check:** unconditional. If a drifting node cannot be evicted, silent corruption is an accepted
  outcome; escalate.

---

## batch

### batch-output-destination
- **condition:** a batch job produces data a live application will query.
- **decision:** have the job itself build the database files, write them once to its output directory,
  and let read-only servers bulk-load them and switch over atomically.
- **why:** no network round trip per record, no extra load on production, all-or-nothing job output
  preserved, and instant rollback — the server keeps serving old files while new ones copy in, and can
  switch back on error. Costs a bulk-load pipeline. Writing per record instead runs orders of magnitude
  slower, swamps the production database for everyone, and creates external side effects that break
  exactly-once, forcing reasoning about partial jobs, task retries and speculative execution.
- **check:** the target store bulk-loads externally built files (Voldemort, Terrapin, ElephantDB, HBase
  bulk load). If it does not and per-record writes into production are the only path, name those three
  consequences explicitly before proceeding.

### join-algorithm
- **condition:** joining two datasets in a distributed batch job.
- **decision:** choose by what you can assume. Nothing → sort-merge. One input small enough for memory →
  broadcast hash join. Inputs partitioned the same way → partitioned hash join. Partitioned the same way
  and sorted → map-side merge join.
- **why:** sort-merge assumes nothing and pays for sorting, copying to reducers and merging, touching
  disk several times. Map-side joins drop the whole reduce stage but depend on size, sort and partition
  guarantees an earlier job must have set up. The output layout follows: after a reduce-side join,
  output is partitioned and sorted on the join key; after a map-side join, output keeps the partitioning
  of the large input.
- **check:** know the physical layout — format and directory, plus partition count and the keys data is
  partitioned and sorted by. If the layout cannot be established, only sort-merge is safe. These are the
  algorithms Spark, Flink and query optimisers run today.

### batch-hot-key
- **condition:** a join or grouping key is wildly skewed.
- **decision:** sample or declare the hot keys, then spread their records across reducers at random and
  replicate the other side; or aggregate in two stages.
- **why:** restores parallelism on the hot key. Costs replicating the other join input to every reducer
  handling that key or, in the two-stage form, an extra pass.
- **check:** hot keys are known before the run (Pig samples; Crunch and Hive need declaration). Halt if
  they cannot be identified and the job has a deadline — one reducer will set the runtime.

### materialize-or-pipeline
- **condition:** chaining processing stages.
- **decision:** when other teams consume the output, materialise it at a well-known location; when it is
  intermediate state inside one team's workflow, pipeline it through a dataflow engine.
- **why:** materialising gives durable intermediate state, so a failed task simply reads its input
  again, plus a named dataset others can reuse, which decouples producer and consumer; it pays for
  stragglers blocking stage transitions, redundant mapper stages and replicated temporary data.
  Pipelining gets the six dataflow-engine gains, including operators that start as soon as input is ready;
  it pays recomputation on failure, which requires determinism.
- **check:** know whether the output has consumers you do not control. Halt on a recomputation-based
  engine over nondeterministic logic (hash-table iteration order, random numbers, the system clock,
  external data sources): recomputed data that differs from the lost data leaves downstream
  contradictions that only killing and rerunning downstream operators resolves. MapReduce itself is
  obsolete for new work; apply the fork inside a dataflow engine.

### graph-processing-scale
- **condition:** running a graph algorithm over a whole graph.
- **decision:** when the graph fits on one machine, in memory or even on local disk, run a
  single-machine algorithm. Distribute only when it really cannot fit.
- **why:** one machine avoids cross-machine message passing, whose intermediate state often outgrows the
  graph, so a single-threaded run often beats a distributed batch job. Distributed processing exceeds
  one machine and pays heavy communication overhead, since graphs are usually split by arbitrary vertex
  ID with no grouping of related vertices.
- **check:** measure the graph's size; an estimate does not count. If it does not fit, Pregel/BSP is
  unavoidable and efficient graph parallelism is still an open research area — budget for that.

---

## stream

### broker-type
- **condition:** choosing a message broker.
- **decision:** ordering matters, throughput is high, each message is quick, replay has value →
  log-based broker. Each message is expensive to handle, order does not matter, and history is never
  replayed → AMQP/JMS-style broker.
- **why:** a log-based broker gives replay (run a consumer copy from yesterday's offsets, writing
  elsewhere), total order within a partition, cheap tracking (one offset instead of per-message acks),
  throughput steady whatever the retention, and a lagging consumer that hurts only itself, which makes
  it safe for debugging on production data. It caps parallelism at the partition count and suffers
  head-of-line blocking behind a slow message. AMQP/JMS gives per-message parallelism, but consumption
  is destructive and load balancing with redelivery reorders messages unavoidably; neither standard
  stops it.
- **check:** know whether consumers will ever reprocess history. Halt if you need both fine-grained
  per-message parallelism and strict ordering — they exclude each other; pick one. Queue semantics are
  arriving on log brokers (Kafka KIP-932, Redpanda), so the split is blurring; re-verify against current
  tooling before treating it as absolute.

### never-dual-write
- **condition:** the same data must land in two or more stores.
- **decision:** name one system of record and derive the others from its change stream; the application
  writes only to the system of record.
- **why:** CDC lets a single leader fix write order, which removes the race, and makes bootstrapping any
  future derived system free; it costs asynchrony, so every replication-lag problem applies and a user
  may read a stale derived view right after writing. Dual writes fail two ways: a race that diverges
  permanently without raising any error, invisible without version vectors, and a partial failure where
  one write lands and the other does not.
- **check:** the system of record emits a change stream, through CDC on its replication log or an
  explicit event log. If it cannot and dual writes are the only path, add concurrency detection (version
  vectors) and an atomic commit, and state plainly that the expensive path was chosen.

### cdc-or-event-sourcing
- **condition:** choosing how to produce the change stream.
- **decision:** CDC when the application already mutates a database and should stay unchanged. Event
  sourcing when the application is yours to change and the log should record intent.
- **why:** CDC is invisible to the application and supports log compaction, since every event holds the
  complete new record and older events for the same key become discardable; its events record mechanism,
  not meaning. Event sourcing records events that outlive new features (a student cancelled an
  enrolment, rather than a delete and an insert that bake in assumptions about later use) and adds
  auditability and debuggability; later events do not supersede earlier ones, so compaction does not
  work the same way, the full history must stay, and snapshots are only a read optimisation.
- **check:** for event sourcing, a place exists to validate before publishing. Halt if a consumer is
  expected to reject events — once in the log an event is immutable and others may already have read it.
  Run validation synchronously ahead of publishing, or emit a tentative event and confirm it later.

### log-compaction-for-bootstrap
- **condition:** a new derived system must be built from an existing database.
- **decision:** with a log-compacted change topic, point a fresh consumer at offset 0 and build from the
  log. Without one, take a consistent snapshot pinned to a known log position.
- **why:** yields a full copy without touching the source database, with disk use tracking current
  contents rather than write history. Costs one stored record per live key indefinitely, plus compaction
  work.
- **check:** each change has a primary key and each update overwrites the earlier value for its key.
  Halt if events express intent rather than state (event sourcing) — compaction cannot summarise them.

### event-time-windowing
- **condition:** computing any windowed aggregate on a stream.
- **decision:** window by event time, not processing time, and decide explicitly what happens to
  stragglers: drop them and count the drops, or correct and retract.
- **why:** event time stays deterministic under reprocessing and correct across restarts, but no window
  is ever known for certain to be complete. Processing time is simpler and fine when lag is negligible,
  yet each redeploy shows a phantom spike as the backlog drains and a steady rate looks like a burst.
- **check:** a trustworthy event timestamp exists. On user-controlled devices it does not: record event
  time and send time by device clock and receipt time by server clock, and subtract to estimate the
  offset. Halt on ignoring stragglers without measuring them — that is silent corruption.

### stream-join-time-dependence
- **condition:** joining a stream against state that changes over time.
- **decision:** decide which version of the state the join uses and encode that choice. Where historical
  correctness matters, version dimension records explicitly (slowly changing dimension, SCD).
- **why:** SCD versioning makes the join deterministic — an invoice references the tax rate in force at
  the time of sale, not today's. Costs: compaction of the log is ruled out, because all versions of all
  dimension records must be kept.
- **check:** know whether the output will ever be recomputed from history. Halt if ordering across
  streams is undetermined and the result must be reproducible — reruns on identical input may then
  differ.

### exactly-once-mechanism
- **condition:** a stream processor must not apply an effect twice.
- **decision:** prefer idempotence keyed on the input offset; use the framework's internal atomic commit
  only where idempotence cannot work. Microbatching or checkpointing alone stops being enough once
  output leaves the framework.
- **why:** idempotence gives effectively-once at small overhead, paid in its four preconditions and
  extra metadata (the triggering offset stored with the value). Internal atomic commit covers state
  changes, messages and the offset advance together, amortised over several messages per transaction,
  but only inside one framework — deliberately, since cross-technology XA is what it avoids.
- **check:** idempotence needs four things: processing is deterministic; replay yields the same messages
  in the same order; nothing else writes the same value at the same time; failover is fenced. Halt on
  external irreversible effects (email, card charge): once output leaves the processor, the framework
  cannot discard a failed batch's output. Framework transactions (Kafka transactions) now ship, so
  internal atomic commit is available off the shelf.

### stream-state-recovery
- **condition:** a stream processor holds state (windows, joins, local table replicas).
- **decision:** hold state locally and either replicate it on a schedule or rebuild it by replaying the
  input streams. A remote database lookup per message is acceptable only once measured as fast enough.
- **why:** local state with periodic replication avoids a network round trip per message, at the cost of
  a replication mechanism. Options: periodic snapshots of operator state to durable storage (Flink);
  streaming every state change into a log-compacted Kafka topic, which is CDC on your own state (Samza,
  Kafka Streams); or redundant processing of each input on several nodes (VoltDB).
- **check:** know whether the state can be rebuilt; short-window aggregates and log-compacted database
  replicas both can. No single trade-off fits every case, and the local-versus-remote balance moves as
  storage and networks change — re-measure when the platform changes.

---

## correctness of derived data

### timeliness-vs-integrity
- **condition:** someone says the system must be consistent.
- **decision:** split the requirement into timeliness and integrity and establish which one is meant.
  Timeliness violations are temporary and heal on their own; integrity violations are permanent and need
  explicit repair.
- **why:** lets you relax timeliness, where nearly all coordination cost sits, while holding integrity,
  at the cost of doing the analysis. Late data is eventual consistency; corrupted data is permanent
  inconsistency; in most applications integrity matters far more than timeliness.
- **check:** name one concrete failure of each kind for this application. Halt if the requirement is
  integrity and the design leans on anything eventual — waiting does not repair corruption.

### end-to-end-operation-id
- **condition:** an operation can be retried by a person or by a client you do not control.
- **decision:** generate a unique operation ID at the outermost client, carry it to the store, and
  enforce it with a uniqueness constraint on a requests table.
- **why:** gives real end-to-end idempotence, enforced correctly even at weak isolation, because
  relational databases maintain uniqueness constraints reliably (an application check-then-insert fails
  under non-serializable isolation). Costs a requests table and an ID threaded through every hop; the
  table doubles as an event log, so balance updates can be derived later instead of written in the same
  transaction.
- **check:** the outermost client can create the ID and send the same one again on retry, for instance
  from a hidden form field or by hashing the fields that matter. Halt if a design claims TCP, database
  transactions or stream-processor exactly-once suppress duplicates; none reaches beyond its own layer —
  the classic two-UPDATE money transfer is not correct on its own, and real banks do not work that way.

### loose-constraint-or-linearizable
- **condition:** the application has a uniqueness or capacity constraint.
- **decision:** ask whether an apology is acceptable. Yes → check the constraint asynchronously and
  compensate. No → pay for synchronous coordination.
- **why:** loose constraints run without coordination — a multi-leader, multi-datacenter deployment
  where each region carries on independently — while keeping integrity, at the price of occasional
  apologies and a workflow to issue them. Coordination cuts apologies for inconsistency but can reduce
  performance and availability, raising apologies for outages; the total never reaches zero.
- **check:** a compensating process exists or can exist, and often already does for other reasons. Halt
  if the operation cannot be undone — validate before, not after.

### multi-partition-without-atomic-commit
- **condition:** one logical operation must update state in several partitions.
- **decision:** log the request as one message first, derive per-partition instructions from it, and
  deduplicate downstream by request ID.
- **why:** gives the same property as atomic commit — each request takes effect exactly once in each
  partition it touches, even under faults — without any distributed transaction or cross-partition
  coordination, because a single-object write is atomic in nearly every store. Costs an extra derivation
  stage and dedup state at each consumer; the client sees the outcome asynchronously unless it waits on
  an output stream.
- **check:** the request-to-instructions derivation is deterministic. Halt if it is not: replay after a
  crash yields different instructions and deduplication no longer protects you.

### audit-your-derived-data
- **condition:** any derived dataset exists (index, cache, materialised view, model).
- **decision:** on a schedule, rebuild it from the source log and compare the two; keep hashes of the
  event log to catch storage corruption; run real restores of your backups.
- **why:** catches corruption from any source on the path, because every disk, network, service and
  algorithm along it sits inside the comparison; like automated tests, it lets you move faster because
  bugs surface early. Costs compute and storage for the redundant derivation; skipping it means finding
  corruption downstream, later, when tracing it is far harder.
- **check:** the derivation is deterministic and repeatable, which event sourcing gives by construction.
  Halt if it cannot be re-run: a correct view and a corrupted one are then indistinguishable for good.

### unbundle-or-integrate
- **condition:** choosing between composing several specialised stores and using one product.
- **decision:** if one product meets every requirement, use it. Compose only when none does.
- **why:** unbundling buys breadth — good performance across a far wider range of workloads than one
  product covers. Each component brings its own learning curve, configuration and operational quirks,
  and on any one workload the composition probably trails a system built for it; the aim is breadth, not
  beating one database at its own job.
- **check:** access patterns are enumerated honestly, not anticipated. Halt if the composition targets
  scale you do not have — that is premature optimisation and can lock in a rigid design.

### derived-view-migration
- **condition:** a data restructuring or schema change that is beyond what `ALTER TABLE` can do.
- **decision:** keep old and new as two independently derived views over the same underlying data, move
  a small share of users to the new one, raise the share gradually, then drop the old view.
- **why:** every stage is reversible, so a working system is always one step back, and lower risk of
  irreversible damage lets you move faster. Costs running both views at once, with the storage and
  operating load that implies — like dual-gauge railway track converted over years, costly enough that
  odd gauges still survive.
- **check:** the source data can be processed again — from an event log, or from a snapshot plus the
  changes since. Halt if it was overwritten destructively: nothing remains to re-derive from, and the
  migration is big-bang again.

### write-path-read-path-boundary
- **condition:** deciding whether to add a cache, an index or a materialised view.
- **decision:** state where you are moving the boundary between write path and read path and what each
  side gains. Caches, indexes and materialised views are one decision placed at different points.
- **why:** moving work to the write path makes reads cheaper, at the cost of more work per write and a
  derived dataset to keep correct. The boundary can differ per segment: a social timeline can push posts
  out on write for ordinary users and assemble them on read for accounts with huge followings.
- **check:** quantify the work on each side today. Halt if the current read-path cost is unknown — then
  nobody can say whether moving the boundary helps.

### data-collection-minimization
- **condition:** choosing which personal data to gather and its retention period.
- **decision:** gather less, delete it the moment it stops being needed, and weigh the risk against
  every plausible future holder of the data, not only today's.
- **why:** shrinks the blast radius of a breach, an insider leak, a bankruptcy sale, legal compulsion or
  a hostile acquisition; personal data behaves as a toxic asset. Costs analysis you might otherwise have
  run. Purging cuts against immutability, which is solvable: some stores support targeted removal
  (Datomic calls it excision, Fossil calls it shunning).
- **check:** you can actually delete; true deletion is hard because storage engines, filesystems and
  SSDs write to new locations instead of overwriting, and backups are often immutable by design. Halt if
  retention assumes that today's controls, owners and government will last. The regulatory landscape
  (GDPR, CCPA and successors, AI-specific regimes) has moved — re-verify the legal side against current
  rules before acting; the engineering guidance holds.
