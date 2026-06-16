# simulate-students — CS exam student simulator

Simulate N students working on CS exam tasks. Student agents write Python code at human typing speed, make real git commits, and POST them to the cheat-buster server. Cheating students copy each other's files and submit them under the same (or renamed) filename, producing detectable similarity signals.

---

## Task pools

```
SHARED_POOL — cheating students write these (guaranteed overlap):
  bubble_sort.py     — bubble sort a list
  fibonacci.py       — print first N fibonacci numbers
  count_vowels.py    — count vowels in a string

SOLO_POOL — honest students + cheater "cover" tasks:
  reverse_string.py  — reverse a string using a loop
  factorial.py       — recursive factorial function
  find_max.py        — find max in a list without max()
  palindrome.py      — check if a string is a palindrome
  simple_stack.py    — Stack class with push, pop, peek
  temp_convert.py    — celsius to fahrenheit converter
  linear_search.py   — linear search returning index
```

---

## Phase 0 — Config

Use **AskUserQuestion** to collect (2 calls):

**Call 1** (2 questions):
- "Cheat-buster server URL?" (default: `http://localhost:8000`)
- "Exam ID to use? (teacher must have created it already)"

**Call 2** (2 questions):
- "Teacher email and password (format: email:password) — needed to trigger analysis in Phase 5"
- "Rename mode for copied files? same = copier saves as original filename (tests current detection). renamed = copier saves as filename_v2.py (tests TASK-041 cross-file detection, will NOT be detected until TASK-041 is implemented)"

Store: `SERVER_URL`, `EXAM_ID`, `TEACHER_CREDS` (email:password), `RENAME_MODE` (same|renamed)

Validate: authenticate teacher and confirm exam exists:
```bash
TEACHER_EMAIL=$(echo "$TEACHER_CREDS" | cut -d: -f1)
TEACHER_PASS=$(echo "$TEACHER_CREDS" | cut -d: -f2-)

TEACHER_TOKEN=$(curl -s -X POST "${SERVER_URL}/auth/teacher" \
  -c /tmp/cb-teacher-cookie.txt \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEACHER_EMAIL}\",\"password\":\"${TEACHER_PASS}\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','FAILED'))")

echo "Teacher token: ${TEACHER_TOKEN:0:20}..."
```

If teacher auth fails, stop and report error.

---

## Phase 1 — Setup

Use **AskUserQuestion** (2 questions):
- "How many students total? (2–10)"
- "How many cheater PAIRS? Each pair = 1 source student + 1 copier student. (0 to total/2)"

Store:
- `TOTAL` = total students
- `PAIR_COUNT` = cheater pairs
- `COLLAB_COUNT` = PAIR_COUNT * 2 (total cheating students)
- `HONEST_COUNT` = TOTAL - COLLAB_COUNT

**Ask (1 question):**
- "Base working directory? Each student gets a subdirectory. Example: /tmp/exam-sim"

Store `BASE_DIR`.

Assignment:
- Students 1…PAIR_COUNT = **sources** (write shared tasks, share files)
- Students (PAIR_COUNT+1)…COLLAB_COUNT = **copiers** (copy from their paired source)
  - Copier (PAIR_COUNT+k) is paired with source k
- Students (COLLAB_COUNT+1)…TOTAL = **honest**

---

## Phase 2 — Environment Setup + Authentication

Run as orchestrator using Bash tool:

```bash
# 1. Create directories
for i in $(seq 1 {TOTAL}); do
    mkdir -p {BASE_DIR}/student${i}
done
mkdir -p /tmp/cheat-buster-sim/share
for i in $(seq 1 {TOTAL}); do
    mkdir -p /tmp/cheat-buster-sim/inbox/student${i}
done
echo "" > /tmp/cheat-buster-sim/relayed.log

# 2. Authenticate each student with server, store tokens
for i in $(seq 1 {TOTAL}); do
    TOKEN=$(curl -s -X POST "{SERVER_URL}/auth/student" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"sim_student${i}@exam.test\",\"exam_id\":{EXAM_ID},\"group_number\":\"SIM\",\"variant\":1}" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")
    echo "${TOKEN}" > /tmp/cheat-buster-sim/token_student${i}.txt
    echo "student${i} token: ${TOKEN:0:20}..."
done

# 3. Git init per student
for i in $(seq 1 {TOTAL}); do
    cd {BASE_DIR}/student${i}
    git init -q
    git config user.email "sim_student${i}@exam.test"
    git config user.name "Sim Student ${i}"
done
```

