import anthropic
import os
import re
import time
from datetime import datetime, timezone


def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    sections = [
        {
            "id": "fuel",
            "icon": "&#x26FD;",
            "title": "Jet Fuel &amp; Flight Disruptions &mdash; Panama",
            "priority": "high",
            "tag": "PRIORITY",
            "prompt": (
                f"Search for very recent news (last 2 weeks) about jet fuel shortages, "
                f"aviation fuel supply issues, or flight cancellations/disruptions at Panama's "
                f"Tocumen International Airport (PTY) or in Panama generally. Also check for any "
                f"airline operational issues, airport strikes, or air travel disruptions in Panama. "
                f"Summarize in 4-5 concise bullet points. If there are no current issues, state "
                f"that clearly. Today is {today}."
            ),
        },
        {
            "id": "panama",
            "icon": "&#x1F1F5;&#x1F1E6;",
            "title": "Panama &mdash; Travel Advisories &amp; Local News",
            "priority": "medium",
            "tag": "WATCH",
            "prompt": (
                f"Search for recent news (last 2 weeks) relevant to tourists visiting Panama. "
                f"Cover: travel advisories or safety updates, protests or road blockades, notable "
                f"weather events or flooding, border or entry requirement changes, crime trends in "
                f"tourist areas (Casco Viejo, Panama City, Bocas del Toro, Boquete), and significant "
                f"local events affecting visitors. Summarize in 4-6 concise bullet points. Today is {today}."
            ),
        },
        {
            "id": "costarica",
            "icon": "&#x1F1E8;&#x1F1F7;",
            "title": "Costa Rica &mdash; Travel Advisories &amp; Local News",
            "priority": "medium",
            "tag": "WATCH",
            "prompt": (
                f"Search for recent news (last 2 weeks) relevant to tourists in Costa Rica. "
                f"Cover: travel advisories or safety updates, volcanic activity (Arenal, Po\u00e1s, "
                f"Turrialba, Rinc\u00f3n de la Vieja), road closures or landslides, weather events, "
                f"entry or visa changes, crime alerts in tourist zones (Manuel Antonio, La Fortuna, "
                f"Tamarindo, San Jos\u00e9), and anything affecting travel within the country. "
                f"Summarize in 4-6 concise bullet points. Today is {today}."
            ),
        },
        {
            "id": "expat",
            "icon": "&#x1F30E;",
            "title": "Expat &amp; Long-Stay News &mdash; Both Countries",
            "priority": "low",
            "tag": "INFO",
            "prompt": (
                f"Search for recent news (last month) relevant to expats and long-stay visitors in "
                f"Panama and Costa Rica. Cover: changes to residency or visa rules, pensionado program "
                f"updates, healthcare access for foreigners, cost of living changes, banking or currency "
                f"issues for foreigners, notable expat community developments, and new laws affecting "
                f"foreign residents. Summarize in 4-6 concise bullet points. Today is {today}."
            ),
        },
    ]

    results = {}
    fuel_alert = None

    for i, section in enumerate(sections):
        print(f"Fetching: {section['title']}...")
        max_retries = 4
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}],
                    messages=[{"role": "user", "content": section["prompt"]}],
                )
                text = "\n".join(
                    block.text
                    for block in response.content
                    if hasattr(block, "text")
                ).strip()
                bullets = parse_bullets(text)
                results[section["id"]] = bullets
                if section["id"] == "fuel":
                    lower = text.lower()
                    if any(
                        w in lower
                        for w in ["shortage", "disruption", "cancell", "strike", "closure", "suspend"]
                    ):
                        fuel_alert = (
                            "Potential flight disruption indicators detected for Panama "
                            "&mdash; see Fuel &amp; Flight section below."
                        )
                break  # success
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed for {section['title']}: {e}")
                if attempt < max_retries - 1:
                    wait = 90 * (attempt + 1)
                    print(f"Rate limited â waiting {wait}s before retry...")
                    time.sleep(wait)
                else:
                    results[section["id"]] = [f"Error fetching data: {e}"]
        if i < len(sections) - 1:
            time.sleep(120)  # gap between sections to stay within rate limits

    html = generate_html(sections, results, fuel_alert, today)
    with open("pa_cr.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Generated pa_cr.html successfully.")


