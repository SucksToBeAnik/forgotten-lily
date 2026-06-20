# Forgotten Lily
## Full Project Plan — HuggingFace Build Small Hackathon
### Category: Thousand Token Wood

---

## 1. What This Is

**Forgotten Lily** is a narrative mystery game disguised as a conversation.

The player sits across from a girl named Lily. She has been in an accident. She cannot speak in words anymore — only in tones. Soft, strange sounds that carry feeling without language. The player is a detective. Their job is to understand what happened to her.

Over the course of the game, the player learns Lily's tonal language — slowly, the way you learn someone's silences. They unlock fragments of her life through notes that appear like evidence on a board. They build a picture of who she was.

Then, near the end, something stops making sense. A note is dated wrong. A person she mentioned doesn't exist in the hospital records. Her tones for "I am here" and "yes" are the same glyph — and the player realizes, too late, that they've been reading one as the other.

Lily died at the scene of the accident. She was never in the hospital room. The detective has been alone the entire time.

The game ends when Lily speaks — once, in a real voice — one sentence she needed someone to hear. Then silence.

---

## 2. Prize Targeting

| Prize | Requirement | Our Qualification |
|-------|-------------|-------------------|
| Main — Thousand Token Wood | Delightful, AI-load-bearing, original, polished | Core concept |
| NVIDIA (2× RTX 5080) | Use a Nemotron model meaningfully | Nemotron-Mini-4B as silent semantic scorer |
| OpenBMB ($10,000 pool) | Use MiniCPM series model | MiniCPM-o 4.5 for audio input |
| llama.cpp badge | Run inference via llama.cpp runtime | Gemma 4 12B via llama-cpp-python |
| Off-brand UI badge | Custom Gradio UI, unrecognizable from default | Full custom HTML/Tailwind/JS via gr.Server |
| Off the Grid badge | No cloud inference APIs | 100% local inference on Modal GPUs |
| Modal credits | Use Modal for compute | All inference on Modal |
| Sharing is Caring | Log agent traces to HF dataset | Structured trace logger, privacy-preserving |
| Field Notes | Blog post / README writeup | Detailed Space README written as narrative |

**Total parameter budget:** Gemma 4 12B + Nemotron-Mini 4B + MiniCPM-o 4.5 (~8B) = ~24B of the 32B limit.

---

## 3. Lily — Character Profile

**Full name:** Lily Anne
**Age:** 19
**University:** Second-year CS undergraduate, full scholarship
**From:** A small coastal town. First in her family to go to university.

Lily is the kind of person who fills every margin. Her CS assignments have scraps of melody in the corners. Her manuscript books have snippets of code tucked between the staves. She can't fully separate the two things she loves — she thinks of programs the way she thinks of compositions, as things with rhythm and weight.

A piece of hers — "A Held Breath," generative code woven with melody she writes by hand — is a finalist for an international student composition prize. She's been re-reading the email, saving the news to tell her parents in person.

> NOTE (canon as of the story pivot — see todo.md / memory `design-pivot-musician`): the spine of Lily's story is now her UNFULFILLED DREAMS, not the relationship. She wants to become a composer, see the world, and stand at **Mount Fuji** at sunrise with **both** her divorced parents, together for once, after she graduates. R is a faint, gentle, recently-ended thread — not the center. Player-facing evidence is written in PRESENT tense and never reveals the twist; only the final reveal (N10) does. The sections below predate the pivot and are kept for design history; where they conflict, this note and the data files win.

She was in her second year when everything happened. She was also in the middle of a relationship that was falling apart — someone named R. Not a bad person. Just two people who wanted different things and didn't know how to say it. Their last real conversation was at 11:43pm, three days before the accident. It did not go well.

The accident was not dramatic. It was a Tuesday. She was walking home from the library. The details are in the police report — the one that surfaces at the very end of the game, the one that changes everything.

**What Lily wants, more than anything** (pivot canon): the life still ahead of her — to become a composer, to see the whole world, and above all to stand at Mount Fuji at sunrise with both her parents, together for once, after she graduates. She grew up shuttled between two homes and learned to go quiet when things got hard; the trip is her dream of finally bringing them into one frame. R is a quiet, kind, recently-ended thread that weighs on her but is not the center.

