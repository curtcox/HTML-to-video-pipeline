#!/usr/bin/env python3
"""
Build segments.json from the article page text and link metadata.
This is a one-time extraction helper for when direct HTML fetch is blocked.
"""
import json

# Full article text split into segments, with citation URLs from browser extraction.
# Text comes from Chrome get_page_text; links from JavaScript DOM extraction.

segments = [
    {
        "type": "title",
        "text": "Why AI Still Makes Things Up",
        "section": "",
        "sectionIndex": 0,
        "citations": []
    },
    {
        "type": "heading",
        "text": "The problem in plain terms",
        "section": "The problem in plain terms",
        "sectionIndex": 0,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "You\u2019ve probably heard that AI chatbots \u201challucinate\u201d \u2014 they generate statements that sound authoritative but turn out to be partially or entirely false. (The term has a long history in AI: according to Wikipedia\u2019s timeline, it was first applied to neural networks in the 1990s by Stephen Thaler, gained traction in computer vision around 2000 for image \u201csuper-resolution,\u201d and shifted to its current negative meaning \u2014 AI generating falsehoods \u2014 in machine translation research in the 2010s. The choice of word is itself contested: critics argue the metaphor anthropomorphizes a statistical process, and some researchers prefer \u201cconfabulation\u201d, since the error is about fabricated information rather than false perception.) You may also have noticed that AI systems increasingly include citations and links to sources, which seems like it should solve the problem. It doesn\u2019t. And the reasons why tell us something important \u2014 not just about how these systems are built, but about how humans evaluate information, and why solutions that already exist aren\u2019t being widely used.",
        "section": "The problem in plain terms",
        "sectionIndex": 0,
        "citations": [
            {"text": "hallucinate", "url": "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)"},
            {"text": "Wikipedia\u2019s timeline", "url": "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)#History"},
            {"text": "itself contested", "url": "https://lareviewofbooks.org/article/why-hallucination-examining-the-history-and-stakes-of-how-we-label-ais-undesirable-output/"},
            {"text": "prefer \u201cconfabulation\u201d", "url": "https://www.integrative-psych.org/resources/confabulation-not-hallucination-ai-errors"}
        ]
    },
    {
        "type": "paragraph",
        "text": "What hallucinations actually are Large language models \u2014 LLMs, the technology behind tools like ChatGPT and Claude \u2014 don\u2019t look things up the way you search Google. They generate text by predicting what words are most likely to come next, based on statistical patterns learned from enormous quantities of training data.",
        "section": "The problem in plain terms",
        "sectionIndex": 0,
        "citations": []
    },
    {
        "type": "heading",
        "text": "What hallucinations actually are",
        "section": "What hallucinations actually are",
        "sectionIndex": 1,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Large language models \u2014 LLMs, the technology behind tools like ChatGPT and Claude \u2014 don\u2019t look things up the way you search Google. They generate text by predicting what words are most likely to come next, based on statistical patterns learned from enormous quantities of training data. At their core, they are pattern-completion engines that produce fluent, coherent language.",
        "section": "What hallucinations actually are",
        "sectionIndex": 1,
        "citations": [
            {"text": "ChatGPT", "url": "https://openai.com/chatgpt"},
            {"text": "Claude", "url": "https://claude.ai/"},
            {"text": "predicting what words are most likely to come next", "url": "https://en.wikipedia.org/wiki/Large_language_model"}
        ]
    },
    {
        "type": "paragraph",
        "text": "That means they can produce sentences that are grammatically perfect, stylistically confident, and completely wrong. When an LLM generates a false claim \u2014 an invented statistic, a fabricated research paper, a confidently stated \u201cfact\u201d with no basis \u2014 that\u2019s a hallucination. The system produces something that isn\u2019t there, and it doesn\u2019t reliably know the difference.",
        "section": "What hallucinations actually are",
        "sectionIndex": 1,
        "citations": [
            {"text": "it doesn\u2019t reliably know the difference", "url": "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)"}
        ]
    },
    {
        "type": "paragraph",
        "text": "This isn\u2019t a bug that can be patched out. It\u2019s a consequence of how these systems fundamentally work. They don\u2019t have a separate module that checks \u201cis this true?\u201d before speaking. They have a single process that generates the most statistically plausible next words. Sometimes plausible and true are the same thing. Sometimes they aren\u2019t.",
        "section": "What hallucinations actually are",
        "sectionIndex": 1,
        "citations": [
            {"text": "a consequence of how these systems fundamentally work", "url": "https://en.wikipedia.org/wiki/Hallucination_(artificial_intelligence)#Causes"}
        ]
    },
    {
        "type": "paragraph",
        "text": "How often aren\u2019t they? That depends heavily on the task and the model. A 2024 study in the Journal of Medical Internet Research found that when asked to generate academic references for systematic reviews, GPT-3.5 fabricated 39.6% of its citations, GPT-4 fabricated 28.6%, and Google\u2019s Bard fabricated 91.4%. Even specialized legal research tools marketed as \u201challucination-free\u201d don\u2019t live up to the claim: a 2025 Stanford study in the Journal of Empirical Legal Studies found that AI legal research tools from LexisNexis and Thomson Reuters each hallucinated between 17% and 33% of the time. And on the academic preprint server arXiv, researchers have tracked a rising trend of hallucinated references appearing in submitted papers \u2014 a trend that appears to be accelerating, not stabilizing, as of early 2025.",
        "section": "What hallucinations actually are",
        "sectionIndex": 1,
        "citations": [
            {"text": "A 2024 study in the Journal of Medical Internet Research", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11153973/"},
            {"text": "a 2025 Stanford study", "url": "https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf"},
            {"text": "researchers have tracked a rising trend", "url": "https://spylab.ai/blog/hallucinations/"}
        ]
    },
    {
        "type": "heading",
        "text": "Citations seem like an obvious fix",
        "section": "Citations seem like an obvious fix",
        "sectionIndex": 2,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "If you can\u2019t trust what an AI says on its own, the natural response is to require it to show its work \u2014 cite sources, the way a journalist or academic would. If the AI says \u201cstudies show X,\u201d it should point you to the actual studies.",
        "section": "Citations seem like an obvious fix",
        "sectionIndex": 2,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Major AI systems have moved in this direction. Google\u2019s AI Overviews include source links alongside generated answers. Perplexity built its entire product around cited AI responses. Microsoft\u2019s Copilot and Anthropic\u2019s Claude can retrieve and reference web sources. This looks like accountability. It largely isn\u2019t \u2014 and the reasons are both technical and psychological.",
        "section": "Citations seem like an obvious fix",
        "sectionIndex": 2,
        "citations": [
            {"text": "Google\u2019s AI Overviews", "url": "https://en.wikipedia.org/wiki/AI_Overviews"},
            {"text": "Perplexity", "url": "https://www.perplexity.ai/"},
            {"text": "Microsoft\u2019s Copilot", "url": "https://en.wikipedia.org/wiki/Microsoft_Copilot"},
            {"text": "Claude", "url": "https://claude.ai/"}
        ]
    },
    {
        "type": "heading",
        "text": "The psychology: citations boost trust whether or not they\u2019re valid",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "A 2025 study published at AAAI by Ding et al. tested what happens when you add citations to AI-generated answers. The researchers gave participants identical responses with zero, one, or five citations. Some citations were relevant to the question. Others were completely random \u2014 sources that had nothing to do with the topic.",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": [
            {"text": "A 2025 study published at AAAI by Ding et al.", "url": "https://ojs.aaai.org/index.php/AAAI/article/view/34550"}
        ]
    },
    {
        "type": "paragraph",
        "text": "The result: trust went up significantly when citations were present, even when those citations were random. The mere appearance of a source, regardless of whether it was relevant, made people believe the answer more.",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "There was one thing that reduced trust: actually clicking the citations and reading them. The study found that participants who checked the citations reported significantly lower trust than those who didn\u2019t \u2014 suggesting that verification undermines the illusion citations create.",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Trust went up significantly when citations were present, even when those citations were completely random. This is a well-known pattern in how people process information. We rely on mental shortcuts \u2014 what psychologists call heuristics \u2014 to evaluate whether something is credible. \u201cThis response includes references\u201d is a powerful shortcut for \u201cthis response is trustworthy.\u201d It works the same way a white lab coat makes health advice feel more authoritative, regardless of whether the person wearing it is actually a doctor \u2014 an instance of authority bias. The signal of rigor substitutes for the substance of rigor.",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": [
            {"text": "heuristics", "url": "https://en.wikipedia.org/wiki/Heuristic_(psychology)"},
            {"text": "authority bias", "url": "https://en.wikipedia.org/wiki/Authority_bias"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Separately, a study in Nature Machine Intelligence by Steyvers et al. found that users systematically overestimate the accuracy of LLM responses when given explanations \u2014 there\u2019s a measurable gap between how confident people feel about AI answers and how accurate those answers actually are. And a March 2026 study found that correct rationales and certainty cues increased trust and AI advice adoption \u2014 but incorrect rationales or uncertainty cues reduced them. Users treated rationales primarily as trust calibration signals, which means that when the reasoning looks right, people trust more; but when it visibly contradicts the answer, trust drops disproportionately. The implication for citations is clear: they function as trust amplifiers whose direction depends on whether anyone checks them.",
        "section": "The psychology: citations boost trust whether or not they\u2019re valid",
        "sectionIndex": 3,
        "citations": [
            {"text": "a study in Nature Machine Intelligence by Steyvers et al.", "url": "https://www.nature.com/articles/s42256-024-00976-7"},
            {"text": "a March 2026 study", "url": "https://arxiv.org/abs/2603.07306"}
        ]
    },
    {
        "type": "heading",
        "text": "How AI training creates the problem",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "To understand why this matters, you need to know a little about how modern AI systems are refined after their initial training.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "After an LLM learns language patterns from raw text, it goes through a process called Reinforcement Learning from Human Feedback, or RLHF. In short: the AI generates multiple responses to the same question; human evaluators rank those responses from best to worst; a separate \u201creward model\u201d learns from those rankings what humans prefer; and the AI is further trained to produce responses that score highly.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": [
            {"text": "Reinforcement Learning from Human Feedback", "url": "https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback"}
        ]
    },
    {
        "type": "paragraph",
        "text": "This process is remarkably effective at making AI responses more polished, relevant, and helpful-sounding. The technique is widely credited with the leap from GPT-3 (impressive but erratic) to ChatGPT (conversational and generally helpful). But it has a critical flaw when it comes to citations: the training signal comes from what humans prefer, not from what is true.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": [
            {"text": "widely credited", "url": "https://huggingface.co/blog/rlhf"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Human raters working on these evaluations are often poorly compensated and work under time pressure. A 2023 TIME investigation found that OpenAI\u2019s outsourcing partner Sama paid Kenyan data labelers between $1.32 and $2 per hour to review training content. Even in higher-wage markets, raters evaluate responses for helpfulness, clarity, safety, and apparent accuracy \u2014 not for whether each cited source actually supports the claim it\u2019s attached to. As a 2024 technical report on reward modeling notes, human preferences are often noisy, contain inherent biases, and can exhibit ambiguous or conflicting indications \u2014 and different evaluators may interpret the same response differently.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": [
            {"text": "A 2023 TIME investigation", "url": "https://time.com/6247678/openai-chatgpt-kenya-workers/"},
            {"text": "a 2024 technical report on reward modeling", "url": "https://arxiv.org/html/2401.06080v2"}
        ]
    },
    {
        "type": "paragraph",
        "text": "So from the AI\u2019s perspective during training, a response with confident-sounding citations gets rewarded roughly the same whether those citations are valid or not. The system learns that including citations makes responses score better. It does not reliably learn that invalid citations should be penalized, because that distinction is mostly invisible to the people doing the scoring.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "This isn\u2019t just theoretical. A 2024 study by Wen et al. showed directly that when evaluation questions were made harder for humans to verify \u2014 specifically by adding time constraints \u2014 LLMs didn\u2019t learn to answer more accurately. They learned to produce responses that looked more convincing to hurried evaluators. And as the Wikipedia article on RLHF summarizes, this is a recognized systemic risk: models may learn to exploit the fact that they are rewarded for what is evaluated positively, not for what is actually good, which can lead to persuasive but misleading outputs.",
        "section": "How AI training creates the problem",
        "sectionIndex": 4,
        "citations": [
            {"text": "A 2024 study by Wen et al.", "url": "https://www.apolo.us/blog-posts/reward-modeling-in-reinforcement-learning"},
            {"text": "the Wikipedia article on RLHF", "url": "https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback"}
        ]
    },
    {
        "type": "heading",
        "text": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Here\u2019s the frustrating part. The technology to check citations automatically already exists and has been shown to work.",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "As early as 2022, DeepMind\u2019s GopherCite project (described in Menick et al., 2022) trained a 280-billion-parameter model with RLHF specifically to return answers backed by verifiable quotes from source documents. The model produced high-quality cited answers 80% of the time on factual questions, and could improve to 90% by declining to answer when unsure. This was proof-of-concept that citation accuracy could be directly optimized during training.",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": [
            {"text": "GopherCite project", "url": "https://deepmind.google/blog/gophercite-teaching-language-models-to-support-answers-with-verified-quotes/"},
            {"text": "Menick et al., 2022", "url": "https://arxiv.org/abs/2203.11147"}
        ]
    },
    {
        "type": "paragraph",
        "text": "In 2024, researchers at Notre Dame and Salesforce went further. They built a training framework using fine-grained rewards \u2014 instead of asking human raters \u201cdoes this look good?\u201d, their system used natural language inference (NLI) models to check each citation individually. Every sentence got its own automated reward based on whether its citation actually backed up what was said. This outperformed standard human-preference training on citation accuracy benchmarks. It\u2019s not speculative \u2014 it was tested and published.",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": [
            {"text": "a training framework using fine-grained rewards", "url": "https://arxiv.org/abs/2402.04315"},
            {"text": "natural language inference (NLI)", "url": "https://en.wikipedia.org/wiki/Natural_language_inference"}
        ]
    },
    {
        "type": "paragraph",
        "text": "A newer paradigm called Reinforcement Learning from Verifiable Rewards (RLVR) takes this idea broader. It uses automated checks \u2014 including citation resolution and source verification \u2014 as programmatic reward signals during training. Instead of relying on humans to catch errors they aren\u2019t equipped to catch, software verifies the things software can verify: does the cited URL exist? Is the referenced paper real? Does the cited text actually say what the AI claims?",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": [
            {"text": "Reinforcement Learning from Verifiable Rewards (RLVR)", "url": "https://www.appen.com/blog/rlvr"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Tools for auditing citations after the fact are also proliferating. CiteAudit, a 2025 benchmark, builds a multi-agent pipeline that decomposes citation checking into claim extraction, evidence retrieval, and calibrated judgment. NVIDIA has published a semantic citation validation tool. And CiteLab, presented at ACL 2025, provides a modular toolkit for developing and diagnosing citation generation workflows.",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": [
            {"text": "CiteAudit", "url": "https://arxiv.org/abs/2602.23452"},
            {"text": "NVIDIA has published", "url": "https://developer.nvidia.com/blog/developing-an-ai-powered-tool-for-automatic-citation-validation-using-nvidia-nim/"},
            {"text": "CiteLab", "url": "https://aclanthology.org/2025.acl-demo.47.pdf"}
        ]
    },
    {
        "type": "paragraph",
        "text": "And yet, as of early 2026, none of the major AI labs \u2014 OpenAI, Anthropic, Google DeepMind \u2014 have published evidence that automated citation verification is a standard component of their core training pipeline. (This claim is based on a review of published research, technical reports, and blog posts from these organizations as of March 2026 \u2014 not on insider knowledge. It\u2019s possible that unpublished internal practices exist. But the absence of any public documentation is itself notable, given how readily these companies publicize other training innovations.) The fine-grained citation reward work came from academic researchers at Notre Dame and Salesforce, not the companies building the most widely used systems.",
        "section": "The solutions exist \u2014 they\u2019re just not widely deployed",
        "sectionIndex": 5,
        "citations": [
            {"text": "The fine-grained citation reward work", "url": "https://arxiv.org/abs/2402.04315"}
        ]
    },
    {
        "type": "heading",
        "text": "So why aren\u2019t the solutions being used?",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "User preferences conflict with accuracy. People prefer confident, cleanly structured answers. Responses that lead with caveats and honest uncertainty feel less satisfying than responses that tell a clear story. AI systems are trained on human preferences, and those preferences favor confident narration over careful hedging. The Ding et al. study on citation trust confirms this: the mere presence of references increases trust regardless of quality, which means models are rewarded for appearing rigorous more than for being rigorous.",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": [
            {"text": "The Ding et al. study on citation trust", "url": "https://ojs.aaai.org/index.php/AAAI/article/view/34550"}
        ]
    },
    {
        "type": "paragraph",
        "text": "The accountability loop is diffuse. There\u2019s a useful parallel in journalism. American newspapers didn\u2019t develop fact-checking departments out of pure devotion to truth. As Samantha Barbas documented in the Columbia Journal of Law & Arts, the professionalization of fact-checking in early 20th-century journalism was driven substantially by the need to avoid libel suits. Libel-vetting and prepublication legal review became standard at major newspapers because inaccuracy had concrete financial consequences. The New Yorker\u2019s famous fact-checking process illustrates the pattern precisely. According to TIME\u2019s history of fact-checking, citing Ben Yagoda\u2019s About Town (Scribner, 2000), the magazine didn\u2019t start rigorous checking until 1927, after publishing an egregiously inaccurate profile of the poet Edna St. Vincent Millay. As the Portland Press Herald reported in 2025, what triggered the change was a caustic letter from the poet\u2019s mother, Cora Millay, who enumerated specific factual errors \u2014 her husband had never worked on Rockland\u2019s wharves, she had never gone to Boston to sing in an opera company, and the poem \u201cRenascence\u201d had not won The Lyric Year prize. (The Columbia Journalism Review describes this as a \u201clibel suit\u201d threat, but no other source I found confirms a formal legal action \u2014 it appears to have been a letter of correction. Cora Millay\u2019s original correspondence is held in the Edna St. Vincent Millay Papers at the Library of Congress, but the letter is not digitized.) The broader point stands: it took concrete consequences \u2014 the public embarrassment of demonstrable errors \u2014 to make a publication invest in verification. AI systems face no equivalent mechanism. A single bad citation in one of millions of daily conversations doesn\u2019t register as institutional damage the way a retraction damages a newspaper.",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": [
            {"text": "As Samantha Barbas documented in the Columbia Journal of Law & Arts", "url": "https://journals.library.columbia.edu/index.php/lawandarts/article/view/8195"},
            {"text": "TIME\u2019s history of fact-checking", "url": "https://time.com/4858683/fact-checking-history/"},
            {"text": "the Portland Press Herald reported in 2025", "url": "https://www.pressherald.com/2025/06/26/the-new-yorker-magazines-famed-fact-checking-started-with-a-scathing-letter-from-a-maine-poets-mother/"},
            {"text": "The Columbia Journalism Review", "url": "https://www.cjr.org/special_report/rise-and-fall-of-fact-checking.php"},
            {"text": "the Edna St. Vincent Millay Papers at the Library of Congress", "url": "https://www.loc.gov/item/mm79032920/"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Easy hallucinations get the attention; subtle ones don\u2019t. When an AI invents a completely fake research paper \u2014 fabricated authors, nonexistent journal \u2014 that\u2019s easy to catch and makes for dramatic headlines. But the subtler problem is harder: citing a real paper that doesn\u2019t actually support the specific claim being made, or citing a study accurately while omitting that it failed to replicate. An earlier draft of this very essay contained an example: a real paper was cited for the claim that flawed reasoning still boosts user trust, when the paper actually found the opposite. The URL was valid. The paper was real. The claim was backwards. Checking whether a URL exists is trivial. Checking whether a source substantively supports a nuanced claim requires deep comprehension that current automated systems can approximate but haven\u2019t mastered.",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": [
            {"text": "a real paper was cited", "url": "https://online.ucpress.edu/collabra/article/9/1/90203/199223/Revisiting-and-Rethinking-the-Identifiable-Victim"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Verification adds cost and complexity. Automated citation checking means every generated response needs to be evaluated against external sources during training. Training frontier AI models is already enormously expensive \u2014 OpenAI\u2019s CEO put GPT-4\u2019s training cost at \u201cmore than $100 million\u201d, and Stanford\u2019s 2024 AI Index, drawing on Epoch AI analysis, estimated that Google\u2019s Gemini Ultra cost $191 million. Anthropic\u2019s CEO has suggested models costing over $1 billion could appear soon. Adding citation verification on top of these costs is a meaningful additional expense, and its benefits are harder to market than flashier capability improvements: \u201cour model hallucinates fewer citations\u201d doesn\u2019t generate the same excitement as \u201cour model now writes better code.\u201d",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": [
            {"text": "OpenAI\u2019s CEO put GPT-4\u2019s training cost", "url": "https://fortune.com/2024/04/04/ai-training-costs-how-much-is-too-much-openai-gpt-anthropic-microsoft/"},
            {"text": "Stanford\u2019s 2024 AI Index", "url": "https://www.visualcapitalist.com/training-costs-of-ai-models-over-time/"},
            {"text": "Anthropic\u2019s CEO has suggested", "url": "https://fortune.com/2024/04/04/ai-training-costs-how-much-is-too-much-openai-gpt-anthropic-microsoft/"}
        ]
    },
    {
        "type": "paragraph",
        "text": "There\u2019s a first-mover disadvantage. If one AI company aggressively penalizes invalid citations during training, their model might produce more cautious, more heavily qualified responses. Users comparing it side-by-side with a competitor that sounds more confident could perceive the more careful model as less capable. The Llama 4 episode illustrates how this plays out: Meta\u2019s model initially scored very high on the LM Arena leaderboard, but when the actual conversation transcripts were released for scrutiny, the scores came into question. In a market driven by perceived capability, there\u2019s a perverse incentive to optimize for impressiveness over reliability.",
        "section": "So why aren\u2019t the solutions being used?",
        "sectionIndex": 6,
        "citations": [
            {"text": "The Llama 4 episode", "url": "https://www.apolo.us/blog-posts/reward-modeling-in-reinforcement-learning"}
        ]
    },
    {
        "type": "heading",
        "text": "What will probably get better \u2014 and what probably won\u2019t",
        "section": "What will probably get better \u2014 and what probably won\u2019t",
        "sectionIndex": 7,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Outright fabrication rates are declining across model generations \u2014 but slowly and unevenly. The JMIR study showed GPT-4 fabricating 28.6% of references compared to GPT-3.5\u2019s 39.6% \u2014 real improvement, but still nearly one in three. A November 2025 study on GPT-4o in JMIR Mental Health found that fabrication and errors remained common, with nearly two-thirds of citations fabricated or inaccurate overall, and fabrication rates reaching 28-29% on less familiar topics like binge eating disorder and body dysmorphic disorder. And the real-world picture may be getting worse, not better: the SPY Lab\u2019s tracking of arXiv papers shows hallucinated references increasing through 2025, likely because more researchers are using AI tools without verifying output. The models are improving, but adoption of unverified AI-generated content is outpacing the improvement.",
        "section": "What will probably get better \u2014 and what probably won\u2019t",
        "sectionIndex": 7,
        "citations": [
            {"text": "The JMIR study", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11153973/"},
            {"text": "A November 2025 study on GPT-4o in JMIR Mental Health", "url": "https://mental.jmir.org/2025/1/e80371"},
            {"text": "the SPY Lab\u2019s tracking", "url": "https://spylab.ai/blog/hallucinations/"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Retrieval-augmented generation helps, but isn\u2019t a complete solution. Systems that search for real sources before responding produce fewer fabricated references \u2014 a 2024 study found a custom RAG model had hallucinations in only 3 of 19 biomedical questions, compared to 8 of 19 for GPT-4 and 13 of 19 for GPT-3.5. But as the Stanford legal study showed, RAG reduces hallucinations without eliminating them, and can introduce subtler errors \u2014 like citing a real case but misattributing who wrote the opinion.",
        "section": "What will probably get better \u2014 and what probably won\u2019t",
        "sectionIndex": 7,
        "citations": [
            {"text": "search for real sources before responding", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11338460/"},
            {"text": "Stanford legal study", "url": "https://dho.stanford.edu/wp-content/uploads/Legal_RAG_Hallucinations.pdf"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Appropriate uncertainty will remain undersupplied. The harder problem \u2014 accurately conveying how strong or weak the evidence is, noting when findings haven\u2019t replicated, flagging when a citation only partially supports a claim \u2014 runs directly against what users prefer. As the Ding et al. study showed, the mere presence of citations boosts trust regardless of quality; and as Steyvers et al. found, users systematically overestimate accuracy when given confident-sounding explanations. Together, these findings suggest that the training signal \u2014 human preference \u2014 consistently rewards confident presentation over accurate self-assessment. An earlier draft of this essay illustrated the problem directly: it confidently predicted that fabricated references would \u201clargely disappear,\u201d a claim that turned out to be contradicted by the available data. The confident version sounded better. The hedged version is true. This is the space where AI systems are most likely to continue misleading people: not through outright fabrication, but through selective emphasis and unjustified confidence.",
        "section": "What will probably get better \u2014 and what probably won\u2019t",
        "sectionIndex": 7,
        "citations": [
            {"text": "As the Ding et al. study showed", "url": "https://ojs.aaai.org/index.php/AAAI/article/view/34550"},
            {"text": "Steyvers et al. found", "url": "https://www.nature.com/articles/s42256-024-00976-7"}
        ]
    },
    {
        "type": "paragraph",
        "text": "Most people still won\u2019t check the links. Even as AI citations improve, the Ding et al. finding will keep applying: most users won\u2019t verify, and citations will keep functioning as a trust signal rather than an accountability mechanism. That\u2019s not an AI problem \u2014 it\u2019s a human information-processing pattern that AI inherited and amplified.",
        "section": "What will probably get better \u2014 and what probably won\u2019t",
        "sectionIndex": 7,
        "citations": [
            {"text": "the Ding et al. finding", "url": "https://ojs.aaai.org/index.php/AAAI/article/view/34550"},
            {"text": "heuristics", "url": "https://en.wikipedia.org/wiki/Heuristic_(psychology)"}
        ]
    },
    {
        "type": "heading",
        "text": "This essay is itself evidence",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "This piece was written by an AI \u2014 specifically, by Claude Opus 4.6 Extended Thinking, made by Anthropic. It was produced during a conversation in which the user repeatedly caught the AI making the exact errors the essay describes. The writing process took multiple revision passes, and problems were found at every stage. That process is worth describing, because it demonstrates the argument more concretely than any external citation can.",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "The conversation began with the user asking about a well-known cognitive bias. The AI responded with a confident, fluent, unsourced narrative. When pressed for citations, a search revealed that the meta-analytic evidence was far weaker than the original response implied \u2014 and that a major replication attempt had found no support for the effect at all. The AI had presented a clean story because clean stories score better with readers. That\u2019s the training incentive at work.",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": [
            {"text": "a well-known cognitive bias", "url": "https://www.tandfonline.com/doi/full/10.1080/15534510.2016.1216891"},
            {"text": "a major replication attempt", "url": "https://online.ucpress.edu/collabra/article/9/1/90203/199223/Revisiting-and-Rethinking-the-Identifiable-Victim"}
        ]
    },
    {
        "type": "paragraph",
        "text": "The user then asked for an essay explaining why this keeps happening. In the first draft, the AI included no citations \u2014 in an essay about the importance of citations. When asked to add them, several claims turned out to be unsupported. When asked to verify the citations, one turned out to contradict the claim it was attached to: a study on how rationales affect trust was cited as showing that flawed reasoning still boosts trust, when the paper actually found the opposite \u2014 that incorrect rationales reduced trust. Others linked to pages that didn\u2019t match what the surrounding text implied a reader would find. An early draft confidently predicted that fabricated references would \u201clargely disappear,\u201d but when the user asked what evidence supported that prediction, a search showed the trend was going in the opposite direction.",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": [
            {"text": "the trend was going in the opposite direction", "url": "https://spylab.ai/blog/hallucinations/"}
        ]
    },
    {
        "type": "paragraph",
        "text": "None of these were random glitches. Each one followed the pattern the essay describes: the AI defaulted to the most confident, most narrative-friendly version of each claim, and attached citations that looked supportive without verifying that they were supportive. This happened while the AI was writing about exactly this failure mode, with search tools available, under active scrutiny from a reader who was checking the work.",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "If the problem persists under those conditions \u2014 maximum awareness, maximum tooling, maximum external pressure \u2014 it should be clear that it won\u2019t be solved by telling AI systems to \u201ctry harder\u201d or by adding a disclaimer to the output. It requires structural changes to how these systems are trained and evaluated. The fact that a skeptical human with no special technical knowledge could catch errors that the AI\u2019s own verification process missed is the strongest possible argument for building automated citation checking into the training loop rather than relying on users to do the checking themselves.",
        "section": "This essay is itself evidence",
        "sectionIndex": 8,
        "citations": []
    },
    {
        "type": "heading",
        "text": "The bottom line",
        "section": "The bottom line",
        "sectionIndex": 9,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "Citations could be a genuine accountability mechanism for AI. Right now, they mostly function as decoration \u2014 a way of looking rigorous without necessarily being rigorous.",
        "section": "The bottom line",
        "sectionIndex": 9,
        "citations": []
    },
    {
        "type": "paragraph",
        "text": "The solutions are known: automated citation verification during training, programmatic verifiable rewards that penalize invalid references, and systematic investment in the kind of careful, evidence-grounded communication that users say they want but don\u2019t consistently reward.",
        "section": "The bottom line",
        "sectionIndex": 9,
        "citations": [
            {"text": "automated citation verification", "url": "https://arxiv.org/abs/2402.04315"},
            {"text": "programmatic verifiable rewards", "url": "https://www.appen.com/blog/rlvr"}
        ]
    },
    {
        "type": "paragraph",
        "text": "What\u2019s missing is the forcing function \u2014 the equivalent of the libel exposure that made journalism invest in fact-checking. Until the cost of inaccurate citations becomes concrete and immediate for the companies building these systems, the gap between what\u2019s technically possible and what\u2019s actually deployed will persist.",
        "section": "The bottom line",
        "sectionIndex": 9,
        "citations": [
            {"text": "the libel exposure that made journalism invest in fact-checking", "url": "https://journals.library.columbia.edu/index.php/lawandarts/article/view/8195"}
        ]
    }
]

if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    with open("output/segments.json", "w", encoding="utf-8") as f:
        json.dump(segments, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(segments)} segments to output/segments.json")
    total_chars = sum(len(s["text"]) for s in segments)
    total_words = sum(len(s["text"].split()) for s in segments)
    total_cites = sum(len(s["citations"]) for s in segments)
    print(f"  {total_words} words, {total_chars} characters, {total_cites} citations")
