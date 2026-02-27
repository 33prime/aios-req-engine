# Extraction Baseline Dump — PersonaPulse Discovery Transcript

**Signal ID**: `5929b7e7-d036-45e2-b71f-5ff8e49e6b7e`
**Project ID**: `634647e8-a22a-4b6f-b42a-452659620bc4`
**Extracted**: 2026-02-20T19:47:18Z
**Model**: `claude-haiku-4-5-20251001` (parallel chunk extraction)
**Pipeline**: Signal Pipeline V2 (8-node LangGraph)

---

## 1. Signal Metadata

```json
{
  "id": "5929b7e7-d036-45e2-b71f-5ff8e49e6b7e",
  "signal_type": "document",
  "source_label": null,
  "processing_status": "complete",
  "triage_metadata": {
    "reason": "~17 entities detected; substantial (4778 words)",
    "strategy": "requirements_doc",
    "word_count": 4778,
    "source_type": "document",
    "priority_score": 0.9,
    "source_authority": "consultant",
    "estimated_entity_count": 17
  },
  "patch_summary": {
    "merged": 12,
    "applied": 65,
    "created": 39,
    "updated": 14,
    "escalated": 0
  },
  "created_at": "2026-02-20T19:47:18.386634+00:00"
}
```

**Source file**: `PersonaPulse_Discovery_Transcript.docx` (uploaded via document processing pipeline)
**Content**: ~29,541 chars, ~4,778 words
**Chunks**: 11 (chunked by document section headers)
**Triage strategy**: `requirements_doc` (parallel chunk path)

---

## 2. All Signal Chunks

### Chunk 0 — Section 1 (Part 1) — 5,959 chars

```
DISCOVERY SESSION TRANSCRIPT
Project: PersonaPulse
"AI-Powered Personal Brand Engine"
Date: Thursday, February 13, 2026
Time: 10:00 AM – 11:47 AM EST
Location: Zoom (Remote)
Recording ID: ZM-2026-0213-PP-001
PARTICIPANTS
Brandon "Bran" Wilson — Founder & CEO, BrandForge Media
Matt Edmund — Technical Consultant, ReadyToGo.ai
Sarah Chen — Head of Product, BrandForge Media (joined 10:32 AM)
Transcribed by: AI Notetaker (Otter.ai) — Reviewed & Edited for Accuracy
— Pre-Call — Informal —
[Zoom room opens. Matt is already connected. Bran joins at 10:01 AM.]
[10:01:12] Bran Wilson: Hey Matt, can you hear me? I just got off another call with my marketing team and my head is spinning. Give me one sec.
[10:01:18] Matt Edmund: No rush, I'm here. Take your time.
[10:01:34] Bran Wilson: Alright, cool. Sorry about that. So listen, before we dive in — I sent you that BRD yesterday. Did you get a chance to look at it?
[10:01:42] Matt Edmund: Yeah, I went through it this morning. I've got some questions, but overall the vision is clear. You want to turn rough ideas into polished multi-platform content that actually sounds like the person who wrote it.
[10:01:58] Bran Wilson: Exactly. Exactly. But there's a lot more behind it than what's on paper. I want to give you the full picture because this thing is personal for me, man. This isn't just another SaaS play.
[10:02:11] Matt Edmund: I'm all ears. Let's start there.
— Section 1 — Origin Story & Why This Matters —
[10:02:24] Bran Wilson: So here's the thing. I ran a boutique marketing agency for six years — BrandForge Media. We had maybe 14 clients at peak, all B2B, mostly SaaS founders and exec coaches. And the number one problem, every single time, was content. Not strategy. Not positioning. Just getting the damn content out the door.
[10:02:51] Matt Edmund: They knew what to say but couldn't find the time to say it.
[10:02:55] Bran Wilson: Bingo. And here's what killed me. We'd hire ghostwriters, and the clients would reject 80% of the drafts. Because it didn't sound like them. The ghostwriter would nail the topic but miss the voice. The cadence, the humor, the way someone structures an argument — that's the stuff that makes a personal brand personal. And no freelancer can replicate that at scale.
[10:03:22] Matt Edmund: So you tried the human route and it didn't scale.
[10:03:26] Bran Wilson: It didn't scale, and honestly it almost tanked the agency. We had one client, Rachel Torres — she's a leadership coach, maybe 30K LinkedIn followers — and she fired us because a ghostwritten post used the phrase "in today's fast-paced business environment." She said, and I quote, "I would literally never say that. That's LinkedIn cringe." And she was right.
[10:03:52] Matt Edmund: Ha. She's not wrong. That phrase should be retired.
[10:03:56] Bran Wilson: It should be a felony. But here's the point — that experience is what started this whole thing. I started thinking, what if the AI could actually learn how someone talks? Not just their topics, but their syntax. Their rhythm. Whether they use em dashes or ellipses. Whether they open with a question or a bold statement. That's PersonaPulse.
[10:04:19] Matt Edmund: And the BRD reflects that with the Style Ingestion piece — the five sample posts for tone calibration.
[10:04:26] Bran Wilson: Right, but I want to push that further. I'll get to that. First let me tell you why the timing matters.
[10:04:33] Bran Wilson: Look, AI is absolutely eating marketing alive right now. And I don't mean that in a doom-and-gloom way. I mean it in a "the old model is dead" way. I was at a conference in Austin last month — SaaS North — and every single panel about growth marketing had the same theme: content volume is table stakes now. You used to be able to post twice a week on LinkedIn and stay visible. Now? The algorithm buries you unless you're posting daily across platforms. And the people winning are the ones using AI to keep up. Not to replace their voice, but to amplify it.
[10:05:12] Matt Edmund: So it's not about whether people should use AI for content — that ship has sailed. It's about how well the AI captures who they actually are.
[10:05:21] Bran Wilson: That's the whole game. And right now, the tools out there are trash for this. ChatGPT, Jasper, Copy.ai — they're all generic. You can give them a prompt and a tone, but they don't learn. They don't remember that you hate the word "leverage" or that you always close with a one-liner. PersonaPulse does.
[10:05:45] Matt Edmund: Got it. So let's walk through the BRD section by section. I'll tell you what I think holds up and where I have questions. Sound good?
[10:05:52] Bran Wilson: Let's do it.
— Section 2 — BRD Walkthrough: Confirmations —
[10:06:01] Matt Edmund: Alright. Phase 1 — Identity and Conversion Calibration. FR-1.1, LinkedIn URL and website scraping for professional context. This is your data foundation. You good with this as described?
[10:06:14] Bran Wilson: Yeah, confirmed. This stays. We need to pull in their headline, about section, experience, even their recommendations if we can. The more context, the better the persona model.
[10:06:28] Matt Edmund: FR-1.2, the style ingestion. Five sample posts minimum. Confirmed?
[10:06:33] Bran Wilson: Confirmed, but I want to talk about expanding this later. Five is a minimum. I want to support up to twenty and weight recent posts more heavily.
[10:06:44] Matt Edmund: Noted. FR-1.3, the Target Destination URL. This is the conversion piece — every piece of content ultimately drives somewhere.
[10:06:53] Bran Wilson: Confirmed. This is non-negotiable. Every content campaign needs a destination. Could be a lead magnet, a booking page, a product launch. If the content isn't driving somewhere, what's the point?
[10:07:08] Matt Edmund: Phase 2 — Content Ingestion. FR-3.1, multimodal input: text musings, long-form stories, voice-to-text. Confirmed?
[10:07:17] Bran Wilson: Confirmed.
```

