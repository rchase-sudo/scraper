# Forma Designs — Cold Outreach Sequence

Merge tags below match the columns in `output/instantly_import_*.csv` exactly
— paste straight into an Instantly.ai campaign, no renaming needed.

---

## Email 1: Initial offer

**Subject:** Concept plan for your listing at {{listing_address}}

Hi {{first_name}},

I came across your listing at {{listing_address}} and put together a
preliminary development concept plan for it, showing potential site layout
and buildable area. I do this for land listings specifically, since a visual
concept plan often helps buyers see the potential faster and can support a
stronger asking price.

I can send you the full concept plan and due diligence package for this
parcel for $200, normally priced much higher. Want me to send it over?

Apollo Forma Designs

---

## Email 2: Follow-up (send a few days after Email 1)

**Subject:** Following up - {{listing_address}}

Hi {{first_name}},

Just following up on the concept plan offer for your listing at
{{listing_address}}. Since it's just $200, most agents treat it as a
no-brainer addition to their listing packet. It usually takes me a day or
two to turn around once you say go.

Happy to send a sample of a completed package if that helps you decide.

Apollo Forma Designs

---

## Email 3: Breakup (send a few days after Email 2)

**Subject:** Should I close this out?

Hi {{first_name}},

Haven't heard back, so I'll assume the timing's not right. If that changes
and you want a concept plan for {{listing_address}}, just reply and I'll get
it moving.

Best of luck with the sale.

Apollo Forma Designs

---

**Note:** if an agent has multiple qualifying listings (`{{num_listings}}` > 1
in the CSV), the emails above only reference their highest-price listing
(`{{listing_address}}`). `{{other_listings}}` is available in the CSV if you
want a 4th variant that mentions "and your other listings at X" — not built
here since the pasted sequence only used one listing per email.
