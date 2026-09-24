import streamlit as st


def apply_styles():
    """Apply the shared visual system used by every page."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

        :root {
            --ink: #202a35;
            --navy: #17232d;
            --navy-soft: #243746;
            --gold: #b48a4a;
            --gold-soft: #d6b574;
            --ivory: #f6f3ee;
            --surface: #ffffff;
            --muted: #69747d;
            --line: #ded7cc;
        }

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 88% 4%, rgba(180, 138, 74, 0.10), transparent 20rem),
                var(--ivory);
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 1440px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            font-family: 'Playfair Display', serif;
            color: var(--navy) !important;
            letter-spacing: -0.02em;
        }

        h1 {
            font-size: clamp(2rem, 4vw, 3.15rem) !important;
        }

        p, label, [data-testid="stCaptionContainer"] {
            color: var(--ink);
        }

        hr {
            border-color: var(--line);
            margin: 1.3rem 0 1.8rem;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.02), transparent 28%),
                var(--navy);
            border-right: 1px solid #334856;
        }

        [data-testid="stSidebar"] * {
            color: #f7f2e8 !important;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 0.7rem;
            margin: 0.1rem 0.65rem;
        }

        [data-testid="stSidebarNav"] a:hover {
            background: rgba(214, 181, 116, 0.12);
        }

        /* Forms and widgets */
        [data-testid="stForm"] {
            background: rgba(255,255,255,0.92);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1.35rem;
            box-shadow: 0 12px 30px rgba(32,42,53,0.06);
        }

        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {
            background: #fff !important;
            border-color: #d4ccc0 !important;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            color: var(--ink) !important;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            background: var(--navy);
            color: #fff;
            border: 1px solid var(--navy);
            border-radius: 0.7rem;
            font-weight: 700;
            min-height: 2.65rem;
            transition: transform 150ms ease, box-shadow 150ms ease, background 150ms ease;
        }
        .stButton > button *,
       .stFormSubmitButton > button * {
            color: #FFFFFF !important;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            background: var(--navy-soft);
            color: #fff;
            border-color: var(--gold);
            box-shadow: 0 8px 18px rgba(32,42,53,0.14);
            transform: translateY(-1px);
        }

        /* Native KPI cards */
        [data-testid="stMetric"] {
            min-height: 8.7rem;
            background: rgba(255,255,255,0.94);
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1.05rem 1.15rem;
            box-shadow: 0 10px 28px rgba(32,42,53,0.055);
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--navy);
            font-family: 'Playfair Display', serif;
            font-size: clamp(1.7rem, 2.35vw, 2rem) !important;
        }

        /* Home dashboard */
        .hero {
            position: relative;
            overflow: hidden;
            background: linear-gradient(120deg, #17232d 0%, #263b49 68%, #3d4e57 100%);
            border-radius: 1.25rem;
            padding: clamp(1.65rem, 4vw, 2.6rem);
            margin-bottom: 1.45rem;
            box-shadow: 0 18px 44px rgba(23,35,45,0.18);
        }

        .hero::after {
            content: '';
            position: absolute;
            right: -5rem;
            top: -8rem;
            width: 22rem;
            height: 22rem;
            border: 1px solid rgba(214,181,116,0.35);
            border-radius: 50%;
            box-shadow: 0 0 0 3.5rem rgba(214,181,116,0.055), 0 0 0 7rem rgba(214,181,116,0.035);
        }

        .hero-kicker {
            color: var(--gold-soft);
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .hero-title {
            position: relative;
            z-index: 1;
            color: #fff !important;
            font-family: 'Playfair Display', serif;
            font-size: clamp(2rem, 4vw, 3.3rem);
            line-height: 1.04;
            margin: 0;
        }

        .hero-copy {
            position: relative;
            z-index: 1;
            color: #dce2e5;
            max-width: 44rem;
            margin: 0.7rem 0 0;
            font-size: 1rem;
        }

        .section-heading {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--navy);
            font-family: 'Playfair Display', serif;
            font-size: 1.35rem;
            font-weight: 700;
            margin: 1.3rem 0 0.7rem;
        }

        .section-heading::after {
            content: '';
            height: 1px;
            flex: 1;
            background: var(--line);
        }

        .panel-note {
            color: var(--muted);
            font-size: 0.86rem;
            margin-top: -0.35rem;
            margin-bottom: 0.85rem;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--line);
            border-radius: 0.9rem;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(32,42,53,0.045);
        }

        /* Existing review page cards */
        .review-card {
            background: #fff;
            border: 1px solid var(--line);
            border-radius: 1rem;
            padding: 1.2rem 1.35rem;
            margin-bottom: 0.9rem;
            box-shadow: 0 8px 22px rgba(32,42,53,0.05);
        }

        .review-stars { color: var(--gold); font-size: 1.25rem; }
        .review-guest { color: var(--navy); font-weight: 700; }
        .review-hotel { color: var(--muted); font-size: 0.88rem; }

        @media (max-width: 700px) {
            [data-testid="stMainBlockContainer"] { padding-top: 1rem; }
            .hero { border-radius: 1rem; }
            [data-testid="stMetric"] { min-height: 7.5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