### Chunk 1 — Section 1 (Part 2) — 2,165 chars

```
And honestly voice is the killer feature. Most of my clients think in voice, not in text. They're walking the dog or driving and they have a thought. They need to capture it before it's gone. Voice-to-text with some AI cleanup is huge.
[10:07:38] Matt Edmund: FR-3.2, LinkedIn as the primary anchor post with CTA to the Target URL. Confirmed?
[10:07:44] Bran Wilson: Confirmed. LinkedIn is the hub. Everything else is a spoke.
[10:07:50] Matt Edmund: FR-3.3, three AI-generated images per post — literal, metaphorical, stylistic. Confirmed?
[10:07:57] Bran Wilson: Confirmed but I have a major update on this. Let's come back to it.
[10:08:03] Matt Edmund: FR-3.4, iterative learning from manual edits. Confirmed?
[10:08:08] Bran Wilson: Big confirm. This is the moat. Every edit makes the system smarter. I want the AI to get so good that after 30 posts, the user barely has to touch anything.
[10:08:22] Matt Edmund: The Ripple Effect workflow — LinkedIn golden, then spin out to X, Reddit, Instagram. Confirmed?
[10:08:30] Bran Wilson: Confirmed. But I want to add TikTok script generation as a platform. We'll get to that.
[10:08:38] Matt Edmund: And the link hierarchy — secondary platforms link to LinkedIn, LinkedIn has the external URL. This is to avoid algorithm penalties for external links.
[10:08:48] Bran Wilson: Exactly. Confirmed. Instagram hates external links. X deprioritizes them. LinkedIn is more forgiving, so it's the natural bridge.
[10:08:59] Matt Edmund: Alright. That's the confirmed stuff. Let me tally that up — we've got solid confirmation on about 70% of the BRD. Now let's talk about what's changing.
— Section 3 — BRD Updates (Major Changes) —
[Sarah Chen joins the call at 10:32 AM.]
[10:32:15] Bran Wilson: Sarah, perfect timing. Matt, this is Sarah Chen, our Head of Product. Sarah, Matt is the technical consultant we're working with on PersonaPulse. We just finished confirming the core BRD and we're about to get into the updates.
[10:32:28] Sarah Chen: Hey Matt. Good to meet you. I've been deep in the competitive analysis so I might jump in with context.
[10:32:34] Matt Edmund: Good to meet you too, Sarah. Jump in anytime.
```

### Chunk 2 — Update 1: Style Ingestion → Full Voice DNA Engine — 2,571 chars

```
[10:32:48] Bran Wilson: Okay, first big change. The style ingestion in FR-1.2 — the five sample posts — that's not enough anymore. I've been thinking about this a lot, and I want to completely overhaul how we build the persona model. I'm calling it the Voice DNA Engine.
[10:33:05] Matt Edmund: Walk me through it.
[10:33:08] Bran Wilson: Instead of just analyzing sample posts, I want the system to do a full voice audit. That means: one, ingest up to 20 sample posts with recency weighting — newer posts matter more because people's voices evolve. Two, the system runs a structured interview — maybe 10 questions — where the user records voice answers about their philosophy, their pet peeves, phrases they love, phrases they hate. Three, it builds a Voice DNA Profile that includes syntax patterns, vocabulary preferences, banned words, sentence structure tendencies, and emotional range.
[10:33:48] Matt Edmund: So you're moving from pattern matching on text samples to a multi-signal persona construction.
[10:33:55] Bran Wilson: Exactly. Here's why this matters. I had a client, Derek Okafor — he's a fintech CEO — and his LinkedIn voice was deliberately different from how he talks in real life. On LinkedIn he's formal, precise, data-driven. In person he's casual, funny, uses sports metaphors constantly. The old system would only capture his LinkedIn voice. The Voice DNA Engine would let him define which version of himself he wants to project, and it would understand the range.
[10:34:28] Sarah Chen: I'll add that from the competitive side, nobody is doing this. Taplio and AuthoredUp let you save templates, but they don't model your voice. This is genuinely differentiated.
[10:34:42] Matt Edmund: I like this. The structured interview is smart because it captures intent, not just output. One thing to flag — 20 posts plus a 10-question voice interview is a pretty heavy onboarding. Are you okay with that friction?
[10:34:58] Bran Wilson: Yes, because the payoff is worth it. But I want the interview to feel conversational, not like a form. Maybe the AI asks the questions in a chat interface and the user can respond via voice or text. Make it feel like you're talking to a branding strategist, not filling out a survey.
[10:35:14] Matt Edmund: Good. We can make that feel natural. I'd also suggest a "quick start" mode where you can use 5 posts and skip the interview, then prompt them to complete the full DNA profile later. Progressive onboarding.
[10:35:28] Bran Wilson: Love it. Do both. Quick start for the impatient, full DNA for the committed.
```

### Chunk 3 — Update 2: Image Generation → Visual Brand Kit with Consistency Engine — 2,244 chars

```
[10:36:02] Bran Wilson: Okay, second big one. FR-3.3 was three AI images per post. I want to completely rethink this. Instead of generating random images each time, I want a Visual Brand Kit.
[10:36:18] Matt Edmund: Define that for me.
[10:36:21] Bran Wilson: During onboarding, the user defines their visual brand. They pick a color palette — maybe from their website or they choose from presets. They select a visual style: minimalist, editorial photography, abstract geometric, illustrated, whatever. They can upload their headshot and brand assets like logos. Then every single image the system generates is constrained to that brand kit. So you don't get a cartoony image one day and a photorealistic image the next. It's consistent.
[10:36:56] Sarah Chen: This is huge for brand trust. I looked at what Canva's doing with their Brand Kit feature and it's one of their highest-retention features. People love consistency.
[10:37:08] Matt Edmund: So the three images per post still happen, but they're all generated within the brand constraints. Different compositions but same visual DNA.
[10:37:18] Bran Wilson: Right. And here's the other piece — I want a Consistency Engine that tracks every image generated and ensures visual coherence over time. If someone's been using blue and white minimalist imagery for 40 posts, the system shouldn't suddenly suggest orange and green. The AI should maintain that thread.
[10:37:42] Matt Edmund: That's a meaningful change from the BRD. The original spec was basically "generate three images from the post theme." This is a persistent visual identity system. Technically, we're talking about storing style embeddings and using them as conditioning inputs for image generation.
[10:37:59] Bran Wilson: Can that be done?
[10:38:02] Matt Edmund: Yeah, it can be done. We'd probably use something like a style reference approach — maintain a bank of approved images and use them as style anchors for new generations. The color palette constraint is straightforward. The trickier part is the consistency over time, but it's solvable.
[10:38:22] Bran Wilson: Good. This is important. I can't overstate how many personal brands look schizophrenic on social media because their visuals have no coherence.
```

