from pathlib import Path
import sys
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.curriculum import load_concept_master
from src.ui import page_header, metric_card

page_header("Curriculum", "Browse the official curriculum map that anchors question generation and diagnostic analysis.")
lo, scope, topics = load_concept_master()

level = st.segmented_control("Level", ["P3", "P4", "P5", "P6"], default="P3")
filtered = lo[lo["Level"].eq(level)] if level else lo

c1, c2, c3 = st.columns(3)
with c1: metric_card("Learning outcomes", len(filtered))
with c2: metric_card("Topics", filtered["Topic_Code"].nunique())
with c3: metric_card("Core ideas", int(filtered["Official Domain"].eq("Core Ideas").sum()) if "Official Domain" in filtered.columns else "—")

st.dataframe(filtered, use_container_width=True, hide_index=True)
with st.expander("Scope notes"):
    st.dataframe(scope[scope["Level"].eq(level)] if "Level" in scope.columns else scope, use_container_width=True, hide_index=True)