The accident night (canon): that morning the gentle breakup with R; that evening her father comes to collect her from her mother's and the two argue in the hall; already raw, she leaves on foot into the dark toward the crossing. What keeps her is everything she still wants and never got to do.

---

## 4. Full Story — Scene by Scene

### 4.1 The Opening

The player opens the game and sees a sparse, warm screen. A case file header. A name: **Lily Anne.** An incident number. A date.

Below that, a single line of detective's notes typed out slowly, as if being written in real time:

> *Lily has forgotten how to speak. She only speaks in melodies now. Keep conversing with Lily to understand what really happened to her.*

The first conversation begins. The UI is warm — muted cream, soft amber. The room feels like late afternoon light through hospital blinds. A gentle ambient piano plays, barely audible.

The player types their first message to Lily. Something simple — hello, or are you okay, or what happened. Lily responds in tones. Two or three glyphs. They play as soft sounds, one after the other. The music ducks to silence while they play, then returns.

The player has no idea what the tones mean. That is the game.

### 4.2 Act I — The Room (Turns 1–30, Tones 1–8 Active)

The detective is building a picture. Lily is responsive. Her tones feel warm — the player learns quickly that some tones feel positive, some feel like questions, some feel like reaching. She is clearly trying to communicate. She is clearly glad someone came.

As the player asks questions — about her life, her interests, what she loves — notes begin appearing on the evidence board beside the conversation. A page of sheet music. An award email. A screenshot of a text thread. The player pieces together who Lily is from these fragments while simultaneously trying to decode her language from context.

**The emotional register of Act I:** Hope. Lily feels present, curious, almost playful. The detective is learning. Progress feels possible. The relationship between detective and Lily feels like it is building toward something.

**What the player learns in Act I:**
- Lily was a CS student and musician — brilliant, driven, warm
- She had a complicated relationship with someone named R
- She won an international award she apparently doesn't know about
- She loved her work, her manuscript books, the feeling of making things
- She communicates in tones that have consistent patterns — learnable

**Act I ends when** the player has seen all 8 active tones at least twice and has made at least 5 lexicon entries.

### 4.3 Act II — The Cracks (Turns 31–60, Tones 9–18 Active)

Something is off. Not dramatically — just a few degrees wrong.

A note appears: the hospital intake form. The date field is smudged. The status field is redacted with a thick black bar. The player may notice. They may not.

Lily starts using a tone the player hasn't seen before — one that seems to collapse "now" and "before" into the same glyph, as if time isn't quite linear for her. She uses tones referring to the past more than the present. When the player asks what today is like, she responds with memories.

A nurse that Lily's tones seemed to reference — the player, if they ask about who else is around — doesn't appear in any hospital records the detective can access. The name doesn't match. The shift log doesn't match.

The UI shifts almost imperceptibly. The warm cream begins cooling. Amber becomes gray-amber. The shadows are longer. The ambient music shifts half a key lower, slower.

**The emotional register of Act II:** Unease. The player feels it before they can name it. Something is wrong with this room. Something is wrong with the timeline. But Lily is still here. She still responds. That must mean she's alive. Right?

**What the player learns in Act II:**
- Inconsistencies in dates and hospital records
- Lily's sense of time is fractured — past and present blur
- R appears more in her tones — there's something unfinished there
- The night of the accident is something she circles but never lands on directly
- 6 more tones are now active — language is getting richer, more nuanced

**Act II ends when** the player has seen 18 of 27 tones and unlocked note N07 (her travel fund + new passport).

### 4.4 Act III — The Truth (Turns 61–90, All 24 Tones Active)

The final 6 tones activate. The vocabulary is complete. The player now has the full language.

And with the full language, they can read everything Lily has said — including things she said in Act I that the player couldn't decode yet. Players who go back and re-read the early conversation will find she was telling them the truth the whole time. She never lied. The words were just missing.

The evidence board gets one final note. It appears differently from the others — not pinned, but placed flat in the center of the board, as if someone just set it down. It is a police report. The incident date is the same as the hospital admission date. The status field reads: *deceased at the scene. No other parties involved. Personal effects catalogued and returned to family.*