After setup, confirm to user that all tokens were obtained and git repos initialized. Ask user to confirm before proceeding.

---

## Phase 3 — Launch Student Agents

**Launch all TOTAL agents in a single message (parallel)**. All use:
- `subagent_type: Bash`
- `model: haiku`
- `run_in_background: true`

Read token for each student before building its prompt:
```bash
TOKEN_SID=$(cat /tmp/cheat-buster-sim/token_student{SID}.txt)
```

Embed the actual token value in each agent prompt (not the variable name).

---

### Agent prompt — HONEST student

Replace `{SID}`, `{WORK_DIR}`, `{SERVER_URL}`, `{TOKEN}` with actual values.

```
You are a CS student (student{SID}) working on a programming exam. You only have the Bash tool.

Working directory: {WORK_DIR}
Server: {SERVER_URL}
Your auth token: {TOKEN}

=== SETUP (run once at start) ===

```bash
cd {WORK_DIR}

# Write the commit-and-post helper
cat > /tmp/cb_post_{SID}.py << 'PYEOF'
import subprocess, json, urllib.request, sys, os

filepath = sys.argv[1]
server_url = os.environ['CB_SERVER']
token = os.environ['CB_TOKEN']
timestamp = subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ']).decode().strip()

commit_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff = subprocess.check_output(['git', 'show', 'HEAD', '--', filepath],
                               stderr=subprocess.DEVNULL).decode(errors='replace')

