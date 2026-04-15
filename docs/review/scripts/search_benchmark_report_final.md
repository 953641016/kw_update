# 搜索引擎基准测试报告

- **日期**: 2026-04-09 00:06
- **测试关键词**: 10
- **每个关键词结果数**: 50 条
- **对比引擎**: Serper (Google), Brave, Tavily, Exa (AI语义搜索)

---

## 摘要

| 指标 | Serper | Brave | Tavily | Exa |
|---|---|---|---|---|
| 总结果数 | 404 | 450 | 391 | 496 |
| 唯一域名数 | 238 | 278 | 229 | 310 |
| AI相关命中数 | 343 | 432 | 312 | 448 |
| 潜在竞争对手域名数 | 225 | 269 | 212 | 291 |

**AI相关结果获胜者**: **EXA** (448 个命中)

**唯一竞争对手域名获胜者**: **EXA** (291 个域名)

---

## API 调用效率对比

| 引擎 | 单次最大结果数 | 获取50条需调用次数 | 分页机制 | API消耗 |
|---|---|---|---|---|
| **Tavily** | 自定义 | 1 次 ✅ | 无需分页，直接指定 max_results | 1 次 |
| **Exa** | 自定义 | 1 次 ✅ | 无需分页，直接指定 num_results | 1 次 |
| **Serper** | 10 条 | 5 次 ❌ | 需要 page 参数分页 | 1-5 次 |
| **Brave** | 20 条 | 5 次 ❌ | 需要 offset 参数分页 | 5 次 |

**高效推荐**: Tavily 和 Exa 支持一次性返回大量结果，API 调用效率更高。

---

## 按关键词细分

| 关键词 | Serper (总数/AI) | Brave (总数/AI) | Tavily (总数/AI) | Exa (总数/AI) |
|---|---|---|---|---|
| ai song creator | 44/42 | 50/50 | 36/31 | 50/50 |
| ai song creation tool | 40/36 | 50/50 | 33/30 | 50/48 |
| ai content creation tool | 45/38 | 50/47 | 40/31 | 49/44 |
| ai design platform | 40/35 | 50/49 | 43/35 | 50/50 |
| ai voice recognition | 44/32 | 50/47 | 38/32 | 50/41 |
| ai video editor | 27/22 | 0/0 | 36/27 | 50/43 |
| educational voice generator | 43/40 | 50/46 | 42/36 | 50/42 |
| generative video software | 40/32 | 50/47 | 41/29 | 49/44 |
| video editing ai | 41/32 | 50/49 | 32/25 | 50/47 |
| realistic voice generator | 40/34 | 50/47 | 50/36 | 48/39 |

## 域名重叠分析

| 类别 | 数量 | 域名示例 |
|---|---|---|
| 所有4个引擎 | 73 | adobe.com, ai-song.ai, aimakesong.com, aiola.ai, aisong.org, aisongmaker.io, aiva.ai, aivoicedetector.com, artlist.io, assemblyai.com |
| 仅 Serper | 46 | abyssale.com, ads.tiktok.com, altametrics.com, aol.com, apartmenttherapy.com, arkdesign.ai, automusic.ai, bandlab.com, banuba.com, benchmarksixsigma.com |
| 仅 Brave | 82 | 3daistudio.com, affine.pro, ai.meta.com, aimusic.so, aimusicgen.ai, aistudios.com, aitoolssme.com, aitoolsspace.com, aivocal.io, aixploria.com |
| 仅 Tavily | 55 | aimultiple.com, almcorp.com, ambiq.com, atlassian.com, audiocipher.com, awwtomation.com, blog.adobe.com, ceros.com, contentpen.ai, cpoclub.com |
| 仅 Exa | 181 | 3dgen.io, about.heyeddie.ai, ai-copysmith.com, aidesigner.ai, aidocmaker.com, aigenerator.world, aisongcreator.pro, aisongmaker.ai, aitoolly.com, aitools.inc |
| 总计唯一 | 580 | - |