def parse_bullets(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    bullets = []
    for line in lines:
        # Skip markdown headers (###, ##, #)
        if re.match(r'^#{1,6}\s', line):
            continue
        clean = re.sub(r"^[-\u2022*\u2713\u2192\u2717\d+\.]+\s*\*?\*?", "", line).strip()
        clean = re.sub(r"\*\*", "", clean).strip()
        clean = re.sub(r"^\*+\s*", "", clean).strip()
        clean = re.sub(r"^#+\s*", "", clean).strip()
        if len(clean) > 15:
            bullets.append(clean)
    if bullets:
        return bullets[:7]
    return [l for l in lines if len(l) > 20][:5]


def section_html(section, bullets):
    bullets_html = "\n".join(f"<li>{b}</li>" for b in bullets)
    return f"""
    <div class="section visible" id="sec-{section['id']}">
      <div class="section-header">
        <span class="section-icon">{section['icon']}</span>
        <span class="section-title">{section['title']}</span>
        <span class="priority-tag {section['priority']}">{section['tag']}</span>
      </div>
      <div class="section-body"><ul>{bullets_html}</ul></div>
    </div>"""


def generate_html(sections, results, fuel_alert, today):
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%a, %b %-d, %Y at %H:%M UTC")
    sections_html = "\n".join(
        section_html(s, results.get(s["id"], ["No data available."]))
        for s in sections
    )
    fuel_html = ""
    if fuel_alert:
        fuel_html = f"""<div class="alert-banner visible">
  <span>&#x26A0;&#xFE0F;</span><span>{fuel_alert}</span>
</div>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Panama &amp; Costa Rica &mdash; Travel Intelligence</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
    :root{{--jungle:#1a3a2a;--palm:#2d6a4f;--leaf:#52b788;--mist:#b7e4c7;--sand:#f4e9d0;--amber:#e9a820;--red:#c0392b;--ink:#0d1f17}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--ink);font-family:'IBM Plex Sans',sans-serif;color:var(--sand);min-height:100vh}}
    .bg-texture{{position:fixed;inset:0;z-index:0;background:radial-gradient(ellipse at 20% 20%,rgba(45,106,79,.25) 0%,transparent 60%),radial-gradient(ellipse at 80% 80%,rgba(82,183,136,.12) 0%,transparent 50%)}}
    .container{{position:relative;z-index:1;max-width:900px;margin:0 auto;padding:2rem 1.5rem 4rem}}
    header{{border-bottom:1px solid rgba(82,183,136,.3);padding-bottom:1.5rem;margin-bottom:2rem}}
    .eyebrow{{font-family:'IBM Plex Mono',monospace;font-size:.65rem;letter-spacing:.25em;text-transform:uppercase;color:var(--leaf);margin-bottom:.5rem}}
    h1{{font-family:'Playfair Display',serif;font-size:clamp(2rem,5vw,3.2rem);font-weight:900;line-height:1.05;color:var(--sand);margin-bottom:.4rem}}
    h1 span{{color:var(--leaf)}}
    .subtitle{{font-size:.85rem;color:rgba(183,228,199,.6);font-weight:300}}
    .timestamp{{font-family:'IBM Plex Mono',monospace;font-size:.65rem;color:rgba(183,228,199,.5);margin-top:.8rem;letter-spacing:.05em}}
    .run-link{{font-family:'IBM Plex Mono',monospace;font-size:.65rem;margin-top:.3rem}}
    .run-link a{{color:var(--leaf)}}
    .alert-banner{{display:none;background:rgba(192,57,43,.15);border:1px solid var(--red);border-left:4px solid var(--red);padding:.8rem 1rem;border-radius:2px;margin-bottom:1.5rem;font-size:.85rem;color:#e88;align-items:center;gap:.6rem}}
    .alert-banner.visible{{display:flex}}
    .sections{{display:flex;flex-direction:column;gap:1.5rem}}
    .section{{background:rgba(255,255,255,.03);border:1px solid rgba(82,183,136,.15);border-radius:3px;overflow:hidden;opacity:0;transform:translateY(10px);transition:opacity .4s ease,transform .4s ease}}
    .section.visible{{opacity:1;transform:translateY(0)}}
    .section-header{{display:flex;align-items:center;gap:.7rem;padding:.9rem 1.2rem;background:rgba(255,255,255,.04);border-bottom:1px solid rgba(82,183,136,.12)}}
    .section-icon{{font-size:1.1rem}}
    .section-title{{font-family:'IBM Plex Mono',monospace;font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;color:var(--leaf)}}
    .priority-tag{{margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:.6rem;padding:.15rem .5rem;border-radius:20px;text-transform:uppercase;letter-spacing:.1em;white-space:nowrap}}
    .priority-tag.high{{background:rgba(192,57,43,.25);color:#e88;border:1px solid rgba(192,57,43,.5)}}
    .priority-tag.medium{{background:rgba(233,168,32,.2);color:var(--amber);border:1px solid rgba(233,168,32,.4)}}
    .priority-tag.low{{background:rgba(82,183,136,.15);color:var(--leaf);border:1px solid rgba(82,183,136,.3)}}
    .section-body{{padding:1.2rem;font-size:.88rem;line-height:1.75;color:rgba(244,233,208,.85)}}
    .section-body ul{{list-style:none;display:flex;flex-direction:column;gap:.75rem}}
    .section-body li{{padding-left:1.2rem;position:relative}}
    .section-body li::before{{content:'\u2192';position:absolute;left:0;color:var(--leaf);font-size:.75rem;top:.1em}}
    footer{{margin-top:3rem;padding-top:1rem;border-top:1px solid rgba(82,183,136,.12);font-family:'IBM Plex Mono',monospace;font-size:.62rem;color:rgba(183,228,199,.2);letter-spacing:.05em;text-align:center}}
  </style>
</head>
<body>
  <div class="bg-texture"></div>
  <div class="container">
    <header>
      <div class="eyebrow">Travel Intelligence Dashboard</div>
      <h1>Panama <span>&amp;</span> Costa Rica</h1>
      <div class="subtitle">Daily news scan &middot; Fuel alerts &middot; Tourist &amp; expat intelligence</div>
      <div class="timestamp">Last updated: {timestamp}</div>
      <div class="run-link"><a href="https://github.com/chrisgoward/news/actions/workflows/daily-scan.yml" target="_blank">&#x21BB; Trigger manual refresh &#x2197;</a></div>
    </header>
    {fuel_html}
    <div class="sections">{sections_html}</div>
    <footer>Powered by Claude &middot; Live web search &middot; Auto-refreshes daily at 7 AM Central</footer>
  </div>
  <script>
    document.querySelectorAll('.section').forEach((el,i)=>{{
      setTimeout(()=>el.classList.add('visible'), i*120);
    }});
  </script>
</body>
</html>"""


if __name__ == "__main__":
    main()