### Chunk 4 — Update 3: The Ripple Effect → Platform Intelligence Layer — 2,075 chars

```
[10:39:01] Bran Wilson: Third update. The Ripple Effect in the BRD is basically "adapt the LinkedIn post for other platforms." That's too simple. Each platform has its own culture, its own algorithm, its own content format. A LinkedIn post adapted for X isn't just shorter — it's a completely different piece of content.
[10:39:24] Matt Edmund: So you want platform-native generation, not adaptation.
[10:39:28] Bran Wilson: Exactly. I want what I'm calling the Platform Intelligence Layer. For each platform, the system should understand: character limits and formatting rules, hashtag culture and density, optimal post structure — like X threads vs single tweets, Reddit's expectation for genuine value and hatred of self-promotion, Instagram's carousel format and caption style, and the algorithm's known preferences — like how LinkedIn boosts posts with native content over external links.
[10:40:02] Sarah Chen: We have a spreadsheet of platform-specific rules we compiled. I'll send it over. It covers character limits, hashtag best practices, posting windows, content format preferences for each platform.
[10:40:15] Matt Edmund: That's helpful. So functionally, the system takes the core idea and the LinkedIn draft as the "source of truth," but then generates genuinely native content for each platform rather than doing a find-and-replace adaptation.
[10:40:32] Bran Wilson: Right. And here's the kicker — for Reddit specifically, I want the system to analyze the target subreddit before generating content. What's the tone in r/entrepreneur vs r/startups vs r/marketing? They're completely different communities. The system should adapt to the subreddit culture, not just "make it sound like Reddit."
[10:40:58] Matt Edmund: That's ambitious but doable. We'd need to scrape or index subreddit content to build those community profiles. There might be API rate limit considerations with Reddit.
[10:41:10] Bran Wilson: Whatever it takes. Reddit is where real thought leadership lives now. LinkedIn is performative. Reddit is where people actually engage with ideas.
```

### Chunk 5 — Update 4: Content Review → Full Command Center with Analytics Feedback Loop — 2,886 chars

```
[10:42:01] Bran Wilson: Last major update. The "Review" step in the BRD is just "look at the draft, pick an image, edit, approve." I want to turn that into a real Command Center.
[10:42:16] Matt Edmund: What does a Command Center look like to you?
[10:42:20] Bran Wilson: Okay so picture this. You open the Command Center and you see: the LinkedIn draft on the left with inline editing. The three images on the right with selection and regeneration. Below that, a platform preview panel showing how the post will look on each platform — actual mockups of what the LinkedIn post looks like in-feed, what the tweet looks like, what the Instagram carousel looks like. And here's the big one — a performance prediction panel.
[10:42:52] Matt Edmund: Performance prediction. You mean like an estimated engagement score?
[10:42:57] Bran Wilson: Yes. Based on the user's historical post data and platform trends, the system gives you a predicted engagement range. Something like "This post is likely to generate 150-300 impressions and 15-30 comments based on your historical average." And if the system detects that the post might underperform, it suggests specific changes. Like "Adding a question at the end could increase comments by 40%."
[10:43:28] Matt Edmund: I want to be straight with you on this one. The prediction piece is interesting but it's also the most fragile part of this feature set. Social media engagement is incredibly noisy. You'd need at minimum 50-100 historical posts with engagement data to build any kind of reliable model, and even then you're looking at wide confidence intervals.
[10:43:52] Bran Wilson: I hear you. But even a rough signal is better than nothing. Right now people post and pray. If we can give them a "this is stronger than your average" or "this is weaker," that's valuable.
[10:44:08] Matt Edmund: Fair. We can frame it as a relative score rather than absolute numbers. "This draft scores 78 out of 100 based on your voice consistency and format optimization." Less about predicting exact engagement, more about telling you whether the content is well-structured.
[10:44:28] Bran Wilson: That works. And then the feedback loop — after the post goes live, the system pulls actual engagement metrics and uses that to improve future predictions and content generation. So it's learning from results, not just from edits.
[10:44:45] Sarah Chen: I want to make sure we're tracking the right metrics here. For B2B thought leaders, comments and saves are way more valuable than likes. The system should weight meaningful engagement over vanity metrics.
[10:44:58] Matt Edmund: Agreed. We can build a weighted engagement score. Comments worth 3x, saves worth 2x, shares worth 2x, likes worth 1x. Something like that.
[10:45:08] Bran Wilson: Sarah's right. Likes are noise. Comments are signal. Build it that way.
— Section 4 — New Feature Requests —
```

### Chunk 6 — New Feature 1: Content Calendar with AI-Driven Cadence Optimization — 1,423 chars

```
[10:46:30] Bran Wilson: Alright, new features. These aren't in the BRD at all. First one: I want a built-in Content Calendar.
[10:46:40] Matt Edmund: As in scheduling?
[10:46:43] Bran Wilson: More than scheduling. I want AI-driven cadence optimization. The system should look at the user's engagement data and figure out the optimal posting schedule. Not just "post on Tuesday at 9 AM" — but "you haven't posted a thought leadership piece in 8 days, and your audience engagement drops 23% after a 7-day gap. Here's a suggested post based on your queued ideas."
[10:47:12] Sarah Chen: We should also think about content mix. If someone posts five consecutive "how-to" posts, the system should suggest a storytelling post or a contrarian take to keep things varied.
[10:47:26] Matt Edmund: So it's not just a calendar — it's an editorial AI that understands pacing, variety, and timing.
[10:47:33] Bran Wilson: Exactly. Think of it as having a content strategist built into the platform. One that knows your voice, knows your audience, and knows your patterns.
[10:47:45] Matt Edmund: This is a solid feature but it's Phase 2 material. You need the core content generation engine working before you can layer on strategic scheduling. I'd build the calendar infrastructure early but add the AI optimization after you have real usage data.
[10:48:02] Bran Wilson: Fair. Calendar in Phase 1, smart optimization in Phase 2. Done.
```

