from __future__ import annotations

import streamlit as st

from src.ai_analysis import AI_MODEL_OPTIONS, AI_PROVIDERS, API_KEY_GUIDES, DEFAULT_AI_MODELS


def _key_state_name(provider: str) -> str:
    return f"ai_api_key_{provider.lower()}"


def clear_session_ai_keys() -> None:
    for provider in AI_PROVIDERS:
        st.session_state.pop(_key_state_name(provider), None)


def render_ai_provider_controls() -> tuple[str, str, str]:
    """Render provider/model/key controls and return provider, model, API key.

    API keys live only in st.session_state. They are not written to files,
    Streamlit Secrets, Google Drive snapshots, reports or logs by this module.
    """
    st.subheader("AI-assisted interpretation")
    provider = st.selectbox(
        "AI provider",
        options=list(AI_PROVIDERS),
        index=0,
        help="Choose which provider will write the optional anonymous report interpretation.",
    )

    model_labels = list(AI_MODEL_OPTIONS[provider])
    default_model = DEFAULT_AI_MODELS[provider]
    default_label = next(
        label for label, model_id in AI_MODEL_OPTIONS[provider].items() if model_id == default_model
    )
    selected_model_label = st.select_slider(
        f"{provider} model",
        options=model_labels,
        value=default_label,
        help="Choose a supported model. The default aims to keep report generation practical rather than maximally expensive.",
    )
    model = AI_MODEL_OPTIONS[provider][selected_model_label]

    state_key = _key_state_name(provider)
    st.session_state.setdefault(state_key, "")
    api_key = st.text_input(
        f"{provider} API key",
        type="password",
        key=state_key,
        help=(
            "Session-only. The key is held only in this Streamlit session and is not written "
            "to project files, Google Drive state, reports, exports or logs."
        ),
    )
    st.caption(
        f"Selected API model: `{model}` · The {provider} key is session-only and is cleared when you sign out."
    )

    guide = API_KEY_GUIDES[provider]
    with st.expander(f"How to get a {provider} API key"):
        st.caption(
            "Use your own or your organisation-approved API account. API usage, quotas and billing are controlled by that provider."
        )
        for index, step in enumerate(guide["steps"], start=1):
            st.markdown(f"{index}. {step}")
        c1, c2 = st.columns(2)
        with c1:
            st.link_button(
                f"Open {provider} key page",
                guide["url"],
                use_container_width=True,
            )
        with c2:
            st.link_button(
                f"Open {provider} API guide",
                guide["help_url"],
                use_container_width=True,
            )

    if st.button("Forget all session API keys", use_container_width=True):
        clear_session_ai_keys()
        st.rerun()

    return provider, model, api_key
