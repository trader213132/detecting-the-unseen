// Project tracker for the website. Edit this file to update the Progress section:
//   - change a milestone's status to "done", "now" or "next" (add "doneOn" when finished)
//   - add a new entry at the TOP of `log` whenever something happens
//   - update `updated` to today's date
window.PROGRESS = {
  updated: "2026-10-15",
  deadline: { date: "2026-11-06", label: "Research Scholarship submission" },
  schedule: { from: "2026-10-08", to: "2026-11-06" },
  milestones: [
    { label: "Define the experiment and check every source", from: "2026-10-08", to: "2026-10-11", status: "done", doneOn: "2026-10-08" },
    { label: "Build the order book and market simulator", from: "2026-10-12", to: "2026-10-18", status: "done", doneOn: "2026-10-08" },
    { label: "Rule, PCA and Isolation Forest baselines", from: "2026-10-19", to: "2026-10-25", status: "done", doneOn: "2026-10-08" },
    { label: "Sequence detectors, including an LSTM autoencoder", from: "2026-10-19", to: "2026-11-01", status: "done", doneOn: "2026-10-08" },
    { label: "Robustness: other markets, finer time, single orders", from: "2026-10-26", to: "2026-11-01", status: "done", doneOn: "2026-10-08" },
    { label: "Part 2: the ladder of teaching (examples, pattern, principle)", from: "2026-10-09", to: "2026-10-16", status: "done", doneOn: "2026-10-09" },
    { label: "Part 3: the price of evasion, and the research report", from: "2026-10-11", to: "2026-10-18", status: "done", doneOn: "2026-10-11" },
    { label: "Parts 4 and 5: an AI challenger, adaptive thresholds and the alert budget", from: "2026-10-12", to: "2026-10-19", status: "done", doneOn: "2026-10-12" },
    { label: "Understand every part of the code well enough to explain it", from: "2026-10-09", to: "2026-10-23", status: "now" },
    { label: "Write the proposal in my own words", from: "2026-10-24", to: "2026-11-03", status: "next" },
    { label: "Practise explaining the results out loud", from: "2026-10-30", to: "2026-11-05", status: "next" },
    { label: "Proofread and submit", from: "2026-11-05", to: "2026-11-06", status: "next" }
  ],
  log: [
    {
      date: "2026-10-15",
      title: "A new question: will AI traders learn to manipulate on their own?",
      text: "Six AI traders learned by trial and error to fill client orders at a good price, three of them fined whenever surveillance flagged them. All six learned ordinary, honest execution; none learned to spoof. A hand-built spoof was not reliably profitable in this market once the risk of its fake order trading was counted. An earlier published study (Byrd, 2022) did find learned spoofing, so whether AI discovers manipulation depends on whether the market makes it pay after its risks."
    },
    {
      date: "2026-10-14",
      title: "Part 6: the price of a false alarm",
      text: "Turned the last gap into a curve: for every alert threshold, the best payoff a spoofer can keep. Against the original legal definition the decoy keeps everything at every false-alarm rate, and layering beats the rule at every rate. Against the refined definition the curve falls, and from about 1% false alarms spoofing stops paying. The fix turned a loophole no threshold could close into a trade-off a regulator can set."
    },
    {
      date: "2026-10-12",
      title: "Parts 4 and 5: a search program attacks the detector, and the alert budget",
      text: "Wrote a challenger: a genetic search over seven spoofing settings that tries to profit without being caught. It gamed my scoring twice before finding a real loophole: a large decoy order on the other side, too far from the price for traders to see, cancels the wall out of the legal definition's 'on balance' sums. Weighing each order by how visible it is, and leaving out orders at the best price, closed it and also stopped an honest market maker being flagged (98% to 0%). Adaptive thresholds cut volatile-market false alarms but did not help tell spoofs from honest orders. Counting alerts showed the base-rate problem: if a large spoof happens once in ten sessions, a quarter of the best detector's alerts are real. Combining both versions of the definition did not close the last gap (a spoof small enough to sit under the threshold) and quadrupled false alarms."
    },
    {
      date: "2026-10-11",
      title: "Part 3: every dodge costs the spoofer its gain, and a written report",
      text: "Gave the spoofer two dodges. Waiting before pulling the wall beat fixed time windows (92% caught fell to 29%), so the detector now judges each withdrawn order over its own life, which caught 78% of even the most patient spoofers with no extra false alarms. Buying back what was sold escaped only by leaving the spoofer worse off than an honest trader. Wrote the research report, added a Research Lab, and split the website into chapters."
    },
    {
      date: "2026-10-09",
      title: "Part 2: a detector built from the law catches what examples and rules miss",
      text: "Gave detectors four levels of teaching: nothing, labelled examples, the rule, and the legal definition (orders that show interest, are withdrawn rather than traded, while the same account trades the other way). Examples and the rule learned what spoofs look like and missed layered spoofs. The definition, with no examples, caught single-wall and layered spoofs alike and flagged no honest large orders; an untaught model given the same account data caught none. Nothing could tell a spoof from an honest change of mind."
    },
    {
      date: "2026-10-08",
      title: "Even order by order, honest orders look stranger than spoofs",
      text: "An Isolation Forest trained on every individual order (size, lifetime, fraction traded, distance from the best price) ranked every honest large order above every spoof. A spoof is unusual only in its size; its quick cancellation looks like ordinary market-making."
    },
    {
      date: "2026-10-08",
      title: "Robustness: four more markets and a finer view of time",
      text: "The central finding, that untaught detectors cannot tell spoofs from honest orders, held in every market. One claim failed (plain PCA catches more spoofs in some markets, but flags honest orders just as often). Recomputing features every step did not help the sequence detectors."
    },
    {
      date: "2026-10-08",
      title: "Sequence detectors and an LSTM autoencoder",
      text: "Detectors that read the last 8 bars did no better than single-bar ones, and a shuffle test showed they ignore the order of events. Threshold-free AUC showed they find honest large orders more unusual than spoofs."
    },
    {
      date: "2026-10-08",
      title: "First results: the hypothesis is not supported",
      text: "Label-free detectors barely beat chance. The rule catches every large single-wall spoof but only 8% once the same order is layered."
    },
    {
      date: "2026-10-08",
      title: "Replaced the Bristol Stock Exchange with a purpose-built simulator",
      text: "BSE allows one order per trader and only single-lot orders, so a large spoof order was impossible. The new order book supports multi-lot orders, cancellations, and traders who react to the book."
    }
  ],
  plan: [
    { when: "Year 12, autumn", what: "Attack the principle detector: a spoofer who splits orders across linked accounts, or trades a little on the wall's side to look genuine. What does evading it cost the spoofer?" },
    { when: "Year 12, spring", what: "An adaptive spoofer that changes its pattern to evade each detector. How quickly does each one fall behind?" },
    { when: "Year 12, summer", what: "Compare the simulated market with real order-book data (the FI-2010 benchmark), and check whether quick cancellation is as ordinary there as here." },
    { when: "Year 13", what: "Extend to wash trading using graph methods, and write up the full study." }
  ]
};