### Chunk 7 — New Feature 2: TikTok/Reels Script Generator with Shot List — 1,673 chars

```
[10:49:01] Bran Wilson: Second new feature. Short-form video is exploding and we're ignoring it. I want the system to generate TikTok and Instagram Reels scripts from the same seed content.
[10:49:15] Matt Edmund: When you say script, what exactly are you envisioning?
[10:49:20] Bran Wilson: A full production-ready script. Hook line — the first 3 seconds that stops the scroll. Main talking points with approximate timestamps. Suggested B-roll or visual cues for each section. A closing CTA. And optionally, suggested on-screen text overlays. Basically, I want someone to be able to read this script, hit record on their phone, and have a video that matches their brand.
[10:49:52] Matt Edmund: So it's a shot list plus script plus visual direction, all generated from the same seed idea that produced the LinkedIn post.
[10:49:59] Bran Wilson: Yes. And it should be calibrated to the user's comfort level. Some people are natural on camera. Others are stiff. The system should know that and adjust the script complexity accordingly.
[10:50:12] Sarah Chen: We tested this concept with three of our agency clients last month. Two of them said they'd pay for this feature alone. The bottleneck for most B2B people with video isn't filming — it's knowing what to say and how to structure it.
[10:50:28] Matt Edmund: This is a strong add. The camera comfort calibration is clever — you could ask during onboarding, "How comfortable are you on camera?" and adjust script pacing, complexity, and length accordingly. Someone who's a natural gets a loose outline. Someone who's nervous gets a word-for-word teleprompter script.
[10:50:48] Bran Wilson: Perfect. That's exactly it.
```

### Chunk 8 — New Feature 3: Collaboration Mode for Teams and Ghostwriters — 1,451 chars

```
[10:52:01] Bran Wilson: Third new feature. I keep going back and forth on this one, but I think it's important. Collaboration Mode.
[10:52:10] Matt Edmund: Like multi-user access?
[10:52:14] Bran Wilson: More nuanced than that. A lot of executives have a ghostwriter or a marketing person who manages their content. I want PersonaPulse to support that workflow. The executive records the voice note or types the seed idea. The system generates the draft. The ghostwriter or marketing manager reviews it, makes edits in a tracked-changes-style interface, and submits it back for the executive's approval. Two-tier workflow: Creator and Editor.
[10:52:45] Matt Edmund: So it's a review and approval pipeline with role-based permissions.
[10:52:50] Bran Wilson: Right. And here's the important part — the iterative learning system from FR-3.4 should only learn from the executive's final approved version, not from the ghostwriter's intermediate edits. Because we're modeling the executive's voice, not the ghostwriter's.
[10:53:08] Matt Edmund: That's a great distinction. The learning signal comes from the final approval, not the editing process. We'd need to track edit authorship and only feed the approved-by-creator versions into the persona model.
[10:53:22] Sarah Chen: This also opens up an agency pricing tier. Agencies managing multiple clients would kill for this.
[10:53:30] Bran Wilson: That's the plan. Individual, Team, and Agency tiers.
```

### Chunk 9 — New Feature 4: Competitor Voice Radar (Part 1) — 5,923 chars

```
[10:55:01] Bran Wilson: Last new feature and this one's a bit spicy. Competitor Voice Radar.
[10:55:08] Matt Edmund: Go on.
[10:55:11] Bran Wilson: The user inputs three to five competitor LinkedIn profiles. People in their space who are posting regularly. The system monitors their content and does two things. One, it alerts the user when a competitor posts about a topic the user has expertise in — basically a "response opportunity." Like, "Jen Martinez just posted about AI in sales enablement. You have three seed ideas related to this. Want to draft a response post?" Two, it runs a differentiation analysis. It tells the user, "Your voice tends to be 30% more data-driven than your competitors. Your unique angle is operational detail. Lean into that."
[10:55:58] Matt Edmund: This is cool but it's also the feature most likely to feel creepy if done wrong. Monitoring competitors is fine strategically, but you need to be careful about how you present it. "Competitor monitoring" sounds like surveillance. "Market awareness" or "Industry pulse" sounds like intelligence.
[10:56:18] Bran Wilson: Good point. We'll brand it carefully. But the functionality is clear, right?
[10:56:24] Matt Edmund: Yeah. Technically this is a content monitoring pipeline — periodic scraping of public LinkedIn posts, topic extraction, similarity matching against the user's content areas, and then a notification system. The differentiation analysis is a comparison of the user's Voice DNA against the competitors' content patterns. It's doable, but LinkedIn's terms of service around scraping are strict. We'd probably need to use their official API or a compliant data provider.
[10:56:52] Sarah Chen: We've looked at Phantom Buster and similar tools. There are compliant ways to do this.
[10:56:58] Matt Edmund: Good. Let's make sure whatever we build is defensible from a ToS perspective. I don't want you getting a cease-and-desist from LinkedIn six months in.
[10:57:08] Bran Wilson: Agreed. Do it right or don't do it.
— Section 5 — Personal Context & Vision —
[11:05:01] Matt Edmund: Bran, before we get into timeline and phasing, I want to understand something. You mentioned at the start this is personal. What's driving this beyond the business case?
[11:05:14] Bran Wilson: Honestly? I'm pissed off at what's happening to personal branding. I spent fifteen years building relationships in marketing, and in the last two years I've watched AI turn content into a commodity. Every LinkedIn feed looks the same. The same frameworks, the same "10 things I learned" posts, the same AI-generated slop with a headshot and a sunset. People have stopped sounding like people.
[11:05:42] Bran Wilson: My dad was a radio DJ in Memphis for 20 years. WDIA. He used to tell me, "Bran, your voice is the only thing nobody can copy. Everything else is just noise." And that stuck with me. PersonaPulse is about preserving that. Using AI to amplify what makes someone unique, not to flatten them into the same generic mush.
[11:06:08] Matt Edmund: That's a strong north star. And frankly, it's a better positioning statement than anything in the BRD. "AI that amplifies your uniqueness instead of replacing it."
[11:06:22] Bran Wilson: Write that down. That might be the tagline.
[11:06:26] Sarah Chen: Already did.
[Laughter.]
[11:06:32] Bran Wilson: But seriously — the market timing is perfect. There are over 900 million LinkedIn users and maybe 3% create content regularly. That's 27 million potential content creators, and most of them are stuck because they don't have the time or the confidence. If we can reduce the time from idea to published, polished, multi-platform campaign to under 10 minutes, we unlock a massive market.
[11:06:58] Matt Edmund: What's your timeline ambition? When do you want users in the product?
[11:07:04] Bran Wilson: I want a private beta with 25 users by Q3 2026. Those are all people from my agency network. Real consultants, coaches, and founders who'll give honest feedback. Then public launch Q4 2026 if the beta goes well.
[11:07:22] Matt Edmund: That's aggressive but not unreasonable if we phase it right. Phase 1 is the core engine — Voice DNA, LinkedIn generation, image generation, and the Command Center. That's your MVP. Phase 2 adds the Ripple Effect with Platform Intelligence, the Content Calendar, and the TikTok scripts. Phase 3 is Collaboration Mode and Competitor Radar.
[11:07:48] Bran Wilson: I like that phasing. Can we get Phase 1 to beta by Q3?
[11:07:53] Matt Edmund: If we start architecture in March and move fast on the AI pipeline, I think we can have a rough beta by August. But "beta" means functional, not polished. Your 25 users need to be okay with some rough edges.
[11:08:06] Bran Wilson: They will be. These are people who've been begging me to build this for two years. They'll deal with rough edges if the core value is there.
— Closing & Action Items —
[11:40:01] Matt Edmund: Alright, let me summarize what we've got. BRD confirmation on approximately 70% of the original requirements. Four major updates: Voice DNA Engine replacing simple style ingestion, Visual Brand Kit with Consistency Engine replacing ad hoc image generation, Platform Intelligence Layer replacing basic content adaptation, and a full Command Center with analytics feedback loop replacing the simple review screen. Four new features: Content Calendar with AI cadence optimization, TikTok and Reels script generation, Collaboration Mode for teams and ghostwriters, and Competitor Voice Radar. Is that everything?
[11:40:48] Bran Wilson: That's everything. This is the product I've been trying to articulate for two years. Matt, I'm fired up.
[11:40:55] Sarah Chen: I'll send over the competitive analysis doc and the platform rules spreadsheet by end of day tomorrow.
[11:41:02] Matt Edmund: Perfect. I'll have an updated BRD v2 with technical annotations back to you by next Wednesday.
```