## 样本搜索结果（每个引擎每个关键词前3名）

### `ai song creator`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | aisongmaker.io | AI Song Maker: AI Music Generator for Royalty-Free | Y |
| serper | 2 | suno.com | Suno | AI Music Generator | Y |
| serper | 3 | aisong.org | AI Song: Free AI Song & Music Generator Online (Ro | Y |
| brave | 1 | suno.com | Suno | AI Music Generator | Y |
| brave | 2 | musiccreator.ai | Free AI Music Generator | Royalty-Free - MusicCrea | Y |
| brave | 3 | producer.ai | Producer.ai | AI Music Agent | Y |
| tavily | 1 | ilovesong.ai | iLoveSong.ai: AI Music Generator By SongAI | Y |
| tavily | 2 | aisong.org | AI Song: Free AI Song & Music Generator Online (Ro | Y |
| tavily | 3 | aisongmaker.io | AI Song Maker: AI Music Generator for Royalty-Free | Y |
| exa | 1 | artlist.io | AI Music Generator: Create AI Music & Songs - Artl | Y |
| exa | 2 | suno.com | Suno | AI Music Generator | Y |
| exa | 3 | song.do | Free AI Song Generator ｜ Song.do | Y |

### `ai song creation tool`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | suno.com | Suno | AI Music Generator | Y |
| serper | 2 | soundraw.io | SOUNDRAW | AI Music Generator – Royalty Free Beats | Y |
| serper | 3 | aimakesong.com | AI Make Song: AI Song Maker & Music Generator Free | Y |
| brave | 1 | aisongmaker.io | AI Song Maker: AI Music Generator for Royalty-Free | Y |
| brave | 2 | musiccreator.ai | Free AI Music Generator | Royalty-Free - MusicCrea | Y |
| brave | 3 | mureka.ai | Mureka: Best AI Music Generator in 2025 to Create  | Y |
| tavily | 1 | gsong.ai | Free AI Song Generator ｜ GSong | Y |
| tavily | 2 | aisong.org | AI Song: Free AI Song & Music Generator Online (Ro | Y |
| tavily | 3 | aimakesong.com | AI Make Song: AI Song Maker & Music Generator Free | Y |
| exa | 1 | suno.com | Suno | AI Music Generator | Y |
| exa | 2 | songsai.com | AI Music Generator Free - Melody Maker & Song Gene | Y |
| exa | 3 | soundraw.io | SOUNDRAW | AI Music Generator – Royalty Free Beats | Y |

### `ai content creation tool`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | getblend.com | 12 Best AI Tools to Use for Content Creation in 20 | Y |
| serper | 2 | contentbot.ai | ContentBot - AI Content Automation and Workflows | Y |
| serper | 3 | copy.ai | Free AI Writing Generator & Tools - Copy.ai | Y |
| brave | 1 | bigtincan.com | 7 AI content creation tools every marketer needs t | Y |
| brave | 2 | buffer.com | 14 AI Tools for Social Media Content Creation in 2 | Y |
| brave | 3 | getblend.com | 12 Best AI Tools to Use for Content Creation in 20 | Y |
| tavily | 1 | medium.com | What Are the Best AI Tools for Content Creation? |  |
| tavily | 2 | rankyak.com | AI-Powered Content Creation Platforms: 14 Free & P | Y |
| tavily | 3 | thinglink.com | The Best AI Content Creation Tools: A Practical Gu | Y |
| exa | 1 | impactplus.com | Top 14 AI Tools for Content Creation in 2026 - IMP | Y |
| exa | 2 | getblend.com | 12 Best AI Tools to Use for Content Creation in 20 | Y |
| exa | 3 | youtube.com | Top 5 AI Tools For Content Creators in 2026 - YouT |  |

### `ai design platform`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | stitch.withgoogle.com | Stitch - Design with AI | Y |
| serper | 2 | cieden.com | 6 Best Product Design AI Tools - Cieden | Y |
| serper | 3 | canva.com | Magic Design™: Free Online AI Design Tool - Canva | Y |
| brave | 1 | stitch.withgoogle.com | Stitch - Design with AI | Y |
| brave | 2 | designs.ai | DesignsAI - AI-Powered Design Platform | Y |
| brave | 3 | figma.com | Figma AI: Your Creativity, unblocked with Figma AI | Y |
| tavily | 1 | support.shazamme.com | 30 AI design tools for agencies : - Shazamme | Y |
| tavily | 2 | youtube.com | We Tested AI Design Tools… Here's the Best One - Y |  |
| tavily | 3 | figma.com | 11 of the Best AI Design Tools for 2026 | Y |
| exa | 1 | canva.com | Magic Design™: Free Online AI Design Tool - Canva | Y |
| exa | 2 | kittl.ai | Kittl | The AI-First Design Platform for Creators | Y |
| exa | 3 | figma.com | Free AI Design Generator - Design Using AI | Figma | Y |

### `ai voice recognition`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | cloud.google.com | Speech-to-Text: AI voice typing & transcription | Y |
| serper | 2 | soniox.com | Soniox | Speech-to-Text AI | Y |
| serper | 3 | boost.ai | Conversational AI and AI Voice Recognition Technol | Y |
| brave | 1 | cloud.google.com | Speech-to-Text: AI voice typing & transcription |  | Y |
| brave | 2 | openai.com | Introducing Whisper | OpenAI | Y |
| brave | 3 | voiceitt.com | Voiceitt - Inclusive Voice AI | Y |
| tavily | 1 | telnyx.com | How AI Voice Works For Real-Time Customer Support | Y |
| tavily | 2 | z3x.io | What is AI Voice Recognition? | Y |
| tavily | 3 | aiola.ai | AI Speech Recognition: A Guide | Y |
| exa | 1 | hearsy.app | Voice Recognition Software: Dragon to Local AI (20 | Y |
| exa | 2 | speechmatics.com | AI Speech Technology | Speech APIs powering Voice  | Y |
| exa | 3 | twilio.com | What is voice recognition and how does it work? |  |  |

### `ai video editor`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | invideo.io | Free AI Video Editor - Edit Videos with AI - Invid | Y |
| serper | 2 | opus.pro | AI Video Editor, No Editing Skills Needed - OpusCl | Y |
| serper | 3 | veed.io | Free Online Video Editor - AI Auto Edits, Audio Cl | Y |
| tavily | 1 | vmaker.com | Award Winning AI Video Editor: Free & Online | Y |
| tavily | 2 | pictory.ai | AI Video Editor | Edit Faster with AI | Y |
| tavily | 3 | vizard.ai | AI Video Editor: Auto Create and Edit Video For Fr | Y |
| exa | 1 | scenery.video | Scenery video editor | AI-powered video editing fo | Y |
| exa | 2 | linkedin.com | Divine Akachukwu | Ai + Traditional Video Editor | |  |
| exa | 3 | linkedin.com | Odeyale pelumi | Video Editor | Motion Designer |  |  |

### `educational voice generator`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | lovo.ai | AI Voices for Educational Content - LOVO AI | Y |
| serper | 2 | canva.com | AI Voice Generator: Text to Speech Online - Canva | Y |
| serper | 3 | readspeaker.com | ReadSpeaker: Text-to-speech for Business & Educati | Y |
| brave | 1 | lovo.ai | Create Educational Content Using AI Voice Generato | Y |
| brave | 2 | elevenlabs.io | Educational AI Voices | ElevenLabs Voice Library | Y |
| brave | 3 | canva.com | AI Voice Generator: Text to Speech Online | Canva | Y |
| tavily | 1 | elevenlabs.io | Educational AI Voices | Y |
| tavily | 2 | finevoice.ai | Informative & Educational AI Voice Generator Onlin | Y |
| tavily | 3 | lovo.ai | AI Voices for Educational Content | Y |
| exa | 1 | lovo.ai | AI Voices for Educational Content - LOVO AI | Y |
| exa | 2 | readspeaker.com | ReadSpeaker: Text-to-speech for Business & Educati | Y |
| exa | 3 | voice.ai | Text to Speech for Education |  |

### `generative video software`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | zapier.com | The 18 best AI video generators in 2026 - Zapier | Y |
| serper | 2 | reddit.com | I tried 5 AI video tools so you don't have to - he |  |
| serper | 3 | canva.com | AI Video Generator: Text to Video AI Tool - Canva | Y |
| brave | 1 | cnet.com | Best AI Video Generators of 2026, Reviewed and Ran | Y |
| brave | 2 | videogen.io | VideoGen - AI Video Generator - Create Videos in M | Y |
| brave | 3 | pcmag.com | So Long, Sora: The Most Powerful AI Video Generato | Y |
| tavily | 1 | capterra.com | Best AI Video Generator Software 2026 |  |
| tavily | 2 | visla.us | Best AI Video Generators for Business in 2026 | Y |
| tavily | 3 | magai.co | Generative AI Video Tools: 7 Best Platforms for 20 | Y |
| exa | 1 | pcmag.com | The Best AI Video Generators for 2026 - PCMag | Y |
| exa | 2 | massive.io | Best AI Video Generator: An Updated Comparison Of  | Y |
| exa | 3 | zapier.com | The 18 best AI video generators in 2026 - Zapier | Y |

### `video editing ai`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | canva.com | AI Video Editor - Create & Edit Videos with AI - C | Y |
| serper | 2 | invideo.io | Free AI Video Editor - Edit Videos with AI - Invid | Y |
| serper | 3 | adobe.com | AI Video Editor | Online Video Editing - Adobe | Y |
| brave | 1 | invideo.io | Free AI Video Editor - Edit Videos with AI | Invid | Y |
| brave | 2 | canva.com | AI Video Editor - Create & Edit Videos with AI | C | Y |
| brave | 3 | adobe.com | AI Video Editor | Online Video Editing – Adobe | Y |
| tavily | 1 | reddit.com | Which video editing AI tool is the best? : r/Artif |  |
| tavily | 2 | editorskeys.com | AI-Powered Editing: How Artificial Intelligence is | Y |
| tavily | 3 | vmaker.com | Award Winning AI Video Editor: Free & Online - Vma | Y |
| exa | 1 | scenery.video | Scenery video editor | AI-powered video editing fo | Y |
| exa | 2 | youtube.com | Best AI Video Editing Tools in 2026 (Don't Choose  |  |
| exa | 3 | canva.com | AI Video Editor - Create & Edit Videos with AI - C | Y |

### `realistic voice generator`

| 引擎 | # | 域名 | 标题 | AI? |
|---|---|---|---|---|
| serper | 1 | wellsaid.io | Most Realistic AI Voice Generator | WellSaid | Y |
| serper | 2 | reddit.com | I tested 3 AI voice tools — this one was the most  |  |
| serper | 3 | elevenlabs.io | ElevenLabs: Free AI Voice Generator & Voice Agents | Y |
| brave | 1 | speechgen.io | Realistic Text to Speech converter & AI Voice gene | Y |
| brave | 2 | naturalreaders.com | Free Text to Speech with Gemini and ChatGPT AI Voi | Y |
| brave | 3 | adobe.com | AI Text to Speech: Realistic AI Voice Generator | Y |
| tavily | 1 | poppop.ai | Realistic Voice Generator: Free Online AI Text to  | Y |
| tavily | 2 | mondial3d.com | Realistic Voice Generator | Best Natural-Sounding  | Y |
| tavily | 3 | acoust.io | Realistic AI Voice Generator | Acoust AI | Y |
| exa | 1 | reddit.com | I tested 3 AI voice tools — this one was the most  |  |
| exa | 2 | elevenlabs.io | ElevenLabs: Free AI Voice Generator & Voice Agents | Y |
| exa | 3 | youtube.com | Best AI Voice Generator 2026 (Most Realistic) - Yo |  |
