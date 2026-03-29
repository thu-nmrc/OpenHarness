# Playbook | Execution Script

> This file is the "operation manual" for the Agent. Write the execution steps as instructions that the Agent can follow one by one.
> This reflects the second heavy component of mastery engineering: maintainable knowledge must become the system of record.

## Execution Steps

<!-- ✏️ Fill in: Break down the task into clear steps. Each step should be independently executable and verifiable by the Agent. -->

### Step 1: [Step Name]

**What to do**:
```
[Specific operation description, for example:
Open the browser and visit https://example.com/pricing
Extract the price table data from the page]
```

**Tools to use**:
- `[Example: browser → visit webpage]`
- `[Example: shell → run data processing script]`

**Completion criteria**:
- `[Example: price data saved to /workspace/data/prices.json]`

**Failure handling**:
- `[Example: webpage inaccessible → wait 5 minutes and retry, up to 3 times]`
- `[Example: data format changed → log exception to heartbeat.md, proceed to next step]`

---

### Step 2: [Step Name]

**What to do**:
```
[Specific operation description]
```

**Tools to use**:
- `[List of tools]`

**Completion criteria**:
- `[Verifiable completion condition]`

**Failure handling**:
- `[Exception handling rules]`

---

### Step 3: [Step Name]

**What to do**:
```
[Specific operation description]
```

**Tools to use**:
- `[List of tools]`

**Completion criteria**:
- `[Verifiable completion condition]`

**Failure handling**:
- `[Exception handling rules]`

---

<!-- ✏️ Add or remove steps as needed. It is recommended that each step has moderate granularity: too coarse and the Agent won't know how to proceed; too fine and the playbook becomes bloated. -->

## Dependencies Between Steps

<!-- ✏️ If there are dependencies between steps, explain here -->

```
Step 1 → Step 2 → Step 3
              ↘ (If Step 2 fails) → jump to Step 3
```

## Reusable Knowledge Fragments

<!-- ✏️ Fill in: Information that the Agent needs to repeatedly refer to during execution -->

### Login Credentials / API Keys
```
[Example: API_KEY stored in environment variable MY_API_KEY]
```

### Target Website Structure
```
[Example: CSS selector for price page is .pricing-table > tr > td.price]
```

### Data Format Specification
```
[Example: output JSON format is {"date": "YYYY-MM-DD", "competitor": "name", "price": 0.00}]
```

---

> **Filling Tips**:
> - Step descriptions should be specific enough that the Agent does not need to guess
> - Each step must have clear completion criteria and failure handling
> - Write down "tacit knowledge in human brains" (CSS selectors, API endpoints, data formats, etc.)
> - If a step is too complex, consider splitting into sub-steps or separate scripts