### Chunk 10 — New Feature 4: Competitor Voice Radar (Part 2) — 1,153 chars

```
That'll include my recommended phasing, a rough architecture proposal, and any technical risks I see with the new features. Sound good?
[11:41:18] Bran Wilson: Sounds great. Oh — one more thing. Budget. I've got $180K earmarked for Phase 1 development and I can stretch to $220K if the scope demands it. But I need a realistic estimate before I commit.
[11:41:35] Matt Edmund: Understood. I'll include cost ranges in the updated BRD. We'll have a clearer picture once I map out the AI service costs. Image generation and voice processing have per-call costs that can add up at scale.
[11:41:48] Bran Wilson: That's fine. Just be straight with me on costs. I'd rather know now than get surprised later.
[11:41:55] Matt Edmund: Always. Talk soon, Bran. Sarah, nice meeting you.
[11:42:00] Sarah Chen: Likewise. This is going to be fun.
[11:42:04] Bran Wilson: Let's go build this thing.
[Call ends at 11:42 AM EST. Total duration: 1 hour 41 minutes.]
DOCUMENT CLASSIFICATION: Confidential — BrandForge Media / ReadyToGo.ai
NEXT STEPS: Updated BRD v2 due Wednesday, February 18, 2026
FOLLOW-UP MEETING: Scheduled Thursday, February 20, 2026 at 10:00 AM EST
```

---

## 3. Entity Inventory at Time of Extraction

This is what the LLM saw as `entity_inventory_prompt` — the pre-existing entities at the moment the signal was processed.

### Features (8)

| ID | Name | Status |
|----|------|--------|
| `c4b4af80-177c-4222-9ff8-2a20fb6ec692` | Identity & Voice Ingestion | confirmed_client |
| `d0a2c3ff-527e-46fc-9be1-550206e0f962` | Primary Redirect URL Configuration | confirmed_consultant |
| `ea093e17-eccf-4e9b-9c04-bdc535c75d6d` | Multi-Modal Content Input | confirmed_consultant |
| `8ebd49ba-4c94-47c2-9f5a-7a2dee577061` | LinkedIn Anchor Post Generation | confirmed_consultant |
| `03eaeef5-ca30-48d4-b935-e80ac226ed29` | Company Content Mode | confirmed_consultant |
| `7c3c3e96-9437-4505-aa0a-0c35c7c595a0` | AI Visual Generation | confirmed_consultant |
| `86ed67b3-ee05-489e-b702-003f24826239` | Multi-Channel Campaign Expansion | confirmed_client |
| `b61b314b-6be2-4079-8bd3-c2f2a7f74c68` | Iterative Persona Learning | confirmed_client |

### Personas (1)

| ID | Name | Status |
|----|------|--------|
| `6d6c4c74-52ef-4376-b130-9120b159783e` | Founder Content Creator | confirmed_client |

### Stakeholders (1)

| ID | Name | Type | Status |
|----|------|------|--------|
| `4238e5c1-c6ec-4020-922b-fca2d3b32b22` | Bran Wilson | champion | confirmed_client |

### Workflows (8)

| ID | Name | Status |
|----|------|--------|
| `4806c5cb-e028-4d42-a208-302ae8688854` | Founder Persona Setup & Voice Calibration | confirmed_consultant |
| `3b81652d-8aa2-403d-a2f9-5333c8384403` | Founder Persona Setup & Voice Calibration | confirmed_consultant |
| `b6b8378f-ffaf-46a7-a0bc-3f0c0bf70f70` | Single-Input to Multi-Channel Content Campaign | confirmed_consultant |
| `3b2d1729-2b21-4d84-af86-2de98fc7bef0` | Single-Input to Multi-Channel Content Campaign | confirmed_consultant |
| `f10b1aa4-27db-470a-a78b-8c24ea678d4e` | Company Content Distribution in Founder Voice | confirmed_consultant |
| `00cff71a-c7a1-40d3-a98d-22c2db899c88` | Company Content Distribution in Founder Voice | confirmed_consultant |
| `897737c0-5d39-4dc6-9ecf-e9ddc15b4375` | Persona Model Iterative Improvement | confirmed_consultant |
| `4ca7191d-6748-47b4-a81f-2a3c683b93be` | Persona Model Iterative Improvement | confirmed_consultant |

> **Note**: Workflows appear duplicated (4 unique names × 2 = 8 rows). This is the current/future state pairing pattern — each workflow has a "current" and "future" variant.

### VP Steps (36)

First 20 shown (all `confirmed_consultant`):

