"""The pages Sentinel watches, each with its OWN relevance question for Jev.
The one file you edit to add a page (until targets move to the database).
Keep it small while on Firecrawl's free tier (1 credit per page per day)."""

TARGETS = [
    {
        "title": "Revenue — Customs Prohibitions & Restrictions",
        "url": "https://www.revenue.ie/en/tax-professionals/tdm/customs/prohibitions-restrictions/index.aspx",
        "question": "Is this change about customs rules affecting chemical products?",
    },
    {
        "title": "Irish Government News",
        "url": "https://www.gov.ie/en/news/",
        "question": "Is this change about new or amended regulations affecting importers or exporters?",
    },
]