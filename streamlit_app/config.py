"""
One place to drop in the Tableau Public embed URL once the dashboard is
published (Stage 5 — Tableau is a manual step, not scripted).

How to get this URL:
  1. Publish the workbook to Tableau Public (File > Save to Tableau Public,
     free account required — no paid tier).
  2. Open the published view in a browser, click Share, copy the
     "Embed Code" link (looks like
     https://public.tableau.com/views/<workbook>/<view>?:embed=y&:showVizHome=no)
  3. Paste it below.

Leave as None and the Streamlit page shows a graceful placeholder + a
plain link instead of a broken embed.
"""

TABLEAU_PUBLIC_EMBED_URL: str | None = None
