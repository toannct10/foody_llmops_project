"""A small, centralized visual layer for the Streamlit demo."""

import streamlit as st

CSS = """
<style>
:root {color-scheme: dark;}
.stApp {background: #0E1117; color: #F1F5F9;}
[data-testid="stSidebar"] {background: #151B24; border-right: 1px solid #2A3442;}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {color: #CBD5E1 !important;}
[data-testid="stWidgetLabel"] p {color: #B8C5D6 !important;}
[data-testid="stSidebar"] .stRadio > label {display: none;}
[data-testid="stSidebar"] [role="radiogroup"] {gap: .36rem;}
[data-testid="stSidebar"] [role="radio"] {padding: .48rem .7rem; border-radius: .65rem;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {background: #253857;}
.block-container {max-width: 1320px; padding-top: 1.45rem; padding-bottom: 3rem;}
h1,h2,h3 {letter-spacing: -.025em; color: #F1F5F9;}
h1 {font-size: 2.15rem !important; font-weight: 750 !important;}
h2 {font-size: 1.35rem !important; margin-top: 1.3rem !important;}
h3 {font-size: 1.08rem !important;}
[data-testid="stVerticalBlockBorderWrapper"] {background: #161B22; border-color: #2A3442 !important; border-radius: .85rem;}
[data-testid="stMetric"] {background: #1A202C; border: 1px solid #2A3442; border-radius: .9rem; padding: .85rem 1rem; min-height: 108px;}
[data-testid="stMetricLabel"] {color: #9AA4B2;}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {color: #F1F5F9 !important; font-size: 1.55rem !important; font-weight: 720; letter-spacing: -.03em;}
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * {font-size: .76rem !important;}
[data-testid="stDataFrame"] {border: 1px solid #2A3442; border-radius: .7rem; overflow: hidden;}
.foody-hero {padding: 1.3rem 1.5rem; background: #182231; border: 1px solid #32425A; border-radius: 1rem; margin-bottom: 1.1rem;}
.foody-eyebrow {font-size: .72rem; text-transform: uppercase; letter-spacing: .12em; color: #82ABF2; font-weight: 700; margin-bottom: .3rem;}
.foody-hero h1 {margin: 0 0 .25rem 0;}
.foody-muted {color: #9AA4B2; font-size: .9rem; margin: .2rem 0;}
.foody-badge {display: inline-block; padding: .25rem .57rem; margin: .25rem .3rem .05rem 0; border: 1px solid #3B5274; background: #22314A; color: #BDD7FF; border-radius: 999px; font-size: .76rem; font-weight: 600;}
.foody-badge.good {background: #15352B; border-color: #286A50; color: #93E5B8;}
.foody-badge.warn {background: #382D1D; border-color: #77602B; color: #F5D38A;}
.foody-badge.muted {background: #252C36; border-color: #3E4855; color: #B2BDCA;}
.foody-card {background: #1A202C; border: 1px solid #303B4B; border-radius: .9rem; padding: 1.1rem 1.25rem; margin: .4rem 0 .85rem;}
.foody-card h3 {margin: 0 0 .45rem;}
.foody-card p {margin: .25rem 0; line-height: 1.55;}
.foody-empty {background: #1A202C; border: 1px dashed #435064; border-radius: .85rem; padding: 1rem 1.2rem; color: #CBD5E1;}
.foody-empty strong {display: block; color: #F1F5F9; margin-bottom: .2rem;}
.foody-answer {background: #1D2937; border-left: 3px solid #79A8F8;}
.foody-query-card {background: #161F2B; border: 1px solid #34445B; border-radius: .9rem; padding: 1rem 1.2rem; margin: .65rem 0 1rem;}
[data-testid="stCodeBlock"] {overflow-x: auto; border: 1px solid #34445B; border-radius: .65rem;}
[data-testid="stAlert"] {border-radius: .7rem;}
.foody-section-note {font-size: .84rem; color: #9AA4B2; margin-top: -.35rem; margin-bottom: .6rem;}
div.stButton > button {border-radius: .55rem; border-color: #3A4E69;}
div.stButton > button[kind="primary"] {background: #4F8EF7; border-color: #4F8EF7; color: #0E1117;}
[data-testid="stTextInput"] input {background: #1A202C; color: #F1F5F9; border-color: #39465B; border-radius: .65rem; min-height: 2.65rem;}
[data-testid="stTextInput"] input::placeholder {color: #97A7BA; opacity: 1;}
[data-testid="stTextInput"] input:focus {border-color: #8B8CF8; box-shadow: 0 0 0 1px #8B8CF8;}
[data-baseweb="select"] > div {background: #1A202C !important; border-color: #39465B !important;}
[data-baseweb="select"] * {color: #F1F5F9 !important;}
[data-testid="stDateInput"] input {background: #1A202C !important; color: #F1F5F9 !important; border-color: #39465B !important;}
.foody-sidebar-card {border: 1px solid #344154; background: #1B2532; border-radius: .65rem; padding: .68rem .78rem; margin: .45rem 0; color: #DCE7F5; font-size: .82rem; line-height: 1.5;}
.foody-sidebar-card strong {color: #F1F5F9;}
.foody-sidebar-muted {color: #9EB0C5; font-size: .73rem;}
.foody-kpi-label {font-size: .75rem; color: #AFC0D3; text-transform: uppercase; letter-spacing: .045em;}
.foody-kpi-value {font-size: 1.06rem; color: #F1F5F9; font-weight: 700; overflow-wrap: anywhere;}
/* Enterprise analytics tokens and component rules. */
:root {
  --foody-bg:#0B0F17; --foody-surface:#131A24; --foody-raised:#17202D;
  --foody-border:rgba(148,163,184,.16); --foody-border-strong:rgba(148,163,184,.24);
  --foody-text:#F8FAFC; --foody-secondary:#94A3B8; --foody-muted:#64748B;
  --foody-primary:#6366F1; --foody-blue:#3B82F6; --foody-cyan:#22D3EE;
  --foody-success:#6BCB9A; --foody-warning:#F5B85A; --foody-danger:#FF6B7A;
}
.stApp {background:var(--foody-bg);color:var(--foody-text);}
.block-container {max-width:1320px;padding-top:1.25rem;padding-bottom:2.75rem;}
h1,h2,h3 {color:var(--foody-text);letter-spacing:-.025em;}
h1 {font-size:2rem !important;font-weight:720 !important;}
h2 {font-size:1.35rem !important;margin-top:1.15rem !important;}
h3 {font-size:1.06rem !important;}
[data-testid="stSidebar"] {background:#0F141D;border-right:1px solid var(--foody-border);}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.3rem;}
[data-testid="stSidebar"] [role="radio"] {padding:.55rem .75rem;border-radius:.65rem;transition:background 180ms ease;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {background:rgba(99,102,241,.19);box-shadow:inset 3px 0 0 #818CF8;}
[data-testid="stSidebar"] [role="radio"]:focus-within {outline:2px solid #A5B4FC;outline-offset:2px;}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] > div > div > div {
  background:#F8FAFC !important;border-color:#818CF8 !important;}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] > div > div {
  background:#6366F1 !important;border-color:#818CF8 !important;}
[data-testid="stTab"][aria-selected="true"] {color:#C7D2FE !important;}
[data-testid="stTab"][aria-selected="true"] .react-aria-SelectionIndicator {
  background:#818CF8 !important;}
[data-testid="stVerticalBlockBorderWrapper"],.foody-card,.foody-query-card,.foody-sidebar-card {
  background:var(--foody-surface);border:1px solid var(--foody-border) !important;
  border-radius:1rem;box-shadow:0 8px 24px rgba(0,0,0,.12);
}
[data-testid="stVerticalBlockBorderWrapper"],.foody-card {
  transition:border-color 180ms ease,transform 180ms ease,box-shadow 180ms ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover,.foody-card:hover {
  border-color:rgba(129,140,248,.3) !important;transform:translateY(-1px);
  box-shadow:0 10px 28px rgba(0,0,0,.22);
}
[data-testid="stMetric"] {background:var(--foody-raised);border:1px solid var(--foody-border);
  border-radius:.9rem;padding:.8rem 1rem;min-height:102px;box-shadow:inset 0 2px 0 rgba(129,140,248,.28);
  transition:border-color 180ms ease,transform 180ms ease,box-shadow 180ms ease;}
[data-testid="stMetric"]:hover {border-color:rgba(129,140,248,.3);transform:translateY(-1px);
  box-shadow:0 10px 28px rgba(0,0,0,.2);}
[data-testid="stMetricLabel"] p {color:var(--foody-secondary) !important;font-size:.74rem !important;
  letter-spacing:.055em;text-transform:uppercase;}
[data-testid="stMetricValue"],[data-testid="stMetricValue"] * {color:var(--foody-text) !important;
  font-size:clamp(1.12rem,1.8vw,1.5rem) !important;font-weight:690 !important;overflow-wrap:anywhere;}
.foody-hero {background:linear-gradient(115deg,#17202D,#131A24 72%);
  border:1px solid var(--foody-border);border-left:3px solid #818CF8;border-radius:1rem;
  padding:1.1rem 1.35rem;margin-bottom:1rem;box-shadow:0 8px 25px rgba(0,0,0,.15);}
.foody-eyebrow {color:#A5B4FC;font-size:.7rem;letter-spacing:.11em;}
.foody-muted,.foody-section-note {color:var(--foody-secondary);}
.foody-badge {background:rgba(99,102,241,.13);border:1px solid rgba(129,140,248,.32);
  color:#C7D2FE;border-radius:999px;font-weight:600;}
.foody-badge.info {background:rgba(59,130,246,.13);border-color:rgba(96,165,250,.3);color:#BFDBFE;}
.foody-badge.cyan {background:rgba(34,211,238,.1);border-color:rgba(34,211,238,.28);color:#A5F3FC;}
.foody-badge.good {background:rgba(107,203,154,.12);border-color:rgba(107,203,154,.34);color:#A7E5C4;}
.foody-badge.warn {background:rgba(245,184,90,.12);border-color:rgba(245,184,90,.34);color:#F7D59B;}
.foody-badge.danger {background:rgba(255,107,122,.12);border-color:rgba(255,107,122,.34);color:#FFABB5;}
.foody-badge.muted {background:rgba(100,116,139,.16);border-color:var(--foody-border);color:#CBD5E1;}
.foody-answer {background:var(--foody-surface);border-left:3px solid #818CF8 !important;}
.foody-answer p {font-size:1.04rem;line-height:1.6;color:var(--foody-text);}
.foody-sidebar-card {padding:.75rem .8rem;color:#CBD5E1;font-size:.78rem;line-height:1.7;}
.foody-sidebar-muted {color:var(--foody-secondary);font-size:.72rem;}
[data-testid="stCodeBlock"] {background:#0F141D;border:1px solid var(--foody-border-strong);
  border-radius:.75rem;overflow-x:auto;}
[data-testid="stDataFrame"] {border:1px solid var(--foody-border);border-radius:.75rem;overflow:hidden;}
[data-testid="stVegaLiteChart"] {background:var(--foody-surface);border:1px solid var(--foody-border);
  border-radius:.85rem;padding:.6rem;}
div.stButton > button {border-color:var(--foody-border-strong);transition:background 180ms ease,
  border-color 180ms ease,transform 180ms ease;}
div.stButton > button:hover {border-color:#818CF8;transform:translateY(-1px);}
div.stButton > button[kind="primary"] {background:#4F46E5;border-color:#6366F1;color:#fff;}
div.stButton > button[kind="primary"]:hover {background:#6366F1;}
button:focus-visible,input:focus-visible,textarea:focus-visible,[role="tab"]:focus-visible {
  outline:2px solid #A5B4FC !important;outline-offset:2px;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:#101722;
  color:var(--foody-text);border-color:var(--foody-border-strong);}
.foody-progress {background:linear-gradient(180deg,rgba(30,41,59,.72),rgba(15,23,42,.82));
  border:1px solid var(--foody-border);border-radius:1rem;padding:1rem 1.15rem;margin:.7rem 0;}
.foody-progress-header {display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:.75rem;}
.foody-progress-title {color:var(--foody-text);font-size:.91rem;font-weight:620;}
.foody-progress-percent {color:#A5B4FC;font-weight:720;font-variant-numeric:tabular-nums;}
.foody-progress-track {height:10px;position:relative;overflow:hidden;border-radius:999px;
  background:rgba(51,65,85,.55);box-shadow:inset 0 0 0 1px rgba(148,163,184,.08);}
.foody-progress-fill {position:relative;height:100%;border-radius:inherit;
  background:linear-gradient(90deg,#7C3AED,#6366F1 40%,#3B82F6 78%,#22D3EE);
  transition:width 450ms cubic-bezier(.4,0,.2,1);box-shadow:0 0 12px rgba(99,102,241,.28);}
.foody-progress-shimmer {position:absolute;inset:0;background:linear-gradient(110deg,
  transparent 20%,rgba(255,255,255,.12) 40%,rgba(255,255,255,.25) 50%,
  rgba(255,255,255,.12) 60%,transparent 80%);transform:translateX(-100%);
  animation:foody-shimmer 1.8s linear infinite;}
.foody-progress-head {position:absolute;right:-3px;top:50%;width:10px;height:10px;
  transform:translateY(-50%);border-radius:50%;background:#A5F3FC;
  box-shadow:0 0 8px rgba(34,211,238,.8),0 0 18px rgba(59,130,246,.5);
  animation:foody-pulse 1.3s ease-in-out infinite;}
.foody-progress-footer {margin-top:.6rem;color:var(--foody-secondary);font-size:.82rem;}
.foody-progress.complete .foody-progress-fill {background:linear-gradient(90deg,#6366F1,#3B82F6);}
.foody-progress.complete .foody-progress-shimmer,.foody-progress.complete .foody-progress-head,
.foody-progress.failed .foody-progress-shimmer,.foody-progress.failed .foody-progress-head {display:none;}
.foody-progress.failed .foody-progress-fill {background:var(--foody-danger);}
@keyframes foody-shimmer {from{transform:translateX(-100%)}to{transform:translateX(100%)}}
@keyframes foody-pulse {0%,100%{transform:translateY(-50%) scale(.92);opacity:.75}
  50%{transform:translateY(-50%) scale(1.15);opacity:1}}
@media(max-width:800px) {.block-container{padding-inline:1rem}
  .foody-hero{padding:1rem}.foody-card{padding:1rem}[data-testid="stMetric"]{min-height:88px}}
@media(prefers-reduced-motion:reduce) {.foody-progress-fill,.foody-progress-shimmer,
  .foody-progress-head,[data-testid="stMetric"],.foody-card,div.stButton > button {
  transition:none !important;animation:none !important;transform:none !important;}}
/* Final information hierarchy: one font family, distinct scale and tabular values. */
.stApp,[data-testid="stSidebar"],button,input,textarea {
  font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
h1 {font-size:clamp(1.75rem,2.4vw,2rem) !important;font-weight:700 !important;}
h2 {font-size:1.35rem !important;font-weight:680 !important;}
h3 {font-size:1.08rem !important;font-weight:660 !important;}
[data-testid="stSidebar"] h3 {font-weight:740 !important;letter-spacing:.045em;}
[data-testid="stSidebar"] [role="radio"]:has(input:checked) {
  background:rgba(99,102,241,.2);box-shadow:inset 3px 0 0 #818CF8;}
.foody-kpi-card {min-width:0;min-height:112px;padding:18px 20px;margin:4px 0 14px;
  background:var(--foody-raised);border:1px solid var(--foody-border);
  border-radius:14px;box-shadow:0 5px 18px rgba(0,0,0,.12);overflow-wrap:anywhere;}
.foody-kpi-primary {min-height:142px;background:linear-gradient(115deg,#1B2540,#17202D);
  border-top:3px solid #818CF8;}
.foody-kpi-tall {min-height:142px;}
.foody-kpi-status {border-top:2px solid #64748B;}
.foody-kpi-healthy {border-top:3px solid var(--foody-success);}
.foody-kpi-warning {border-top:3px solid var(--foody-warning);}
.foody-kpi-danger {border-top:3px solid var(--foody-danger);}
.foody-kpi-label {color:#AFC0D3;font-size:.76rem;font-weight:630;
  letter-spacing:.045em;text-transform:uppercase;line-height:1.3;}
.foody-kpi-value {color:#F8FAFC;font-size:clamp(1.35rem,2vw,1.55rem);
  font-weight:690;letter-spacing:-.02em;font-variant-numeric:tabular-nums;
  line-height:1.18;margin-top:12px;overflow-wrap:anywhere;}
.foody-kpi-primary .foody-kpi-value {color:#E0E7FF;
  font-size:clamp(1.85rem,3vw,2.25rem);font-weight:740;letter-spacing:-.025em;}
.foody-kpi-healthy .foody-kpi-value {color:#A7E5C4;}
.foody-kpi-warning .foody-kpi-value {color:#F7D59B;}
.foody-kpi-danger .foody-kpi-value {color:#FFABB5;}
.foody-kpi-detail {color:var(--foody-secondary);font-size:.8rem;line-height:1.4;margin-top:10px;}
.foody-answer h3 {font-size:1rem !important;text-transform:uppercase;
  letter-spacing:.045em;color:#A5B4FC;}
.foody-answer p {font-size:1.05rem;line-height:1.65;}
.foody-progress-title {font-weight:650;}
.foody-progress-footer {font-size:.78rem;}
[data-testid="stVegaLiteChart"] {padding:12px;}
[data-testid="stCodeBlock"],code,pre {font-family:ui-monospace,SFMono-Regular,Consolas,monospace;}
@media(max-width:800px) {.foody-kpi-card{min-height:96px;padding:16px 18px}
  .foody-kpi-primary{min-height:116px}}
</style>
"""


def apply_styles():
    st.markdown(CSS, unsafe_allow_html=True)