She was never admitted. There was no hospital room. There was no nurse. There was no survivor.

The UI becomes cold. Near-monochrome. The ambient music is gone — it stopped at some point in Act III and the player may not have noticed exactly when.

**The emotional register of Act III:** Quiet devastation. The player is not surprised by the reveal so much as confirmed in what they already half-knew. The game earns the twist because it was honest the entire time.

**Lily's final tone sequence:** She sends one last response. All seven tones together, in order. By now the player can read every one of them. They say, in Lily's language:

> *I / let go / remember — you / happy / him / not / the end*

It means: she can go now. But first.

### 4.5 The Ending

After the final tone sequence plays — each tone one at a time, 1.5 seconds apart — there is silence.

The screen brightens slowly to white over five seconds.

Then a voice. Soft, young, slightly hesitant — Kokoro TTS rendering a 19-year-old's voice.

> **"I just wanted to see the world — all three of us, watching the sun come up."**
>
> *(pivot canon; the old line — "I just wanted someone to know it wasn't his fault." — belonged to the relationship-centric version.)*

Eight seconds of silence.

Then, slowly, a simple screen appears. Lily's name. Her dates. Below that: the player's complete lexicon — every tone they decoded, every word they assigned, every meaning they found — rendered as a quiet list. It is the player's portrait of Lily. They built it without knowing that's what they were doing.

No score. No replay button. No "thanks for playing." Just her name, her dates, and what the player learned of her language.

The game is over.

---

## 5. Character: R

R is never directly named beyond the initial. His full name is Rohan. He was Lily's boyfriend for eight months.

He is not the villain of this story. He was kind to her. He just couldn't follow her into the parts of herself she was still figuring out — her ambition, the way she disappeared into work for days, the way she cared more about making things than about being comfortable. He wanted a relationship that was more present. She wasn't ready to be.

Their last text thread is one of the first notes the player unlocks. Reading it, the player might initially think R was cold or difficult. Re-reading it after the reveal — knowing Lily had been pulling away for weeks, knowing she had been trying to figure out how to say something important to him — the thread reads completely differently.

The game is, in part, about that re-reading. About how much context changes meaning. Which is also what the tone mechanics are about.

---

## 6. The Tone System

### 6.1 Core Philosophy

**One meaning per tone. Always.**

The difficulty is not disambiguation — it is discovery. The player must figure out what each tone means through repeated observation across different contexts. Once they know, they know. The revelation is in the pattern, not the interpretation.

### 6.2 The 24-Tone Vocabulary

Organized into 6 categories of 4 tones each. Categories help the player recognize families — once they learn one tone in a category, they can make educated guesses about the others.

**Category A — Self** *(Lily referring to herself or her inner state)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| ◈ | I / me | Whenever Lily is the subject |
| ◉ | feel / sense | Describing an internal experience |
| ◇ | remember | Reaching into the past |
| ▣ | forget / lost | Something gone, unreachable |

**Category B — Other** *(Lily referring to people)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| △ | you | Addressing the detective directly |
| ▽ | him / R | Only ever used for one person |
| ◫ | us / together | Shared experience |
| ◻ | the world / everyone | Abstract others |

