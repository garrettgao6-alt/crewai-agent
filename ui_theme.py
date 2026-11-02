"""One responsive visual system for the existing Streamlit application."""
CSS = r'''
<style>
:root{--gao-bg:#0b111b;--gao-surface:#111b29;--gao-soft:#172334;--gao-line:#29374a;--gao-text:#eef4fc;--gao-muted:#a9b9cd;--gao-accent:#70e0c6;--gao-blue:#6ca9ff}
html,body,.stApp{background:var(--gao-bg);color:var(--gao-text);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*,*::before,*::after{box-sizing:border-box}
[data-testid="stMainBlockContainer"],.main .block-container{max-width:1360px;padding:4rem 2.2rem 4rem}
[data-testid="stHeader"]{background:rgba(11,17,27,.92)}
[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none}
[data-testid="stSidebar"]{background:#0e1723;border-right:1px solid var(--gao-line)}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:1.5rem 1.1rem}
h1,h2,h3,h4{color:var(--gao-text);letter-spacing:-.035em;font-weight:600!important;line-height:1.18!important}
h1{font-size:clamp(1.8rem,3.5vw,2.8rem)!important}h2{font-size:1.3rem!important}h3{font-size:1.1rem!important}
p,li{line-height:1.65} [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p{color:var(--gao-muted)!important;font-size:.82rem!important;line-height:1.5}
[data-testid="stWidgetLabel"] p{font-size:.86rem;font-weight:500;color:#c6d4e5}
[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button,[data-testid="stDownloadButton"] button{min-height:44px;border:1px solid #34465d;border-radius:10px;background:#172436;color:var(--gao-text);padding:.6rem 1rem;transition:background .16s,border-color .16s,transform .16s;white-space:normal;word-break:normal}
[data-testid="stButton"] button p,[data-testid="stFormSubmitButton"] button p{color:inherit;font-size:.88rem;font-weight:550;line-height:1.25}
[data-testid="stButton"] button:hover,[data-testid="stDownloadButton"] button:hover{background:#21344b;border-color:var(--gao-accent);transform:translateY(-1px)}
button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{outline:3px solid var(--gao-accent)!important;outline-offset:3px}
button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:var(--gao-accent);border-color:var(--gao-accent);color:#072c25}
button[kind="primary"]:hover{background:#9aeedb;color:#072c25}
button:disabled{opacity:.48;transform:none!important;cursor:not-allowed}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:#101b2a!important;border-color:#34465d!important;border-radius:10px!important;color:var(--gao-text)!important}
input,textarea{color:var(--gao-text)!important}input::placeholder,textarea::placeholder{color:#91a4bc!important;opacity:1}
[data-baseweb="popover"] [role="listbox"]{background:#172436;color:var(--gao-text)}
[data-testid="stForm"],[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:var(--gao-line)!important;border-radius:14px}
[data-testid="stFileUploaderDropzone"]{background:#111e2e;border:1px dashed #49617e;border-radius:14px;padding:1.4rem}
[data-testid="stAlert"]{border-radius:12px;font-size:.9rem}
[data-testid="stTabs"] [role="tablist"]{gap:1.1rem;border-bottom:1px solid var(--gao-line);flex-wrap:wrap;height:auto}
[data-testid="stTabs"] [role="tab"]{height:46px;white-space:normal;color:var(--gao-muted)}
[data-testid="stTabs"] [aria-selected="true"]{color:var(--gao-accent)}
[data-testid="stMetric"]{background:var(--gao-surface);border:1px solid var(--gao-line);padding:1rem;border-radius:12px}
[data-testid="stMetricValue"]{font-size:1.8rem;font-weight:600}
.st-key-app_header{border-bottom:1px solid var(--gao-line);padding-bottom:1rem;margin-bottom:.25rem}
.st-key-app_header [data-testid="stHorizontalBlock"]{align-items:center;gap:.75rem}
.auth-action-shell{display:flex;justify-content:flex-end;align-items:center;min-height:44px}.auth-avatar{display:inline-flex;gap:.5rem;align-items:center;font-size:.86rem;color:#d0dcee;overflow-wrap:anywhere}.auth-avatar-mark{width:28px;height:28px;border-radius:50%;display:inline-grid;place-items:center;background:#28425b;color:#cef7ee}
.st-key-quick_navigation [data-testid="stHorizontalBlock"]{gap:.4rem;flex-wrap:wrap}
.st-key-quick_navigation [data-testid="stColumn"]{flex:1 1 84px!important;min-width:0!important}
.st-key-quick_navigation button{padding:.5rem .4rem!important;min-height:40px}
.st-key-quick_navigation button p{font-size:.8rem!important}
.construction-hero{position:relative;overflow:hidden;background:linear-gradient(115deg,#132437,#101b29 75%);border:1px solid #2d4559;border-radius:20px;padding:clamp(1.4rem,3vw,2.6rem);margin:.6rem 0 .25rem;animation:gao-enter .32s ease both}
.construction-hero::after{content:"";position:absolute;right:-55px;top:-100px;width:330px;height:330px;border:1px solid #70e0c61a;border-radius:50%;box-shadow:0 0 0 55px #70e0c608,0 0 0 110px #70e0c605;pointer-events:none}
.hero-kicker,.workspace-card-meta{color:var(--gao-accent);text-transform:uppercase;letter-spacing:.12em;font-size:.69rem;font-weight:600}
.construction-hero h1{font-size:clamp(1.9rem,3.5vw,3rem)!important;max-width:720px;margin:.8rem 0}
.hero-support{max-width:690px;color:#bacbdd;margin-bottom:0;font-size:.95rem}
.hero-subline{display:flex;flex-wrap:wrap;gap:.6rem;font-size:.85rem;color:#b9cadb}
.hero-data-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem;margin-top:1.5rem}.hero-data-cell{padding:.65rem .8rem;border:1px solid #304359;border-radius:10px;background:#0d172280}.hero-data-label{font-size:.66rem;color:#a9b9cd;text-transform:uppercase;letter-spacing:.08em}.hero-data-value{font-size:.88rem;margin-top:.25rem;color:#eff7ff}
.enterprise-page-header{margin:.8rem 0 1rem}.enterprise-title{margin:0 0 .4rem}.enterprise-subtitle{color:var(--gao-muted);margin:0;max-width:760px}
.workspace-section-title,.workspace-title{font-size:1.15rem;font-weight:600;color:#e7f2ff;margin:1.5rem 0 .7rem;letter-spacing:-.02em}
.workspace-card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem}
.workspace-command-card,.quick-action-card,.workspace-activity-card,.workspace-overview-card,.report-section,.usage-card,.pricing-card,.auth-box{background:var(--gao-surface);border:1px solid var(--gao-line);border-radius:14px;padding:1.2rem}
.workspace-command-card{height:100%;transition:border-color .18s,background .18s}.workspace-command-card:hover{border-color:#4f817f;background:#142332}
.workspace-card-label,.quick-action-title{font-size:1rem;font-weight:600;margin-bottom:.5rem}.workspace-card-body,.quick-action-description{font-size:.85rem;color:var(--gao-muted);line-height:1.55;margin-bottom:.8rem}
.dashboard-metric-card{border-left:2px solid #3b756f;background:var(--gao-surface);border-radius:0 12px 12px 0;padding:1rem;min-height:126px}.dashboard-metric-label{color:#b9c8da;font-size:.76rem}.dashboard-metric-value{font-size:1.55rem;font-weight:600;margin:.3rem 0}.dashboard-metric-note{color:var(--gao-muted);font-size:.74rem}
.workspace-overview-line,.workspace-activity-item{padding:.35rem 0;color:#bfcee0;font-size:.9rem}.guest-banner{background:#102f33;border:1px solid #295a59;border-radius:12px;padding:1rem;color:#c6eee8}
.chat-container{border:1px solid var(--gao-line);background:#0f1926;border-radius:16px;padding:1rem;max-height:65vh;overflow-y:auto;overflow-wrap:anywhere}
.chat-row{display:flex;margin:.75rem 0}.chat-user{justify-content:flex-end}.chat-assistant{justify-content:flex-start}.chat-bubble{max-width:94%;padding:.9rem 1rem;border-radius:14px;font-size:.92rem;line-height:1.7;white-space:pre-wrap}.user-msg{background:#234460;color:#f4fbff}.ai-msg{background:#172637;color:#e1ebf8}.chat-bubble pre{white-space:pre-wrap;overflow-wrap:anywhere}
.citation-row{display:flex;flex-wrap:wrap;gap:.4rem}.citation-pill{font-size:.74rem;background:#172d32;color:#a8e5d8;border:1px solid #2a5052;border-radius:7px;padding:.3rem .5rem;overflow-wrap:anywhere}
.quick-chip-row{display:flex;flex-wrap:wrap;gap:.4rem}.quick-chip{border:1px solid #34465d;border-radius:20px;padding:.3rem .7rem;font-size:.75rem;color:#b9cbdf}
.typing-indicator{display:flex;align-items:center;gap:.4rem;color:var(--gao-muted);font-size:.85rem}.typing-dot{width:6px;height:6px;border-radius:50%;background:var(--gao-accent);animation:gao-pulse 1s ease-in-out infinite}.typing-dot:nth-child(2){animation-delay:.15s}.typing-dot:nth-child(3){animation-delay:.3s}
.report-section{margin-bottom:1rem;overflow-wrap:anywhere;line-height:1.75}.report-section h3{color:var(--gao-accent)}
.gao-home-link{display:flex;align-items:center;gap:.7rem;min-height:44px;padding:.15rem 0;color:var(--gao-text)!important;font-size:1rem;font-weight:700;text-decoration:none!important;white-space:nowrap;border-radius:9px}
.gao-home-link:focus-visible{outline:2px solid var(--gao-accent);outline-offset:4px}
.gao-home-mark{display:inline-grid;place-items:center;background:var(--gao-accent);color:#082c26;width:32px;height:32px;flex-shrink:0;border-radius:9px;font-size:1.15rem;font-weight:700}
.private-download{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;min-height:44px;padding:.6rem 1rem;border:1px solid #42665f;border-radius:10px;color:#b8f3e4!important;background:#142e30;text-decoration:none!important;font-size:.88rem;transition:background .15s}.private-download:hover{background:#21463f}.private-download::before{content:"↓"}
[data-testid="stChatInput"]{border:1px solid #3b526a;border-radius:14px;background:#152233}
[data-testid="stMarkdownContainer"] a{color:#8cbeff} [data-testid="stMarkdownContainer"] code{overflow-wrap:anywhere}
[class*="st-key-dm_upload_"] [data-testid="stFileUploaderDropzoneInstructions"] small,[class*="st-key-bim_upload_"] [data-testid="stFileUploaderDropzoneInstructions"] small{display:none}
.st-key-bim_metrics [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:.6rem}.st-key-bim_metrics [data-testid="stColumn"]{min-width:0!important;flex:1 1 0!important}
@media(max-width:640px){.st-key-dashboard_metrics [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.6rem}.st-key-dashboard_metrics [data-testid="stColumn"]{min-width:0!important;flex:1 1 calc(50% - .6rem)!important}.st-key-bim_metrics [data-testid="stMetric"]{padding:.7rem}.st-key-bim_metrics [data-testid="stMetricValue"]{font-size:1.35rem}}
@keyframes gao-enter{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes gao-pulse{50%{opacity:.25}}
@media(min-width:769px){[data-testid="stSidebar"]{min-width:245px!important;max-width:245px!important;width:245px!important}}
@media(max-width:1050px){.workspace-card-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-data-row{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){[data-testid="stMainBlockContainer"],.main .block-container{padding:3.6rem 1rem 3rem}.st-key-app_header [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.5rem}.st-key-app_header [data-testid="stColumn"]{flex:1 1 100px!important;min-width:0!important}.st-key-app_header [data-testid="stColumn"]:first-child{flex-basis:100%!important}.auth-action-shell{justify-content:flex-start}.construction-hero{border-radius:14px}.construction-hero::after{display:none}.workspace-card-grid{grid-template-columns:1fr}.hero-data-row{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-data-cell{padding:.55rem}.hero-subline{font-size:.8rem}.chat-bubble{max-width:100%}.dashboard-metric-card{min-height:100px}.dashboard-metric-value{font-size:1.35rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>
'''

def inject():
    import streamlit as st
    st.markdown(CSS,unsafe_allow_html=True)


def saved_time(value):
    """Readable timestamps with an explicit timezone; preserve invalid legacy values."""
    from datetime import datetime,timezone
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc).strftime('%d %b %Y, %H:%M UTC')
    except (ValueError,TypeError):return str(value or 'Unknown time')