| ID | Label | Workflow |
|----|-------|---------|
| `8ea4955f-...` | Brief Marketing Agency or AI Tool | Founder Persona Setup & Voice Calibration |
| `045bd778-...` | Share Sample Content Manually | Founder Persona Setup & Voice Calibration |
| `7057eb3f-...` | Review First Draft & Identify Voice Mismatches | Founder Persona Setup & Voice Calibration |
| `b49bcd19-...` | Provide Correction Feedback | Founder Persona Setup & Voice Calibration |
| `5caa7095-...` | Repeat Revision Cycles | Founder Persona Setup & Voice Calibration |
| `c206a56c-...` | Submit LinkedIn URL & Website | Founder Persona Setup & Voice Calibration |
| `8dd29922-...` | Upload Sample Posts | Founder Persona Setup & Voice Calibration |
| `e5197b1a-...` | Configure Primary Redirect URL | Founder Persona Setup & Voice Calibration |
| `17bdd50d-...` | Review & Confirm Persona Model | Founder Persona Setup & Voice Calibration |
| `c4e0b89e-...` | Capture Raw Idea | Single-Input to Multi-Channel Content Campaign |
| `473e8858-...` | Manually Draft LinkedIn Post | Single-Input to Multi-Channel Content Campaign |
| `66f439b3-...` | Manually Adapt for Other Channels | Single-Input to Multi-Channel Content Campaign |
| `9b4ac1ab-...` | Source or Create Visuals | Single-Input to Multi-Channel Content Campaign |
| `1df02600-...` | Manually Add CTA and Destination URL | Single-Input to Multi-Channel Content Campaign |
| `297605e3-...` | Publish Across Platforms | Single-Input to Multi-Channel Content Campaign |
| `16f45e53-...` | Submit Raw Input | Single-Input to Multi-Channel Content Campaign |
| `d4d9a343-...` | AI Generates LinkedIn Anchor Post | Single-Input to Multi-Channel Content Campaign |
| `35edf7b0-...` | AI Generates Three Visual Options | Single-Input to Multi-Channel Content Campaign |
| `ed690c9c-...` | Founder Reviews & Selects Visual | Single-Input to Multi-Channel Content Campaign |
| `bacaac2a-...` | AI Expands to Multi-Channel Variants | Single-Input to Multi-Channel Content Campaign |

*... and 16 more*

### Business Drivers (9)

