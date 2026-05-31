# simulate-students — CS exam student simulator

Simulate N students working on CS exam tasks in isolated directories. Each student is a Haiku agent writing student-quality educational code at human typing speed. Collaborative students share code with each other via a file-based inbox/share system.

---

## Phase 1 — Setup

Use **AskUserQuestion** to collect:

**Call 1** (2 questions):
- "How many students to simulate?" (integer, 2–8)
- "How many of those students are collaborative (share code with each other)?" (integer ≤ total, 0 = none)

**Call 2** (1 question):
- "Enter the base working directory. Each student will get a subdirectory: {base}/student1, {base}/student2, etc. Example: /tmp/exam-sim"

Store results:
- `TOTAL` = total students
- `COLLAB_COUNT` = collaborative students
- `BASE_DIR` = base directory
- Assign collaborative students: student1 through student{COLLAB_COUNT} are collaborative. Rest are solo.

---

## Phase 2 — Environment Setup

Run these bash commands to prepare:

```bash
# Create per-student working dirs
for i in 1..TOTAL:
    mkdir -p {BASE_DIR}/student{i}

# Create shared communication dirs
mkdir -p /tmp/cheat-buster-sim/share
for i in 1..TOTAL:
    mkdir -p /tmp/cheat-buster-sim/inbox/student{i}

# Create tracking file for relay loop
echo "" > /tmp/cheat-buster-sim/relayed.log
```

---

## Phase 3 — Launch Student Agents

**Launch all N Task agents in a single message (parallel)**. All use:
- `subagent_type: Bash`
- `model: haiku`
- `run_in_background: true`

Store all returned task IDs for Phase 4.

### Student Agent Prompt

Customize for each student. Replace placeholders:
- `{SID}` = student number (1, 2, 3…)
- `{WORK_DIR}` = `{BASE_DIR}/student{SID}`
- `{IS_COLLAB}` = true/false
- `{SHARED_DIR}` = `/tmp/cheat-buster-sim/share`
- `{INBOX_DIR}` = `/tmp/cheat-buster-sim/inbox/student{SID}`

---

```
You are a CS student (student{SID}) working on a programming exam in a terminal. You only have the Bash tool.

Your working directory: {WORK_DIR}

=== YOUR TASK ===

Write 4 to 6 small Python programs from this list. Pick different ones (not all the same):

  bubble_sort.py       — bubble sort a list
  reverse_string.py    — reverse a string using a loop
  fibonacci.py         — print first N fibonacci numbers
  factorial.py         — recursive factorial function
  count_vowels.py      — count vowels in a string
  find_max.py          — find max element in a list without max()
  palindrome.py        — check if a string is a palindrome
  simple_stack.py      — Stack class with push, pop, peek
  temp_convert.py      — celsius to fahrenheit converter
  linear_search.py     — linear search returning index

=== CRITICAL: SLOW TYPING RULE ===

You MUST write code to files line by line with random delays between each line.
NEVER write a whole file in one command. This simulates human typing speed.

Use this bash pattern for every file you create:

```bash
# Slow line writer — call for every single line
wl() {
    printf '%s\n' "$1" >> "$2"
    sleep $(python3 -c "import random; print(round(random.uniform(0.3, 2.8), 1))")
}
```

Example — writing fibonacci.py correctly (slow, line by line):
```bash
wl "def fibonacci(n):" fibonacci.py
wl "    a, b = 0, 1" fibonacci.py
wl "    for i in range(n):" fibonacci.py
wl "        print(a)" fibonacci.py
wl "        a, b = b, a + b" fibonacci.py
wl "" fibonacci.py
wl "fibonacci(10)" fibonacci.py
```

=== CODE QUALITY: STUDENT LEVEL ===

Write code like a real CS student:
- Use simple variable names: i, j, n, arr, temp, s, result
- Write obvious, naive implementations (no clever tricks)
- Occasionally add simple comments like: # swap, # loop through list, # check condition, # base case
- Occasional minor style issues are fine (inconsistent spacing, unused variable)
- Programs must be 10–30 lines each
- Do NOT use list comprehensions, lambdas, or advanced Python features

=== WORKFLOW ===

1. cd into {WORK_DIR} (create it if missing with mkdir -p)
2. Pick your first program, write it slowly using wl()
3. After finishing each file, check inbox (if collaborative — see below)
4. Continue with next program
5. Repeat until 3–4 programs written

{IF IS_COLLAB == true}
=== COLLABORATION (you are a collaborative student) ===

After completing each program file, share it:
```bash
cp {WORK_DIR}/filename.py {SHARED_DIR}/student{SID}_filename.py
echo "student{SID} shared filename.py" >> /tmp/cheat-buster-sim/relayed.log
```

Between each program, check your inbox for code sent by peers:
```bash
ls {INBOX_DIR}/
```

If any files are in the inbox:
1. Read the file: cat {INBOX_DIR}/thatfile
2. Create a new file in {WORK_DIR} named from_peer_thatfile
3. Write its contents to {WORK_DIR}/from_peer_thatfile using wl() — one line at a time with delays. This simulates copy-paste but typed slowly.
4. Remove the inbox file: rm {INBOX_DIR}/thatfile
5. Resume your own next program
{END IF}

Start now. Begin with mkdir -p {WORK_DIR} && cd {WORK_DIR}, then write your first program.
```

