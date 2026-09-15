# Transit Anchor — crowded-transit wrist companion

> Low-profile dorsal-wrist private haptic companion with bounded routine intervention and a local stop path.

## Design challenge

在移动、通勤和任务切换中提供低打扰、可撤销的情境化介入

## Current design direction

- **Candidate revision:** `scaffold-r1-1.iter-db6118ebbd16.r1`
- **Model revision:** `scaffold-r1-1.model.r3`
- **Form:** wearable — low-profile rounded dorsal-wrist pod with no snagging protrusions
- **Placement:** dorsal wrist, centered proximal to wrist crease
- **Attachment:** broad vented strap with keyed clasp and intentional quick release
- **Contact / mass intent:** broad compliant underside, avoiding wrist prominences / centered over wrist/forearm axis with no distal overhang
- **Routine feedback:** private haptic, short bounded pulse; bounded pulse at a safe task boundary
- **Visible state:** wearer-facing state edge shows active/sensing state without content
- **Local stop:** guarded recessed one-handed press-hold; no response terminates routine event

## Product and graphic evolution

### 1. Baseline structured concept

- **Status:** `confirmed`
- A wearable in the 未来可穿戴 AI 伴行助手 category that helps during 城市通勤、步行和任务切换中的连续使用 while preserving a clear user stop path.
- Candidate: `scaffold-r1-1.r1-992bc9ab26df`
- Model: `scaffold-r1-1.model.r1`
- **Evidence boundary:** Structured design facts only; no physical comfort, scale or outcome is validated.

### 2. Parameterized design revision

- **Status:** `confirmed`
- Applied: wearable.attachment_strategy, wearable.body_placement, control.cancel_action, feedback.modality
- Parent: `scaffold-r1-1.r1-992bc9ab26df`
- Candidate: `scaffold-r1-1.iter-db6118ebbd16.r1`
- Model: `scaffold-r1-1.model.r3`
- Patches: `ergonomic-broad-strap.r1`, `ergonomic-wrist-placement.r1`, `guarded-stop-control.r1`, `private-haptic-routine.r1`
- **Evidence boundary:** Patch adoption describes a structured design revision, not verified physical performance.

### 3. Derived Blender blockout

- **Status:** `draft`
- Review image and geometry exported for form, control-access and placement discussion.
- Parent model: `scaffold-r1-1.model.r1`
- Candidate: `scaffold-r1-1.iter-db6118ebbd16.r1`
- Model: `scaffold-r1-1.model.r3`
- Patches: `ergonomic-wrist-placement.r1`, `ergonomic-broad-strap.r1`, `private-haptic-routine.r1`, `guarded-stop-control.r1`
- Assets:
  - `output/experience/transit-anchor-portfolio-demo/blender/design-tool-request-cb9d6dcfc737-6vmcfjb9/render-2d.png` (local derived asset; not committed)
  - `output/experience/transit-anchor-portfolio-demo/blender/design-tool-request-cb9d6dcfc737-6vmcfjb9/design.blend` (local derived asset; not committed)
  - `output/experience/transit-anchor-portfolio-demo/blender/design-tool-request-cb9d6dcfc737-6vmcfjb9/design.glb` (local derived asset; not committed)
- **Evidence boundary:** Derived assets are review material only; the blockout does not validate dimensions, fit, comfort, materials or movement stability.

### 4. Prototype validation protocol

- **Status:** `planned`
- A pre-prototype measurement plan for fit, control, detectability, contact and privacy boundaries.
- Candidate: `scaffold-r1-1.iter-db6118ebbd16.r1`
- Model: `scaffold-r1-1.model.r3`
- **Evidence boundary:** Planned measures are not evidence until a protocol is run and reviewed.

## Scenario state machine

**Scenario:** Crowded transit routine intervention (`crowded-transit-transfer`)

| From | Event / guard | Action | To |
| --- | --- | --- | --- |
| monitoring | hazard_phase_entered; doors, stairs, crossing or high-motion transit is declared | do not present routine content | suppressed |
| suppressed | routine_event_arrives; hazard remains declared | record only minimal event metadata and defer | deferred |
| deferred | safe_boundary_declared; hazard no longer declared and intervention permission remains valid | offer one private bounded signal | private_signal |
| private_signal | signal_completed; routine event | open one bounded response window | awaiting_response |
| awaiting_response | reject_or_cancel; guarded control is reachable | stop event and suppress ordinary re-intervention in scope | terminated |
| awaiting_response | no_response_timeout; response window expires | terminate with no implicit consent and no escalation | terminated |
| awaiting_response | context_corrected; user indicates an incorrect context | stop current event and require new permission decision | safe_boundary_review |
| terminated | new_independent_event; new permission and no active hazard | return to monitoring | monitoring |

### Control boundaries

- Routine intervention never uses public audio for private content.
- No-response ends a routine event; it never grants consent.
- Hazard, pose, route and movement state are context inputs, not evidence of intent or emotion.
- Rejection and correction do not trigger ordinary escalation.
- When hands are unavailable, the system relies on suppression or timeout rather than pretending a physical control is reachable.

### Not claimed by this state machine

- critical-event policy
- emotion or health inference
- measured haptic detectability
- production sensor classifier accuracy

## Prototype validation protocol

**Objective:** Test whether the declared wrist form preserves bounded control and low interruption under plausible crowded-transit movement conditions.

**Participants and context:** Consented adult participants perform controlled standing-transit, handrail, bag-carrying, sleeve and walking tasks; no road-crossing or live transit hazard is required for the first protocol.

| Test question | Conditions | Metric | Evidence boundary |
| --- | --- | --- | --- |
| Does the device slip or rotate under declared movements? | standing vibration proxy; handrail grip; bag carry; sleeve and sweat proxy | displacement and rotation relative to initial marked position | Pre-register a tolerable displacement/rotation threshold before data collection; do not derive it from the render. |
| Does gripping or incidental contact trigger guarded controls? | handrail grip; bag handle grip; body contact proxy | false activations per task and per controlled exposure time | Compare against a pre-registered maximum false-activation rate. |
| Can a reachable user perform reject/stop without visual search? | one hand free; intermittent hand availability; attention-divided task | completion rate, completion time and erroneous activation | Pre-register success and time bounds; hands-unavailable trials test suppression/timeout policy rather than control reachability. |
| Is the private haptic pattern detectable without demanding visual attention? | vibration proxy; walking; sleeve coverage; sweat proxy | hit rate, false alarm rate and response time | Pre-register a detection criterion and distinguish non-detection from rejection. |
| Does the declared contact geometry create observable pressure, heat or irritation signals in the short protocol? | short wear; movement task; sleeve coverage | participant-reported discomfort plus measured surface/skin-adjacent temperature where safely instrumented | Exploratory safety screen only until duration, measurement method and threshold are pre-registered. |
| Can bystanders infer private content from routine feedback? | nearby observer; private haptic; wearer-facing state edge | observer identification of state versus private content | Pre-register acceptable content-identification rate; state-legibility and content leakage are analyzed separately. |

### Stopping conditions

- Stop an individual session on discomfort, skin irritation, distress or a participant request.
- Do not test the routine intervention flow in live road-crossing, vehicle-door or stair hazards in this first protocol.
- Pause the protocol if a control failure removes the local stop path.

### Outcomes not claimed

- long-term comfort
- medical safety
- ingress protection
- manufacturing durability
- real-world crash or injury reduction
- user intent, emotion or consent inference

---

_Portfolio boundary: This portfolio projection separates declared design changes, derived graphics and planned validation. It never presents Blender output or scenario context as proof of user outcomes, comfort, consent, engineering readiness or physical performance._