| ID | Type | Description (truncated) | Status |
|----|------|------------------------|--------|
| `b8750ec5-...` | kpi | Number of active founders using the platform to publish content per month | ai_generated |
| `b7d9bb8d-...` | goal | Automate the end-to-end personal brand content workflow so founders can publish... | confirmed_consultant |
| `04703a56-...` | goal | Enable each founder to distribute Steadynamic company content through their pers... | confirmed_consultant |
| `768398fe-...` | goal | Drive measurable traffic to user-defined destination URLs (landing pages, lead m... | confirmed_consultant |
| `fab870a4-...` | goal | Build a self-improving persona model that becomes more accurate over time by lea... | confirmed_consultant |
| `204c2ffa-...` | kpi | Time from raw input (text or voice note) to publishable multi-channel draft | ai_generated |
| `6531be9d-...` | kpi | Click-through rate from published content to the founder's Primary Redirect URL | ai_generated |
| `7f31d005-...` | kpi | Persona model accuracy as measured by reduction in manual edits per generated po... | ai_generated |
| `66058633-...` | pain | Generic AI tools like ChatGPT and Gemini do not capture a founder's unique tone... | confirmed_client |

### Constraints (5)

| ID | Title | Type | Status |
|----|-------|------|--------|
| `014bcd3e-...` | LinkedIn API Terms of Service Compliance | regulatory | ai_generated |
| `92d869d3-...` | AI-Generated Content Disclosure Requirements | regulatory | ai_generated |
| `4b25587a-...` | User Voice & Identity Data Privacy Obligations | regulatory | ai_generated |
| `60572462-...` | Third-Party AI Model Dependency & Vendor Lock-In Risk | technical | ai_generated |
| `71667879-...` | Brand Impersonation & Misuse Liability | strategic | ai_generated |

### Data Entities (0)

*None existed before this signal.*

### Competitor References (0)

*None existed before this signal.*

---

## 4. System Prompt (Full Literal Text)

The extraction uses **3 system blocks** sent to the Anthropic API:

### Block 1: Static Extraction Prompt (cached)

```
You are a senior requirements analyst extracting structured entity patches from project signals.

Your output is EntityPatch[] — surgical create/merge/update operations targeting specific BRD entities.

## RULES
1. Reference existing entity IDs for merge/update operations — NEVER create duplicates.
2. CRITICAL: Use the COMPLETE entity ID from the inventory (full UUID, e.g. "aeb74d67-0bee-4eaa-b25c-6957a724b484"). Never truncate IDs.
3. For each patch, note if it supports or contradicts a memory belief.
4. Flag any answers to open questions.
5. Prioritize extraction of entities that fill the identified gaps.
6. Every patch MUST have evidence quotes from the source text.
7. Set confidence based on: explicit statement (high) vs implied/inferred (medium) vs ambiguous (low).

## ENTITY TYPES & FIELDS

### feature
create: {name, overview, priority_group (must_have|should_have|could_have|out_of_scope), category, is_mvp}
merge/update: any subset of above fields

### persona
create: {name, role, goals (list), pain_points (list)}
merge/update: append to goals/pain_points, update role

### stakeholder
create: {name, first_name, last_name, role, stakeholder_type (champion|sponsor|blocker|influencer|end_user), influence_level (high|medium|low), domain_expertise}
merge/update: any subset

### workflow
create: {name, description}
merge/update: description update

### workflow_step
create: {label, description, workflow_name, state_type (current|future), time_minutes, pain_description, benefit_description, automation_level (manual|semi_automated|fully_automated), operation_type}
merge/update: any subset
NOTE: Current-state steps should default to "manual". Future-state steps should default to "semi_automated" or "fully_automated" — only use "manual" for future steps that truly remain manual.

### data_entity
create: {name, entity_category (domain|reference|transactional|analytical), fields (list of {name, type, required, description})}
merge/update: append fields, update category

### business_driver
create: {description, driver_type (pain|goal|kpi), business_impact, affected_users, measurement, baseline_value, target_value}
merge/update: any subset

### constraint
create: {title, constraint_type (technical|compliance|business|integration), description}
merge/update: update description

### competitor
create: {name, reference_type (competitor|design_inspiration|feature_inspiration), relevance_description}
merge/update: update relevance

### vision
update: {statement} — single vision statement for the project

## CONFIDENCE LEVELS
- very_high: Explicit, unambiguous statement with specific details
- high: Clear requirement but may lack some specifics
- medium: Implied or inferred from context
- low: Ambiguous, could be interpreted differently

## OPERATIONS
- create: New entity not matching any existing
- merge: Add evidence/data to existing entity (use target_entity_id from inventory)
- update: Change specific fields on existing entity (use target_entity_id)
- stale: New signal contradicts existing entity
- delete: Signal explicitly removes/cancels something

## KEY EXTRACTION RULES
- Business requirements (BRs) = BOTH a feature AND a workflow_step
- Named processes = workflow with multiple steps (3-8 per process)
- Current vs future: "Today we..." → current steps, "System will..." → future steps
- Stakeholders are INDIVIDUAL PEOPLE only, never organizations
- Data entities are domain objects (Patient, Invoice, Order), not generic "data"
```

### Block 2: Chunk-Specific Prompt (cached)

```
You are extracting structured entity patches from ONE SECTION of a larger document.

Focus on entities clearly present in THIS chunk. Another pass will merge duplicates across chunks — extract everything you see without worrying about cross-chunk dedup.

If a section title is provided, use it as page_or_section in evidence references.
```

### Block 3: Dynamic Context (not cached)

This block is assembled from `EXTRACTION_CONTEXT_TEMPLATE`:

```
{strategy_block}

## CONTEXT

{entity_inventory}

{memory}

{gaps}
```

Where `strategy_block` for this signal (triage strategy = `requirements_doc`) is:

```
## SOURCE-SPECIFIC: Requirements Document
- Extract ALL named processes as workflows with 3-8 steps each
- Every business requirement becomes BOTH a feature AND a workflow_step
- High entity volume expected — be comprehensive
- Default source_authority: check triage metadata, usually "client"
```

And `entity_inventory` is rendered in the format:
```
## Existing Entity Inventory

### Features
- [c4b4af80-177c-4222-9ff8-2a20fb6ec692] Identity & Voice Ingestion [confirmed_client]
- [d0a2c3ff-527e-46fc-9be1-550206e0f962] Primary Redirect URL Configuration [confirmed_consultant]
... (all 8 features)

### Personas
- [6d6c4c74-52ef-4376-b130-9120b159783e] Founder Content Creator [confirmed_client]

### Stakeholders
- [4238e5c1-c6ec-4020-922b-fca2d3b32b22] Bran Wilson (champion) [confirmed_client]

### Workflows
... (all 8 workflows)

### Workflow Steps
... (all 36 steps, max 20 shown per type)

### Business Drivers
... (all 9 drivers)

### Constraints
... (all 5 constraints)

### Data Entities
(none)

### Competitor References
(none)
```

**Memory** and **Gaps** layers are also injected but their exact content at extraction time is ephemeral (not stored in DB).

---

## 5. Example User Message (Chunk 0)

This is the exact user message sent for the first chunk:

```
## Document Chunk 1 (Section: Section 1 (Part 1))

DISCOVERY SESSION TRANSCRIPT
Project: PersonaPulse
"AI-Powered Personal Brand Engine"
Date: Thursday, February 13, 2026
Time: 10:00 AM – 11:47 AM EST
Location: Zoom (Remote)
Recording ID: ZM-2026-0213-PP-001
PARTICIPANTS
Brandon "Bran" Wilson — Founder & CEO, BrandForge Media
Matt Edmund — Technical Consultant, ReadyToGo.ai
Sarah Chen — Head of Product, BrandForge Media (joined 10:32 AM)
[... full chunk content as shown in Section 2, Chunk 0 ...]

## Task
Extract all EntityPatch objects from this chunk. Use the submit_entity_patches tool.
```

Each of the 11 chunks gets an identical structure with `chunk_index + 1` and its section title.

---

## 6. Raw Extraction Results (Pre-Dedup)

> **NOT AVAILABLE** — Raw patches are **ephemeral**. The V2 pipeline extracts patches in memory, deduplicates them, scores them, and applies them — none of the intermediate results are persisted to the database.
>
> Only the final `patch_summary` counts survive:
>
> ```json
> {
>   "created": 39,
>   "merged": 12,
>   "updated": 14,
>   "escalated": 0,
>   "applied": 65
> }
> ```
>
> The `chat_summary` field on the signal also captures a natural language description (see Section 1).
>
> **To get raw patches, we need to re-run extraction with logging enabled.** See Section 9 for instrumentation plan.

---

## 7. Post-Dedup Results

> **NOT AVAILABLE** — Dedup results are also ephemeral. The 3-tier dedup pipeline (`app/core/entity_dedup.py` — exact match → fuzzy match → embedding similarity) runs in memory between extraction and scoring.
>
> What we can infer from the final state:
> - Several features were created as near-duplicates (e.g., "Visual Consistency Engine" appears 3 times, "Content Mix Optimization" appears 2 times, "Subreddit Culture Analysis" appears 2 times, "TikTok Script Generation" appears 3 forms)
> - This suggests the cross-chunk dedup (`_merge_duplicate_patches()` in `extract_entity_patches.py`) may not be catching all duplicates before they reach the apply stage
>
> **To get dedup decisions, we need to re-run with logging enabled.** See Section 9 for instrumentation plan.

---

## 8. Final Applied State

### Summary

| Entity Type | Before | After | Created | Merged | Updated |
|-------------|--------|-------|---------|--------|---------|
| Features | 8 | 34 | 26 | — | — |
| Personas | 1 | 3 | 2 | — | — |
| Stakeholders | 1 | 1 | 0 | — | — |
| Workflows | 8 | 8 | 0 | — | — |
| VP Steps | 36 | 36 | 0 | — | — |
| Business Drivers | 9 | 37 | 28 | — | — |
| Constraints | 5 | 11 | 6 | — | — |
| Data Entities | 0 | 10 | 10 | — | — |
| Competitor Refs | 0 | 0 | 0 | — | — |

**Totals**: 65 applied patches (39 created, 12 merged, 14 updated)

### New Features Created (26)

| Name | Priority | MVP | Status |
|------|----------|-----|--------|
| AI-Driven Cadence Optimization | should_have | | confirmed_client |
| Analytics Feedback Loop for Content Improvement | should_have | | confirmed_client |
| Collaboration Mode for Teams and Ghostwriters | should_have | | confirmed_client |
| Command Center with Inline Editing | must_have | MVP | confirmed_client |
| Competitor Voice Radar | could_have | | confirmed_client |
| Content Calendar | must_have | MVP | confirmed_client |
| Content Mix Optimization | should_have | | confirmed_client |
| Content Mix Optimization *(duplicate)* | should_have | | confirmed_client |
| Conversational Voice Interview | must_have | MVP | confirmed_client |
| Multi-Platform Ripple Effect Distribution | must_have | MVP | confirmed_client |
| Performance Prediction Panel | should_have | | confirmed_client |
| Platform Intelligence Layer | must_have | MVP | confirmed_client |
| Platform Preview Mockups | must_have | MVP | confirmed_client |
| Progressive Onboarding (Quick Start Mode) | should_have | MVP | confirmed_client |
| Progressive Onboarding with Quick Start Mode *(duplicate)* | should_have | | confirmed_client |
| Subreddit Culture Analysis | must_have | MVP | confirmed_client |
| Subreddit Culture Analysis *(duplicate)* | must_have | MVP | confirmed_client |
| TikTok Script Generation | must_have | MVP | confirmed_client |
| TikTok Script Generation *(variant)* | should_have | | confirmed_client |
| TikTok/Reels Script Generator with Shot List *(variant)* | should_have | | confirmed_client |
| Visual Brand Kit | must_have | MVP | confirmed_client |
| Visual Consistency Engine | must_have | MVP | confirmed_client |
| Visual Consistency Engine *(duplicate)* | should_have | | confirmed_client |
| Visual Consistency Engine *(duplicate)* | must_have | MVP | confirmed_client |
| Voice DNA Engine | must_have | MVP | confirmed_client |
| Voice-to-Text Input with AI Cleanup | must_have | MVP | confirmed_client |

### New Personas Created (2)

| Name | Role | Status |
|------|------|--------|
| Ghostwriter / Marketing Manager | Content Editor and Reviewer | confirmed_client |
| Ghostwriter / Marketing Manager *(duplicate)* | Editor in Collaboration Mode workflow | confirmed_client |

### New Business Drivers Created (28)

| Type | Count | Examples |
|------|-------|---------|
| goal | 14 | Phase 1 MVP by Q3 2026, agency pricing tiers, Reddit engagement, content pacing |
| pain | 14 | AI commoditized content, ghostwriters can't replicate voice, visual incoherence, video bottleneck |

### New Constraints Created (6)

| Title | Type | Status |
|-------|------|--------|
| Reddit API Rate Limits & Scraping Constraints | technical | confirmed_consultant |
| Style Embedding Storage & Conditioning for Image Generation | technical | confirmed_consultant |
| Reddit API Rate Limits & Scraping Constraints *(duplicate)* | technical | confirmed_client |
| Engagement Prediction Reliability Threshold | technical | confirmed_client |
| Edit Authorship Tracking for Collaboration Workflows | technical | confirmed_client |
| AI Service Per-Call Cost Scaling | technical | confirmed_consultant |

### New Data Entities Created (10)

| Name | Category | Status |
|------|----------|--------|
| Voice DNA Profile | domain | confirmed_client |
| Voice DNA Profile *(duplicate)* | domain | confirmed_client |
| Visual Brand Kit Profile | domain | confirmed_client |
| Visual Brand Kit *(duplicate)* | domain | confirmed_client |
| Platform Rules Registry | reference | confirmed_client |
| Platform Rules Registry *(duplicate)* | reference | confirmed_client |
| Camera Comfort Profile | domain | confirmed_client |
| Camera Comfort Profile *(duplicate)* | domain | confirmed_client |
| Edit Audit Trail | transactional | confirmed_client |
| Edit Audit Trail *(duplicate)* | transactional | confirmed_client |

---

## 9. Observations & Next Steps

### Duplicate Problem

The extraction produced significant duplicates that survived the dedup pipeline:

| Entity | Duplicate Count | Notes |
|--------|----------------|-------|
| Visual Consistency Engine | 3 | Same concept from chunks 3, 5, and synthesis |
| Content Mix Optimization | 2 | From chunks 5 and 6 |
| Subreddit Culture Analysis | 2 | From chunks 4 and synthesis |
| TikTok Script Generation | 3 variants | "TikTok Script Generation", "TikTok Script Generation" (different overview), "TikTok/Reels Script Generator with Shot List" |
| Progressive Onboarding | 2 | Slight name variation |
| Voice DNA Profile | 2 | Identical name, same category |
| Platform Rules Registry | 2 | Identical |
| Camera Comfort Profile | 2 | Identical |
| Edit Audit Trail | 2 | Identical |
| Reddit API Rate Limits | 2 | Same constraint, different authority |
| Ghostwriter persona | 2 | Same concept, different role wording |

**Root cause hypothesis**: Cross-chunk dedup (`_merge_duplicate_patches()`) merges exact name matches within the same extraction batch, but:
1. Slight name variations ("Progressive Onboarding (Quick Start Mode)" vs "Progressive Onboarding with Quick Start Mode") slip past exact matching
2. Data entities with identical names are still getting created as duplicates, suggesting the dedup may not be checking data_entity types
3. The 3-tier entity dedup in `entity_dedup.py` (which runs between extraction and scoring) should catch these via fuzzy/embedding matching, but may have a threshold that's too strict

### Instrumentation Plan

To capture raw patches for eval comparison, add logging to:

1. **`app/chains/extract_entity_patches.py`** — Log raw patches per chunk before `_merge_duplicate_patches()`
2. **`app/core/entity_dedup.py`** — Log dedup decisions (which patches were merged and why)
3. **`app/graphs/unified_processor.py`** — Log patches after scoring, before apply

Storage: Write to a `signal_extraction_logs` table or to a JSON file in `docs/eval/runs/`.

### Tool Schema

The LLM is forced to use this tool (tool_choice = "submit_entity_patches"):

```json
{
  "name": "submit_entity_patches",
  "input_schema": {
    "type": "object",
    "properties": {
      "patches": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "operation": { "enum": ["create", "merge", "update", "stale", "delete"] },
            "entity_type": { "enum": ["feature", "persona", "stakeholder", "workflow", "workflow_step", "data_entity", "business_driver", "constraint", "competitor", "vision"] },
            "target_entity_id": { "type": "string" },
            "payload": { "type": "object" },
            "evidence": {
              "type": "array",
              "items": {
                "properties": {
                  "chunk_id": { "type": "string" },
                  "quote": { "type": "string" },
                  "page_or_section": { "type": "string" }
                },
                "required": ["quote"]
              }
            },
            "confidence": { "enum": ["very_high", "high", "medium", "low"] },
            "confidence_reasoning": { "type": "string" },
            "source_authority": { "enum": ["client", "consultant", "research", "prototype"] },
            "mention_count": { "type": "integer" },
            "belief_impact": {
              "type": "array",
              "items": {
                "properties": {
                  "belief_summary": { "type": "string" },
                  "impact": { "enum": ["supports", "contradicts", "refines"] },
                  "new_evidence": { "type": "string" }
                }
              }
            },
            "answers_question": { "type": "string" }
          },
          "required": ["operation", "entity_type", "payload", "confidence"]
        }
      }
    },
    "required": ["patches"]
  }
}
```
