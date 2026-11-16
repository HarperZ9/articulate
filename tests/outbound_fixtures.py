"""Synthetic fixtures for the outbound check. Every sentence below was written
for these tests; no private text is used.

HUMAN holds six short messages in a plain human register: names, numbers,
the same noun carried from one sentence to the next, a slip or two. REWRITE
holds a model-style rewrite of each, at about the same length, made the way
the paired method makes them: the content described, then written again with
a thank-you opener, no names, vague quantities, a new abstract noun per
sentence, a softener or an ask, a colon and a sign-off.

FORMAL holds three messages from a reader who writes a formal register that
varies the noun from sentence to sentence by convention (tell 1), and
FORMAL_DRAFT is a reply written in that register.
"""

HUMAN = [
    "The ferry from Anacortes was two hours late again, so the ferry crew handed out coffee in "
    "paper cups. Marta said the late ferry is the third this month and the county still won't "
    "post the delays.. I timed it at 2 hours 14 minutes from the dock. Nobody at the dock knew why.",
    "Pulled the pump apart on Saturday and the pump seal was shot, cracked right across. Dave at "
    "Northside Hydraulics had one seal left for $38, so I took it. The old seal had 6,000 hours "
    "on it according to the log/tag. Pump runs quiet now.",
    "Our block lost power at 9:40 and the power stayed off until almost 1 am. PSE said a tree "
    "came down on the line on 4th and Pine, the same tree they were warned about in March. The "
    "tree was leaning for a year. I called it in twice.",
    "Read the Hendricks paper on soil cores last night and the cores they pulled are from 1,200 "
    "meters, not 120 like the abstract says. The abstract is wrong or the table is wrong. Table 3 "
    "has the depth at 1,200 in every row. Somebody should email Hendricks about it.",
    "the bus to Ballard skipped our stop three times this week, and the bus driver on Thursday "
    "just waved. Route 40 is supposed to come every 12 minutes. I waited 31 minutes Friday. "
    "Metro's app said the bus was arriving the whole time.",
    "Got the sourdough starter from Lena on Sunday and the starter doubled in 6 hours, which is "
    "way faster than mine ever did. Lena feeds her starter rye flour, 50 grams at a time. My "
    "starter never got rye. Switching tonight.",
]

REWRITE = [
    "Thanks for raising this. The crossing was delayed once more, and staff offered refreshments "
    "to travelers. Several similar disruptions have occurred recently: communication about "
    "schedules remains limited. One small thing worth noting is the lack of clarity at the "
    "terminal. Happy to share more details if helpful.\nBest,\nSam",
    "Thanks for checking in on the equipment. After a weekend inspection, the component showed "
    "significant deterioration. A local supplier provided a replacement at a reasonable cost: the "
    "previous part had seen extensive use. Performance has improved considerably. Let me know if "
    "you would like further information.\nCheers,\nSam",
    "Thanks for checking in. Our neighborhood experienced an extended outage overnight. The "
    "utility attributed the disruption to vegetation affecting nearby infrastructure, a concern "
    "raised previously. Despite repeated reports, the situation went unaddressed. I'd be glad to "
    "discuss next steps.\nBest,\nSam",
    "Great question. While reviewing a recent study, I noticed a discrepancy in the reported "
    "measurements. The summary and the supporting data appear inconsistent: the tables suggest a "
    "considerably greater depth. Just wanted to flag this for clarity. Could you pass this along "
    "to the authors?\nThanks,\nSam",
    "Thanks for following up. Service on the local route has been unreliable this week, with "
    "several missed stops. Scheduled frequency and actual performance differ significantly. The "
    "tracking information also proved misleading. Happy to provide documentation if that would "
    "be useful.\nBest,\nSam",
    "Lovely to hear from you. A friend kindly shared a culture that showed remarkable activity, "
    "far exceeding my previous experience. Her approach involves a different grain and careful "
    "portions. This suggests a simple adjustment: I will adopt the method going forward. Would "
    "you like me to share the results?\nCheers,\nSam",
]

FORMAL = (
    "Dear Mr Harper, the committee reviewed your proposal on Monday. The panel considered the "
    "document thorough and clear. Its members request a short summary before the meeting. "
    "Kind regards, Irina Volkova\n"
    "---\n"
    "Dear Mr Harper, the laboratory received the samples yesterday. Our technicians will process "
    "each specimen within the week. Results should reach you by Friday. Kind regards, Irina "
    "Volkova\n"
    "---\n"
    "Dear Mr Harper, I write concerning the invoice. The document lists two items. Each charge "
    "matches our earlier agreement. Please confirm receipt at your convenience. Best regards, "
    "Irina Volkova\n"
)

FORMAL_DRAFT = ("Dear Dr Volkova, the shipment left Seattle on Tuesday. The courier expects "
                "delivery within four days. Each package carries a tracking label. Best regards, "
                "Zain")