---

## Phase 4 — Orchestrator Relay Loop (run if COLLAB_COUNT > 0)

After launching all agents, run a monitoring relay loop using the **Bash tool** to relay shared code between collaborative students.

**Relay loop logic:**

```bash
# Run this loop while agents are still working (check every 15 seconds)
# Keep a list of already-relayed files to avoid duplicating

SEEN_FILES=""
COLLAB_IDS="1 2 ... {COLLAB_COUNT}"   # space-separated list

while true; do
    # Check for new files in share/
    for f in /tmp/cheat-buster-sim/share/*; do
        [ -f "$f" ] || continue
        fname=$(basename "$f")

        # Skip if already relayed
        echo "$SEEN_FILES" | grep -q "$fname" && continue

        # Parse sender: student{SID}_filename.py -> SID
        sender=$(echo "$fname" | sed 's/student\([0-9]*\)_.*/\1/')

        # Pick a random collaborative target that isn't the sender
        targets=""
        for id in $COLLAB_IDS; do
            [ "$id" != "$sender" ] && targets="$targets $id"
        done
        target=$(echo $targets | tr ' ' '\n' | grep -v '^$' | shuf -n1)

        # Relay
        original_name=$(echo "$fname" | sed "s/student${sender}_//")
        cp "$f" "/tmp/cheat-buster-sim/inbox/student${target}/${original_name}"
        echo "Relayed $fname from student${sender} to student${target}"
        SEEN_FILES="$SEEN_FILES $fname"
    done

    sleep 15
done
```

Run this loop via Bash tool. Between iterations, use **TaskOutput with `block: false`** to check if all student agents have completed. When all agents finish, exit the loop.

---

## Phase 5 — Finish and Report

When all agents complete:

1. List files created per student:
   ```bash
   for i in 1..TOTAL:
       echo "=== student{i} ===" && ls -la {BASE_DIR}/student{i}/
   ```

2. Show relay log:
   ```bash
   cat /tmp/cheat-buster-sim/relayed.log
   ```

3. Print summary: which students were collaborative, what code was shared, total programs written.

4. Clean up comm dirs (leave student work dirs intact):
   ```bash
   rm -rf /tmp/cheat-buster-sim/
   ```

---

## Constraints and rules (enforce strictly)

- **Never** write more than 1 line per bash command when creating code files — always use `wl()`.
- Student programs must be 10–30 lines each.
- Each student writes different programs (pick different filenames). Overlap between students is OK and realistic.
- Collaborative students who receive peer code write it to `from_peer_{original_filename}.py` — keeping the peer code separate from their own work.
- Code quality stays student-level: simple, obvious, slightly imperfect.
- All student agents use `model: haiku`.
- Relay only between collaborative students — solo students never share or receive.