lines_added   = sum(1 for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++'))
lines_removed = sum(1 for l in diff.splitlines() if l.startswith('-') and not l.startswith('---'))

payload = json.dumps({'commits': [{'commit_id': commit_id, 'timestamp': timestamp,
    'exercise_id': 'default', 'file_name': filepath,
    'lines_added': lines_added, 'lines_removed': lines_removed, 'diff': diff}]}).encode()

req = urllib.request.Request(server_url + '/commits', data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f'  [server] posted {filepath} commit {commit_id[:8]} ({lines_added}+/{lines_removed}-)')
except Exception as e:
    print(f'  [server] ERROR: {e}', file=sys.stderr)
PYEOF

export CB_SERVER="{SERVER_URL}"
export CB_TOKEN="{TOKEN}"

commit_and_post() {
    git add "$1" 2>/dev/null
    git diff --cached --quiet && return 0
    git commit -m "auto: $(date -u +%Y-%m-%dT%H:%M:%SZ)" --quiet
    python3 /tmp/cb_post_{SID}.py "$1"
}
```

=== YOUR TASK ===

Write 3 programs from the SOLO POOL. Pick any 3:
  reverse_string.py, factorial.py, find_max.py,
  palindrome.py, simple_stack.py, temp_convert.py, linear_search.py

=== SLOW TYPING RULE ===

Write one line at a time with delays (simulates human typing):

```bash
wl() {
    printf '%s\n' "$1" >> "$2"
    sleep $(python3 -c "import random; print(round(random.uniform(0.4, 2.5), 1))")
}
```

=== CODE QUALITY ===

Write like a real student. Use descriptive multi-word variable names so the AST analysis can detect patterns:
- Variables: `count`, `result`, `length`, `current_val`, `max_val`, `temp_val`, `index`, `total`
- Functions: `bubble_sort`, `find_maximum`, `count_vowels`, `is_palindrome`
- Avoid single-char names like `i`, `n`, `s` — use `idx`, `num`, `text` instead
- Naive implementations, occasional comments, 12–25 lines per file
- No list comprehensions, lambdas, or advanced features

=== WORKFLOW ===

For each of your 3 programs:
1. Write the file line by line using wl()
2. Call commit_and_post <filename>
3. Continue to next program

Example for find_max.py:
```bash
wl "# find the maximum element in a list" find_max.py
wl "def find_maximum(arr):" find_max.py
wl "    max_val = arr[0]" find_max.py
wl "    for idx in range(1, len(arr)):" find_max.py
wl "        if arr[idx] > max_val:" find_max.py
wl "            max_val = arr[idx]" find_max.py
wl "    return max_val" find_max.py
wl "" find_max.py
wl "my_list = [3, 1, 7, 2, 9, 4]" find_max.py
wl "result = find_maximum(my_list)" find_max.py
wl "print('Maximum:', result)" find_max.py
commit_and_post find_max.py
```

Start now.
```

---

### Agent prompt — SOURCE student (cheater who shares)

Replace `{SID}`, `{WORK_DIR}`, `{SERVER_URL}`, `{TOKEN}` with actual values.

```
You are a CS student (student{SID}) working on a programming exam. You only have the Bash tool.

Working directory: {WORK_DIR}
Server: {SERVER_URL}
Your auth token: {TOKEN}

=== SETUP (run once at start) ===

```bash
cd {WORK_DIR}

cat > /tmp/cb_post_{SID}.py << 'PYEOF'
import subprocess, json, urllib.request, sys, os

filepath = sys.argv[1]
server_url = os.environ['CB_SERVER']
token = os.environ['CB_TOKEN']
timestamp = subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ']).decode().strip()

commit_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff = subprocess.check_output(['git', 'show', 'HEAD', '--', filepath],
                               stderr=subprocess.DEVNULL).decode(errors='replace')

lines_added   = sum(1 for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++'))
lines_removed = sum(1 for l in diff.splitlines() if l.startswith('-') and not l.startswith('---'))

payload = json.dumps({'commits': [{'commit_id': commit_id, 'timestamp': timestamp,
    'exercise_id': 'default', 'file_name': filepath,
    'lines_added': lines_added, 'lines_removed': lines_removed, 'diff': diff}]}).encode()

req = urllib.request.Request(server_url + '/commits', data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f'  [server] posted {filepath} commit {commit_id[:8]} ({lines_added}+/{lines_removed}-)')
except Exception as e:
    print(f'  [server] ERROR: {e}', file=sys.stderr)
PYEOF

export CB_SERVER="{SERVER_URL}"
export CB_TOKEN="{TOKEN}"
SHARED_DIR="/tmp/cheat-buster-sim/share"

commit_and_post() {
    git add "$1" 2>/dev/null
    git diff --cached --quiet && return 0
    git commit -m "auto: $(date -u +%Y-%m-%dT%H:%M:%SZ)" --quiet
    python3 /tmp/cb_post_{SID}.py "$1"
}

share_file() {
    cp "$1" "${SHARED_DIR}/student{SID}_$1"
    echo "student{SID} shared $1 at $(date -u +%H:%M:%S)" >> /tmp/cheat-buster-sim/relayed.log
    echo "  [share] shared $1"
}
```

=== YOUR TASK ===

Write ALL 3 programs from the SHARED POOL in order:
  1. bubble_sort.py
  2. fibonacci.py
  3. count_vowels.py

Then write 1 program from the SOLO POOL as extra work.

=== SLOW TYPING RULE ===

```bash
wl() {
    printf '%s\n' "$1" >> "$2"
    sleep $(python3 -c "import random; print(round(random.uniform(0.4, 2.5), 1))")
}
```

=== CODE QUALITY ===

Use descriptive multi-word variable names (required for structural analysis):
- `current_val`, `max_val`, `temp_val`, `count`, `result`, `length`, `index`, `total`
- Function names: `bubble_sort`, `fibonacci_seq`, `count_vowels`
- No single-char names except loop counters (`idx`, not `i`)
- 15–25 lines per file, naive implementations, a few comments

=== WORKFLOW ===

For each of the 3 SHARED programs:
1. Write file line by line using wl()
2. Call commit_and_post <filename>
3. Call share_file <filename>   ← shares with peers immediately after committing
4. Continue to next program

After all 3 shared programs, write 1 SOLO POOL program (no sharing needed).

Start now.
```

---

### Agent prompt — COPIER student (cheater who receives)

Replace `{SID}`, `{WORK_DIR}`, `{SERVER_URL}`, `{TOKEN}`, `{INBOX_DIR}`, `{RENAME_MODE}` with actual values.
`{RENAME_MODE}` is either `same` or `renamed`.

```
You are a CS student (student{SID}) working on a programming exam. You only have the Bash tool.

Working directory: {WORK_DIR}
Server: {SERVER_URL}
Your auth token: {TOKEN}
Inbox: {INBOX_DIR}
File rename mode: {RENAME_MODE}

=== SETUP (run once at start) ===

```bash
cd {WORK_DIR}

cat > /tmp/cb_post_{SID}.py << 'PYEOF'
import subprocess, json, urllib.request, sys, os

filepath = sys.argv[1]
server_url = os.environ['CB_SERVER']
token = os.environ['CB_TOKEN']
timestamp = subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ']).decode().strip()

commit_id = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
diff = subprocess.check_output(['git', 'show', 'HEAD', '--', filepath],
                               stderr=subprocess.DEVNULL).decode(errors='replace')

lines_added   = sum(1 for l in diff.splitlines() if l.startswith('+') and not l.startswith('+++'))
lines_removed = sum(1 for l in diff.splitlines() if l.startswith('-') and not l.startswith('---'))

payload = json.dumps({'commits': [{'commit_id': commit_id, 'timestamp': timestamp,
    'exercise_id': 'default', 'file_name': filepath,
    'lines_added': lines_added, 'lines_removed': lines_removed, 'diff': diff}]}).encode()

req = urllib.request.Request(server_url + '/commits', data=payload,
    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print(f'  [server] posted {filepath} commit {commit_id[:8]} ({lines_added}+/{lines_removed}-)')
except Exception as e:
    print(f'  [server] ERROR: {e}', file=sys.stderr)
PYEOF

export CB_SERVER="{SERVER_URL}"
export CB_TOKEN="{TOKEN}"

commit_and_post() {
    git add "$1" 2>/dev/null
    git diff --cached --quiet && return 0
    git commit -m "auto: $(date -u +%Y-%m-%dT%H:%M:%SZ)" --quiet
    python3 /tmp/cb_post_{SID}.py "$1"
}

# FAST writer — simulates copy-paste speed
wl_fast() {
    printf '%s\n' "$1" >> "$2"
    sleep $(python3 -c "import random; print(round(random.uniform(0.05, 0.25), 2))")
}
```

=== YOUR TASK ===

**Part 1**: Write 1–2 programs from the SOLO POOL (your own work):
  Choose from: reverse_string.py, factorial.py, find_max.py, palindrome.py, temp_convert.py

**Part 2**: Check inbox every 30 seconds. When peer's files arrive, copy them IMMEDIATELY.

=== SLOW TYPING RULE (Part 1 only) ===

```bash
wl() {
    printf '%s\n' "$1" >> "$2"
    sleep $(python3 -c "import random; print(round(random.uniform(0.4, 2.5), 1))")
}
```

=== CODE QUALITY (Part 1) ===

Use descriptive multi-word variable names: `count`, `result`, `length`, `current_val`, `index`.
12–20 lines, naive implementations. No single-char names.

=== WORKFLOW ===

**Step A — Write your own work first:**
Write 1–2 SOLO POOL programs using wl(), then commit_and_post each.

**Step B — Poll inbox and copy received files:**

Repeat this loop until you've received all 3 shared files (bubble_sort.py, fibonacci.py, count_vowels.py):

```bash
# Check inbox
ls {INBOX_DIR}/

# If files present, for each file:
RECEIVED_FILE="<filename>"   # e.g. bubble_sort.py

# RENAME MODE: {RENAME_MODE}
# If RENAME_MODE == "same":  save as original filename
#   TARGET="${RECEIVED_FILE}"
# If RENAME_MODE == "renamed":  save as filename_v2.py
#   TARGET="${RECEIVED_FILE%.py}_v2.py"
TARGET="<determined by rename mode above>"

# Copy peer's code into your file using FAST writer (simulates copy-paste)
# Read the received file line by line and write to TARGET
while IFS= read -r line; do
    wl_fast "$line" "$TARGET"
done < {INBOX_DIR}/${RECEIVED_FILE}

# Make one small modification to look like your own work
# (rename one variable: add a comment at the top, or change a variable name)
# Example: prepend a comment line
sed -i '1s/^/# my solution\n/' "$TARGET"

# Commit and post FAST — must happen within 5 minutes of source's commit
commit_and_post "$TARGET"

# Remove from inbox
rm {INBOX_DIR}/${RECEIVED_FILE}
echo "  [copy] submitted $TARGET"
```

Sleep 30 seconds between inbox checks. Do NOT wait longer — speed matters for sequential detection.

Start now. Begin with Part A (your own SOLO POOL program).
```

---

## Phase 4 — Relay Loop

After launching all agents, run this loop using Bash tool.
Relay at **3-second intervals** (fast = sequential detection window is 300s).

```bash
SEEN_FILES=""
SOURCE_IDS="{space-separated source SIDs}"   # e.g. "1 2"
COPIER_MAP="{source:copier pairs}"           # e.g. "1:3 2:4" — source 1 → copier 3, source 2 → copier 4

while true; do
    for f in /tmp/cheat-buster-sim/share/*; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")
        echo "$SEEN_FILES" | grep -qF "$fname" && continue

        sender=$(echo "$fname" | sed 's/student\([0-9]*\)_.*/\1/')
        original=$(echo "$fname" | sed "s/student${sender}_//")

        # Find copier paired with this sender
        target=$(echo "$COPIER_MAP" | tr ' ' '\n' | grep "^${sender}:" | cut -d: -f2)

        if [ -n "$target" ]; then
            cp "$f" "/tmp/cheat-buster-sim/inbox/student${target}/${original}"
            echo "$(date -u +%H:%M:%S) Relayed $fname → student${target}/${original}"
            SEEN_FILES="$SEEN_FILES $fname"
        fi
    done

    # Check if all agents done (use TaskOutput block:false for each task ID)
    # When all done: break

    sleep 3
done
```

Between iterations, check TaskOutput with `block: false` for each agent task ID. Exit loop when all agents have finished.

---

## Phase 5 — Analysis + Verify

When all agents complete:

**1. Show file listing per student:**
```bash
for i in $(seq 1 {TOTAL}); do
    echo "=== student${i} ===" && ls -la {BASE_DIR}/student${i}/
done
```

**2. Show relay log:**
```bash
cat /tmp/cheat-buster-sim/relayed.log
```

**3. Trigger analysis on the server:**
```bash
# Use teacher cookie from Phase 0
curl -s -X POST "{SERVER_URL}/exams/{EXAM_ID}/regenerate" \
  -b /tmp/cb-teacher-cookie.txt \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('Analysis done:', d)"
```

**4. Fetch and display similarity scores:**
```bash
curl -s "{SERVER_URL}/reports/{EXAM_ID}" \
  -H "Authorization: Bearer ${TEACHER_TOKEN}" \
  | python3 - << 'PYEOF'
import sys, json
data = json.load(sys.stdin)
edges = data.get('group', {}).get('edges', [])

# Load email map from individual results (student_id → email not in report, use student_id)
print(f"\n{'='*60}")
print(f"SIMILARITY SCORES ({len(edges)} pairs)")
print(f"{'='*60}")
print(f"{'Student A':>6}  {'Student B':>6}  {'Score M':>7}  {'Cosine':>7}  {'Struct':>7}  {'Seq':>7}")
print("-"*60)

edges_sorted = sorted(edges, key=lambda e: e['score'], reverse=True)
for e in edges_sorted:
    d = e.get('details', {})
    print(f"{e['student_a']:>8}  {e['student_b']:>8}  "
          f"{e['score']:>7.4f}  {d.get('cosine',0):>7.4f}  "
          f"{d.get('structural',0):>7.4f}  {d.get('sequential',0):>7.4f}")

print(f"\nExpected cheater pairs (source→copier):")
PYEOF
```

Print the expected cheater pairs (source student_id → copier student_id) so the user can see if scores match expectations.

**5. Cleanup:**
```bash
rm -rf /tmp/cheat-buster-sim/
rm -f /tmp/cb_post_*.py /tmp/cb-teacher-cookie.txt
# Leave {BASE_DIR} intact for manual inspection
```

---

## Constraints and rules

- **Never** write more than 1 line per bash command when creating files — always use `wl()` for own code, `wl_fast()` for copies.
- All programs 12–25 lines.
- **Use multi-char variable names** (`count`, `result`, `index`, `max_val`) — single-char names (`i`, `n`, `s`) are filtered by the AST analysis and will produce zero structural similarity.
- Source students write SHARED_POOL (bubble_sort.py, fibonacci.py, count_vowels.py). Honest students write SOLO_POOL only. This guarantees file overlap only between cheater pairs.
- Copied files use the **same filename** by default (same_mode) so cosine + structural detection works. Use `renamed` mode only to test TASK-041 cross-file detection (not yet implemented).
- Relay runs every **3 seconds** — this keeps copier commits within the 300-second sequential detection window.
- All student agents use `model: haiku`.
- If a student token is empty (auth failed), abort and tell user to check that the exam_id exists and the exam has sufficient duration (≥ 60 minutes).
