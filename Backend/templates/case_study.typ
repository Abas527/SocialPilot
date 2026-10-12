// Content is read from data.json, so model text never needs Typst escaping.
#let d = json("data.json")
#set page(margin: 2.2cm, numbering: "1",
  footer: context [#align(center)[#text(size: 8pt, fill: gray)[#d.footer \u{2022} Page #counter(page).display()]]])
#set text(size: 11pt)
#set par(justify: true, leading: 0.7em)
#show heading.where(level: 2): set text(size: 14pt)

#text(size: 22pt, weight: "bold")[#d.title]
#v(0.3em)
#text(fill: gray)[#d.meta]
#v(1em)
#for s in d.sections [
  == #s.heading
  #s.body
  #v(0.6em)
]