**Category C — Time** *(Lily's fractured relationship with time)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| ∿ | now / this moment | Present tense |
| ⌒ | before / the past | Memories, what was |
| ↝ | after / what comes | Future or consequence |
| ≋ | always / never changes | Something permanent |

**Category D — Emotion** *(What Lily is feeling)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| ♭ | happy / light | Joy, warmth, ease |
| ♮ | sad / heavy | Grief, weight, ache |
| ♯ | afraid | Fear, uncertainty |
| ≈ | love / care | Affection, closeness |

**Category E — Action** *(What happened or is happening)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| → | go / move / happen | Motion, events |
| ← | stay / stop | Stillness, pause, refusal |
| ↑ | want / reach | Desire, aspiration |
| ↓ | fall / let go | Loss, release, surrender |

**Category F — Truth** *(The spare grammar of her language)*
| Glyph | Meaning | When Lily uses it |
|-------|---------|-------------------|
| — | pause / breath | Between thoughts, hesitation |
| ∎ | yes / true | Affirmation |
| □ | no / not | Negation |
| ∅ | nothing / the end | Absence, finality |

### 6.3 Tone Unlock Progression

Lily only uses tones that are "active" for the current act. This prevents overwhelming the player:

- **Act I start:** 8 tones active (◈ ◉ △ ♭ ♮ ∎ □ —)
- **Act I → II transition:** 4 more activate (◇ ▽ ⌒ ≈)
- **Act II:** 6 more activate (▣ ◫ ∿ ♯ → ←)
- **Act III:** Final 6 activate (◻ ↝ ≋ ↑ ↓ ∅)

### 6.4 Tone Audio Character

All 24 tones are synthesized procedurally at app startup using `scipy` and `numpy`. No neural audio model is used for tone generation — each tone is a designed sound, reproducible and precise.

Category A tones (Self) are warm, sustained hums in the mid-low frequency range.
Category B tones (Other) are slightly cooler, more directional.
Category C tones (Time) have rhythmic or envelope-based character — fade-ins, pulses.
Category D tones (Emotion) are the most expressive — minor intervals for sadness, brightness for joy.
Category E tones (Action) are shorter, more percussive — they feel like motion.
Category F tones (Truth) are the sparsest — the pause tone is near-silence, the end tone is a sub-frequency barely audible.

### 6.5 Background Music

A soft ambient piano loop (CC0 licensed, sourced from Freesound.org) plays throughout the game. The music is the "alive" world. When Lily speaks — when tones play — the music ducks to silence. When tones finish, it fades back.

This contrast is the game's most important emotional design decision. Every time Lily responds, the world goes quiet for her.

The music shifts tone slightly between acts — same loop, slightly different equalization. Warmer in Act I, cooler and slower in Act II, gone before the player notices in Act III.

In the ending sequence, the music does not return after Lily's final tones. The silence before her spoken sentence is total.

---

## 7. The Notes System

### 7.1 What Notes Are

Notes are physical artifacts from Lily's life. They are not narration. They are not summaries. They are the things that were left behind — screenshots, scans, forms, photographs — that the detective has gathered.

They appear on the evidence board one by one as the player progresses. Finding a new note feels like opening a drawer in someone's room.

### 7.2 Two Ways Notes Unlock

**Threshold unlock:** The player has reached a certain number of decoded tones in their lexicon. Some notes appear automatically as the investigation deepens.

**Conversation unlock:** When the player asks Lily about a relevant topic, Gemma detects the theme and signals the frontend to reveal the corresponding note. Asking about her music unlocks the manuscript. Asking about R unlocks the text thread. The conversation and the evidence board inform each other.

### 7.3 Complete Note Inventory

**N01 — Text thread: Lily & R, 11:43pm**
*Unlocks: 2 tones in lexicon (Act I)*
A screenshot of the last real conversation between Lily and R. The player reads it first as a difficult breakup — R seems cold, Lily seems withdrawn. Later, knowing the full story, the thread reads as two people who cared about each other and ran out of words. Designed to be read twice.

**N02 — Manuscript: an unfinished song, final bar left blank**
*Unlocks: Player asks about music, playing, or creativity (Act I)*
A song in soft pencil on staff paper, almost complete. The melody is rendered with extraordinary care — phrasing, dynamics, the breath-marks where a voice would rise and fall. Then the final bar is completely absent. Not erased. Just never written. When the player sees this in Act I it's a glimpse into Lily's talent. When they see it after the reveal, the unwritten ending means something else entirely.

**N03 — Award email: Composition Prize finalist notification**
*Unlocks: 6 tones in lexicon (Act I)*
The email arrived the week she died. "We are thrilled to inform you..." She never read it. The timestamp is two days after the accident date — a detail the player may not notice until Act III.

**N04 — CS assignment: margin notes in Lily's handwriting**
*Unlocks: Player asks about university or coding (Act I)*
A scan of a printed assignment, covered in her handwriting. Not corrections — thoughts. Scraps of melody in the margins. A note to herself: *"this function feels like a held breath."* Her personality in ink.

**N05 — Photograph: Lily at her desk, laughing**
*Unlocks: 10 tones in lexicon (Act II)*
A candid photograph — someone else took it, she didn't know. She's at her desk in what appears to be her dorm room, laughing at something off-camera. The room is beautiful chaos. Pinned sheets of staff paper. Open textbooks. Three half-empty mugs. This is the note that makes the player love her.

**N06 — Second text thread: R and Lily, two days before**
*Unlocks: Player asks about R, or about the relationship (Act II)*
This thread has almost no words from Lily. R is trying. "Are you okay?" "Can we talk?" "Just tell me what's wrong." Lily sends one-word answers, then goes quiet. The player understands now that she was pulling away. They also understand R had no idea why.

**N07 — Hospital intake form: redacted status field**
*Unlocks: 14 tones in lexicon (Act II)*
Standard hospital form. Patient name: Lily Anne. Date of admission: the field is smudged, illegible. Status: covered with a thick black bar. The discharge date reads "N/A." A careful player will flag this. Most players will file it away and keep going.

**N08 — Nurse shift log: the nurse doesn't exist**
*Unlocks: Player asks about hospital staff or who else is around (Act II)*
A photocopy of the ward's shift log for the relevant week. The nurse Lily's tones seemed to reference — when a player asks who is with her — does not appear anywhere on this document. The name doesn't match any staff on record.

**N09 — Journal page: the night she was going to tell R something**
*Unlocks: 18 tones in lexicon (Act III)*
A torn page from a small notebook. Lily's handwriting, more hurried than usual. She was going to meet R that night. She had finally figured out what she wanted to say — that she needed space, that it wasn't about him, that she loved him in a way that didn't fit the shape their relationship had taken. She was going to say this on the walk home from the library. She wrote it out first so she could get the words right.

She never got there.

**N10 — Police report: case closed**
*Unlocks: All 27 tones seen at least once (Act III)*
This note appears differently from all others — placed flat in the center of the evidence board, not pinned. The incident date matches the hospital admission date on N07. Status: *deceased at the scene. No other parties involved. Personal effects catalogued and returned to family.*

She died on the walk home. The accident was minor by road standards. It was enough.

---

## 8. Input Design

### 8.1 Character Limit

Player inputs are capped at **280 characters**. This is enforced client-side with a live counter. The limit serves two purposes: it keeps the conversation natural and prevents players from writing essays that defeat the investigative tone of the interaction.

A detective's questions are short. Precise. That's what the character limit creates.

### 8.2 Harmful Input Handling

Moderation is handled by Nemotron-Mini-4B as part of its dual role. If a player's input is classified as harmful or inappropriate, the game never breaks character. There are no error messages. No system alerts.

Lily simply goes quiet. The ∅ tone plays — the one that means "nothing / the end." A small line appears beneath the chat, in the detective's journal style: *She doesn't respond to that.*

Then the conversation continues. The game absorbs the moment without rupturing the fiction.

### 8.3 Off-Topic Inputs

If the player sends something genuinely irrelevant — unrelated to Lily, to the investigation, to anything the game is about — Lily responds with ◇ — (remember / pause). She turns inward. It reads as her withdrawing slightly. The detective's journal notes: *She seems to have drifted somewhere.*

This is never punishing. It is in character. Lily is not a chatbot — she does not respond to everything with equal attention.

---

## 9. The Lexicon

The lexicon is the player's ongoing record of what they believe each tone means. It is a bottom-panel drawer that slides up from the edge of the screen — always accessible but never intrusive.

For each tone the player has encountered, they see:
- The glyph, large
- A text field for their current best guess at the meaning
- A confidence bar — colored, not numbered — that shifts based on Nemotron's silent semantic scoring

The confidence bar has four states:
- **Red:** The guess does not match the contexts where this tone has appeared
- **Amber:** Possibly right — fits some contexts but not others
- **Teal:** Likely right — consistent across most appearances
- **Green:** Very confident — the guess fits every context

Players never see numbers. They see the bar shift over time. A bar that was amber going green across three conversations means they've found it. No confirmation is ever given explicitly — the confidence bar is Nemotron's silent verdict expressed as color.

Tones the player hasn't encountered yet show as grayed-out question marks. The player can see how many remain. It creates a collection mechanic without making it feel like a checklist.

---

## 10. Technical Architecture

### 10.1 System Stack Overview

**Frontend:** Custom HTML + Tailwind CSS + Vanilla JavaScript, served via `gr.Server`. The Gradio app is unrecognizable as Gradio. It looks like a designed game.

**Backend:** Gradio `gr.Server` running on a HuggingFace Space (CPU Basic, free tier). It serves the static frontend and routes API calls to Modal.

**Compute:** Modal serverless GPU endpoints. All inference runs here. The HF Space itself never runs a model.

**Models:**
- **Gemma 4 12B** (GGUF Q4_K_M, via `llama-cpp-python`) — Lily's core reasoning and tone generation
- **Nemotron-Mini 4B** (via `transformers`) — input moderation + lexicon confidence scoring
- **MiniCPM-o 4.5** (via `transformers`) — optional audio input processing, earns OpenBMB prize
- **Kokoro TTS** (82M params, not counted toward 32B limit) — Lily's single spoken sentence at the end
- **Scipy/Numpy tone synthesis** — all 24 tone WAV files, generated procedurally at startup

**Total parameter count:** ~24B (under the 32B limit)

### 10.2 Why gr.Server + Tailwind (Not Standard Gradio)

Standard Gradio components cannot achieve:
- An evidence board with rotated kraft-paper note cards
- Tone chips with hover lexicon states
- Ambient music with Web Audio API ducking behavior
- Act-based color temperature transitions
- The final white-screen ending sequence

`gr.Server` serves the custom frontend as static files while Gradio handles backend routing. The HF Space registers as a Gradio app for eligibility. The player sees a designed game.

Tailwind CSS is used for all styling — utility-first, no custom CSS framework needed. The design system is implemented through Tailwind's configuration (custom colors, fonts, spacing) rather than bespoke stylesheets.

### 10.3 UI Layout

Three-panel layout on desktop:

```
┌─────────────────────────────────────────────────┐
│  FORGOTTEN LILY                    [act] [lexicon]│  ← header
├──────────────────┬──────────────────────────────┤
│                  │                              │
│  EVIDENCE BOARD  │   CONVERSATION               │
│  (notes panel)   │                              │
│                  │   Detective: ...             │
│  [note card]     │                              │
│  [note card]     │   Lily: ◈ — ◉ ♮             │
│                  │                              │
│  New notes       │   ┌──────────────────────┐   │
│  appear here     │   │ Type your question   │   │
│  as investigation│   └──────────────────────┘   │
│  deepens         │   [send]  [mic] 280 chars     │
└──────────────────┴──────────────────────────────┘
│  LEXICON DRAWER (slides up on click)             │
└─────────────────────────────────────────────────┘
```

### 10.4 Visual Design Language

**Aesthetic:** Melancholic investigation — like reading someone's diary after they're gone.

**Typography:**
- Display: `Cormorant Garamond` — elegant, emotional, slightly aged
- Mono/UI: `DM Mono` — clinical, detective's notes feel

**Color temperature shifts by act (implemented as Tailwind CSS variable transitions):**
- Act I: Warm cream, dusty rose, amber accents — feels alive
- Act II: Cooling, gray-amber, longer shadows — feels uncertain
- Act III: Near-monochrome, cold — feels like a room after someone has left

**Evidence board aesthetic:**
- Kraft paper card backgrounds
- Subtle rotation per card (seeded random, consistent)
- Red pushpin detail at top of each card
- DM Mono handwriting aesthetic for typed notes
- New notes drop in with a soft pin animation

**Tone chips in chat:**
- Each tone renders as a styled glyph chip, not plain text
- Hover state shows current lexicon guess and confidence
- Click opens the lexicon drawer scrolled to that tone
- Chips in past messages update retroactively when lexicon changes

### 10.5 Modal Deployment

Models are hosted on Modal with a persistent volume for weights. The HF Space calls Modal via Modal's Python client — no HTTP endpoints, just function stubs.

Two Modal functions:
1. **Main inference** — Gemma 4 12B (A10G GPU) for tone generation
2. **Moderation + scoring** — Nemotron-Mini 4B (T4 GPU, shared endpoint, fast)

MiniCPM-o runs on a separate cold-start endpoint — only invoked when the player uses the optional audio input feature.

Models are downloaded to a Modal Volume on first run and cached. Cold start after first run is fast.

### 10.6 HuggingFace Space Setup

- **SDK:** Gradio
- **Hardware:** CPU Basic (free tier — all compute is on Modal)
- **Visibility:** Public
- **Secrets:** `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `HF_TOKEN`

The Space README doubles as the Field Notes submission — written as a narrative about what Forgotten Lily is, why it was built this way, what was discovered in the process.

### 10.7 Trace Logging

Every turn logs structured metadata (never the player's message content) to a HuggingFace dataset:
- Turn number, act, tones emitted
- Moderation classification
- Note unlocked (if any)
- Lexicon size at time of turn

This satisfies the Sharing is Caring badge and creates a public dataset of anonymous gameplay patterns.

---

## 11. Build Order

### Phase 1 — Inference Foundation (Day 1)
- Set up Modal, deploy endpoints, verify Gemma 4 responds with valid tone JSON
- Generate all 24 tone WAV files with scipy, verify they sound correct
- Write and test the Gemma system prompt in isolation

### Phase 2 — Core Loop (Day 2)
- Build the `gr.Server` app with Tailwind frontend
- Implement conversation panel: message input, tone chip rendering, audio playback
- Connect frontend to Modal via gr.Server API routes
- Implement session state management

### Phase 3 — Notes + Lexicon (Day 3)
- Write all 10 note contents, design note card visuals
- Build evidence board UI with Tailwind — kraft paper cards, pushpins, rotation
- Implement note unlock logic (threshold + topic detection via Gemma response)
- Build lexicon drawer with confidence bars driven by Nemotron scoring

### Phase 4 — Atmosphere + Ending (Day 4)
- Implement background music with Web Audio API ducking
- Implement act-based color temperature transitions via Tailwind CSS variables
- Build the ending sequence: tone finale → white screen → Kokoro TTS → memorial screen
- Add Nemotron input moderation with in-character response handling
- Final polish: animations, transitions, mobile responsiveness

### Phase 5 — Submission (Day 5)
- Write Space README as Field Notes blog post
- Set up HF dataset trace logging
- Deploy Modal endpoints with `modal deploy`
- Final Space deployment, set to public
- Full playthrough test
- Record demo video

---

## 12. Budget

**Modal ($250 credit):**
- Model storage (Volume): ~$3/month for 30GB of model weights
- A10G inference: ~$1.10/hour, ~5 minutes per full game session ≈ $0.09/session
- The credit comfortably supports ~2,700 full sessions — ample for judging

**HuggingFace ($20 credit):**
- CPU Basic Space: free tier, no credits consumed
- Dataset storage for traces: free tier
- Reserve the $20 for any Space hardware upgrade needed during the judging period

---

## 13. Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Tone meanings | One meaning per tone | Discovery, not disambiguation — simpler and more satisfying |
| Tone count | 24 in 6 categories | Rich enough for real expression, learnable in one session |
| Input limit | 280 characters | Keeps detective questions sharp and conversational |
| Harmful input | Lily goes silent, in-character | Immersion never breaks |
| Confirmation of guesses | Nemotron confidence bar only | Preserves the investigation feel — never explicit |
| Background music | Ambient piano, ducks during tones | The contrast is the game's core emotional design |
| Final sentence | "I just wanted to see the world — all three of us, watching the sun come up." | Specific, earned, the dream she never reached |
| UI framework | gr.Server + Tailwind + Vanilla JS | Required for the emotional design vision |
| Tone generation | Procedural scipy (not neural) | Deterministic, instant, no model budget used |
| Ending | No score, no replay prompt | The memorial screen is the ending |

---

*Forgotten Lily — Plan v2.0*
*Ready for implementation.*